import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from entities.response.openai import OpenAIResponse
from tests.support import response_body, ticket_output
from utils import metrics


class MetricsTests(unittest.TestCase):
    def response(self, model='gpt-6-luna', cached=0):
        body = response_body()
        body['model'] = model
        body['usage'] = {
            'input_tokens': 413, 'output_tokens': 76, 'total_tokens': 489,
            'input_tokens_details': {'cached_tokens': cached, 'cache_write_tokens': 0},
            'output_tokens_details': {'reasoning_tokens': 0},
        }
        return OpenAIResponse.model_validate(body)

    def test_appends_and_computes_cached_cost(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(metrics, 'METRICS_DIR', Path(directory)):
            first = metrics.record_openai_metrics(self.response(), 45.6761, stage="input")
            second = metrics.record_openai_metrics(self.response(cached=100), 1, stage="input")
            lines = [json.loads(line) for line in (metrics.METRICS_DIR / "input_moderation.jsonl").read_text().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(first['cost_usd'], 0.0000793)
        self.assertAlmostEqual(second['cost_usd'], 0.0000703)
        self.assertEqual(first['total_tokens'], 489)
        self.assertEqual(first['latency_s'], 45.676)
        self.assertTrue(first['timestamp'].endswith('+00:00'))
        self.assertNotIn('output_text', first)

    def test_unknown_model_and_missing_usage_are_not_free(self):
        self.assertIsNone(metrics.estimate_cost('unknown', self.response().usage))
        self.assertIsNone(metrics.estimate_cost('gpt-6-luna', None))

    def test_write_failure_does_not_break_response(self):
        with patch.object(metrics, 'METRICS_DIR') as path:
            path.__truediv__.return_value.open.side_effect = OSError('unwritable')
            with self.assertLogs('utils.metrics', level='WARNING'):
                result = metrics.record_openai_metrics(self.response(), 1, stage="input")
        self.assertEqual(result['total_tokens'], 489)

    def test_pipeline_records_each_openai_stage(self):
        from tests.integration.test_pipeline import PipelineIntegrationTests
        harness = PipelineIntegrationTests()
        with patch('clients.openai.openai_client.record_openai_metrics') as record:
            code, _, _, calls = harness.run_pipeline(harness.valid_bodies())
        self.assertEqual(code, 0)
        self.assertEqual(record.call_count, 3)
        self.assertEqual([call.kwargs["stage"] for call in record.call_args_list],
                         ["input", "generation", "output"])
        self.assertEqual(len(calls), 3)


    def test_each_stage_has_its_own_file(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(metrics, 'METRICS_DIR', Path(directory)):
            for stage in metrics.STAGE_FILES:
                metrics.record_openai_metrics(self.response(), 1, stage=stage)
            self.assertEqual({p.name for p in Path(directory).iterdir()},
                             {'input_moderation.jsonl', 'input_question.jsonl', 'output_moderation.jsonl'})
            for path in Path(directory).iterdir():
                self.assertEqual(len(path.read_text().splitlines()), 1)


class GeminiMetricsTests(unittest.TestCase):
    def response(self, **overrides):
        from entities.response.gemini.gemini_response import GeminiResponse
        body = {
            'candidates': [], 'model_version': 'test-gemini',
            'usage_metadata': {'prompt_token_count': 100, 'candidates_token_count': 20,
                               'thoughts_token_count': 10, 'total_token_count': 130,
                               'cached_content_token_count': 40},
        }
        body.update(overrides)
        return GeminiResponse.model_validate(body)

    def test_appends_both_providers_and_counts_thinking_with_synthetic_prices(self):
        with tempfile.TemporaryDirectory() as directory:
            prices = Path(directory) / 'prices.json'
            prices.write_text(json.dumps({'models': {'test-gemini': {
                'input_per_million': 1, 'cached_input_per_million': 0.1,
                'output_per_million': 2,
            }}}))
            with patch.object(metrics, 'METRICS_DIR', Path(directory) / 'metrics'), \
                 patch.object(metrics, 'GEMINI_PRICING_PATH', prices):
                metrics.record_openai_metrics(MetricsTests().response(), 1, stage='input')
                record = metrics.record_gemini_metrics(self.response(), 1.23456, stage='input', requested_model='alias')
                rows = [json.loads(line) for line in (metrics.METRICS_DIR / 'input_moderation.jsonl').read_text().splitlines()]
            self.assertEqual([row['provider'] for row in rows], ['openai', 'gemini'])
            self.assertEqual(record['model'], 'test-gemini')
            self.assertEqual(record['completion_tokens'], 30)
            self.assertEqual(record['total_tokens'], 130)
            self.assertEqual(record['latency_s'], 1.235)
            self.assertAlmostEqual(record['cost_usd'], 0.000124)
            self.assertNotIn('output_text', record)

    def test_missing_usage_and_unknown_prices_are_null(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(metrics, 'METRICS_DIR', Path(directory)):
            record = metrics.record_gemini_metrics(self.response(model_version=None, usage_metadata=None),
                                                  1, stage='output', requested_model='alias')
            self.assertEqual(record['model'], 'alias')
            for key in ['prompt_tokens', 'completion_tokens', 'total_tokens', 'cost_usd']:
                self.assertIsNone(record[key])
            record = metrics.record_gemini_metrics(self.response(), 1, stage='input', requested_model='alias')
            self.assertIsNone(record['cost_usd'])

    def test_write_failure_does_not_break_gemini_response(self):
        with patch.object(metrics, 'METRICS_DIR') as path:
            path.__truediv__.return_value.open.side_effect = OSError('private-value')
            with self.assertLogs('utils.metrics', level='WARNING') as logs:
                record = metrics.record_gemini_metrics(self.response(), 1, stage='input', requested_model='alias')
            self.assertNotIn('private-value', '\n'.join(logs.output))
            self.assertEqual(record['provider'], 'gemini')

    def test_gemini_adapter_records_each_stage_and_not_transport_errors(self):
        from google.genai import types
        import httpx
        from clients.gemini.gemini_client import GeminiClient
        from clients.gemini.settings import GeminiSettings
        from clients.errors import ProviderUnavailableError
        from entities.ticket_contracts import TicketOutput
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(metrics, 'METRICS_DIR', Path(directory)), \
             patch('clients.gemini.gemini_client.dotenv_values', return_value={'GEMINI_API_KEY': 'test'}), \
             patch('clients.gemini.gemini_client.genai.Client') as sdk:
            sdk.return_value.models.generate_content.return_value = types.GenerateContentResponse(
                candidates=[types.Candidate(finish_reason=types.FinishReason.STOP,
                    content=types.Content(parts=[types.Part(text='{}')]))],
                model_version='returned-model',
                usage_metadata=types.GenerateContentResponseUsageMetadata(
                    prompt_token_count=10, candidates_token_count=5, total_token_count=15))
            client = GeminiClient(GeminiSettings(model='alias'))
            client.moderate_input('Ticket')
            client.generate('Ticket')
            client.moderate_output(TicketOutput(**ticket_output()))
            for filename in metrics.STAGE_FILES.values():
                rows = (Path(directory) / filename).read_text().splitlines()
                self.assertEqual(len(rows), 1)
                self.assertEqual(json.loads(rows[0])['model'], 'returned-model')
            sdk.return_value.models.generate_content.side_effect = httpx.ConnectError('private-value')
            with self.assertRaises(ProviderUnavailableError):
                client.generate('Ticket')
            self.assertEqual(len((Path(directory) / 'input_question.jsonl').read_text().splitlines()), 1)
            client.close()

    def test_configured_gemini_prices_match_ticket_example(self):
        from datetime import datetime, timezone
        response = self.response(model_version='gemini-3.8-flash', usage_metadata={
            'prompt_token_count': 475, 'candidates_token_count': 71, 'total_token_count': 546,
        })
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(metrics, 'METRICS_DIR', Path(directory)), \
             patch.object(metrics, 'datetime') as clock:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.return_value = datetime(2026, 11, 6, tzinfo=timezone.utc)
            record = metrics.record_gemini_metrics(response, 1.928, stage='input', requested_model='gemini-3.8-flash')
            self.assertAlmostEqual(record['cost_usd'], 0.0006225)
            clock.now.return_value = datetime(2027, 1, 1, tzinfo=timezone.utc)
            with self.assertLogs('utils.metrics', level='WARNING'):
                expired = metrics.record_gemini_metrics(response, 1, stage='input', requested_model='gemini-3.8-flash')
            self.assertIsNone(expired['cost_usd'])
            self.assertEqual(expired['total_tokens'], 546)


class ReadableMetricsTests(unittest.TestCase):
    def test_both_providers_use_decimal_usd_and_explicit_units(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(metrics, 'METRICS_DIR', Path(directory)):
            for provider in ['openai', 'gemini']:
                record = {
                    'timestamp': '2026-11-06T12:10:57.211466+00:00',
                    'provider': provider, 'model': 'test-model', 'prompt_tokens': 507,
                    'completion_tokens': 39, 'total_tokens': 546,
                    'latency_s': 3.578, 'cost_usd': 7.02e-05,
                }
                metrics._persist_metrics(record, 'input')
            raw = (Path(directory) / 'input_moderation.jsonl').read_text()
            self.assertNotIn('7.02e-05', raw)
            self.assertIn('"cost_usd": 0.0000702', raw)
            for line in raw.splitlines():
                row = json.loads(line)
                self.assertEqual(list(row)[:3], ['system_prompt', 'prompt_file', 'prompt_sha256'])
                self.assertEqual(row['system_prompt'], {'stage': 'input_moderation', 'version': None})
                self.assertEqual(row['cost_usd'], 0.0000702)
                self.assertIsInstance(row['latency_s'], float)
                self.assertEqual(row['readable']['costo_estimado'], 'USD 0.0000702')
                self.assertEqual(row['readable']['duracion'], '3.578 segundos')
                self.assertEqual(row['readable']['tokens_entrada'], '507 tokens')
                self.assertEqual(row['readable']['fecha_utc'], '2026-11-06 12:10:57 UTC')

    def test_missing_cost_and_usage_are_not_displayed_as_zero(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(metrics, 'METRICS_DIR', Path(directory)):
            record = metrics.record_gemini_metrics(
                GeminiMetricsTests().response(usage_metadata=None), 2, stage='output', requested_model='test')
            raw = (Path(directory) / 'output_moderation.jsonl').read_text()
            self.assertIn('"latency_s": 2.000', raw)
            self.assertIn('"cost_usd": null', raw)
            self.assertEqual(record['readable']['costo_estimado'], 'No disponible')
            self.assertEqual(record['readable']['tokens_entrada'], 'No disponible')

    def test_prompt_identity_matches_actual_instructions_for_both_providers(self):
        import hashlib
        from clients.prompts import _load_instructions
        active = _load_instructions()
        candidate = _load_instructions('input_question', 'version_5_06_11.yaml')
        with tempfile.TemporaryDirectory() as directory, patch.object(metrics, 'METRICS_DIR', Path(directory)):
            first = metrics.record_openai_metrics(MetricsTests().response(), 1, stage='generation', instructions=candidate)
            second = metrics.record_gemini_metrics(GeminiMetricsTests().response(), 1, stage='generation',
                                                  requested_model='test', instructions=active)
            self.assertEqual(first['prompt_file'], 'prompts/input_question/few_shots/version_5_06_11.yaml')
            self.assertEqual(second['prompt_file'], 'prompts/input_question/few_shots/version_7_06_11.yaml')
            self.assertEqual(first['prompt_sha256'], hashlib.sha256(candidate.encode()).hexdigest())
            self.assertNotEqual(first['prompt_sha256'], second['prompt_sha256'])
            self.assertEqual(first['system_prompt'], {'stage': 'input_question', 'version': 'version_5_06_11'})
            self.assertEqual(second['system_prompt'], {'stage': 'input_question', 'version': 'version_7_06_11'})
            custom = metrics.record_openai_metrics(MetricsTests().response(), 1, stage='generation', instructions='custom')
            self.assertIsNone(custom['prompt_file'])
            self.assertEqual(custom['system_prompt'], {'stage': 'input_question', 'version': None})
            self.assertEqual(custom['prompt_sha256'], hashlib.sha256(b'custom').hexdigest())
            raw = (Path(directory) / 'input_question.jsonl').read_text()
            self.assertNotIn('Sos un clasificador', raw)
