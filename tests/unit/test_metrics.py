import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from entities.response.openai import OpenAIResponse
from tests.support import response_body
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
