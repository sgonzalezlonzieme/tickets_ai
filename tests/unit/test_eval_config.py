import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from google.genai import types
import httpx
from pydantic import ValidationError

from evals.core import cli, config, providers
from utils import metrics


class EvalConfigTests(unittest.TestCase):
    def test_config_validates_provider_model_and_limits(self):
        for values in [
            {'provider': 'invalid', 'model': 'test'},
            {'provider': 'gemini', 'model': ' '},
            {'provider': 'gemini', 'model': 'test', 'max_output_tokens': 0},
            {'provider': 'gemini', 'model': 'test', 'api_key': 'private-value'},
        ]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                config.EvalConfig.model_validate(values)

    def test_model_override_and_provider_settings_do_not_read_other_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.yaml'
            path.write_text('provider: gemini\nmodel: configured-model\nmax_output_tokens: 123\n')
            selected = config.load_eval_config(path, model='override-model')
            with patch.object(providers, 'Settings', side_effect=AssertionError('OpenAI settings not needed')):
                settings = providers.get_eval_settings(selected)
            self.assertEqual(settings.model, 'override-model')
            self.assertEqual(settings.max_output_tokens, 123)
            with self.assertRaises(ValidationError):
                config.load_eval_config(path, model=' ')

    def test_bad_config_stops_before_creating_clients_and_omits_values(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(providers, 'OpenAIClient') as openai, \
             patch.object(providers, 'GeminiClient') as gemini:
            path = Path(directory) / 'config.yaml'
            for text in ['provider: [private-value', 'provider: private-value\nmodel: test\n']:
                path.write_text(text)
                stderr = io.StringIO()
                with self.subTest(text=text), patch('sys.stderr', stderr):
                    with self.assertRaises(SystemExit) as error:
                        cli.main(['--all', '--config', str(path)])
                    self.assertEqual(error.exception.code, 2)
                    self.assertNotIn('private-value', stderr.getvalue())
            openai.assert_not_called()
            gemini.assert_not_called()

    def response(self, text):
        return types.GenerateContentResponse(
            candidates=[types.Candidate(finish_reason=types.FinishReason.STOP,
                content=types.Content(parts=[types.Part(text=text)]))],
            model_version='test-gemini-returned',
        )

    def test_gemini_evaluates_all_stages_and_records_selected_model_without_openai(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('clients.gemini.gemini_client.genai.Client') as sdk, \
             patch('clients.gemini.gemini_client.dotenv_values', return_value={'GEMINI_API_KEY': 'test'}), \
             patch.object(providers, 'OpenAIClient') as openai, \
             patch.object(metrics, 'METRICS_DIR', Path(directory) / 'metrics'), \
             patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
            path = Path(directory) / 'config.yaml'
            path.write_text('provider: gemini\nmodel: configured-model\nmax_output_tokens: 123\n')
            sdk.return_value.models.generate_content.side_effect = [
                self.response('{"allowed":true}'),
                self.response('{"answer":"Podemos revisar tu consulta.","category":"billing","confidence":0.9,"actions":[]}'),
                self.response('{"answer":"Consultá al soporte oficial.","actions":[]}'),
            ]
            result = cli.main(['--all', '--limit', '1', '--config', str(path),
                               '--model', 'override-model', '--output-dir', directory])
            self.assertEqual(result, 0)
            report = json.loads(next(Path(directory).glob('*/summary.json')).read_text())
            self.assertEqual(report['provider'], 'gemini')
            self.assertEqual(report['model'], 'override-model')
            self.assertIsNone(report['temperature'])
            self.assertIsNone(report['reasoning_effort'])
            self.assertEqual(report['max_output_tokens'], 123)
            self.assertEqual(len(report['summaries']), 3)
            calls = sdk.return_value.models.generate_content.call_args_list
            self.assertEqual(len(calls), 3)
            for call in calls:
                self.assertEqual(call.kwargs['model'], 'override-model')
                self.assertEqual(call.kwargs['config'].max_output_tokens, 123)
            self.assertEqual([call.kwargs['config'].response_json_schema['title'] for call in calls],
                             ['GeminiModerationOutput', 'GeminiTicketOutput', 'GeminiOutputModerationOutput'])
            for filename in metrics.STAGE_FILES.values():
                row = json.loads((metrics.METRICS_DIR / filename).read_text())
                self.assertEqual(row['provider'], 'gemini')
                self.assertIsNotNone(row['prompt_file'])
            openai.assert_not_called()
            sdk.return_value.close.assert_called_once()

    def test_gemini_failure_does_not_fallback_and_client_is_closed(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('clients.gemini.gemini_client.genai.Client') as sdk, \
             patch('clients.gemini.gemini_client.dotenv_values', return_value={'GEMINI_API_KEY': 'test'}), \
             patch.object(providers, 'OpenAIClient') as openai, \
             patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
            path = Path(directory) / 'config.yaml'
            path.write_text('provider: gemini\nmodel: test\n')
            sdk.return_value.models.generate_content.side_effect = httpx.ConnectError('private-value')
            result = cli.main(['--stage', 'input_moderation', '--limit', '1',
                               '--config', str(path), '--output-dir', directory])
            self.assertEqual(result, 1)
            report = json.loads(next(Path(directory).glob('*/summary.json')).read_text())
            self.assertEqual(report['summaries'][0]['errors'], 1)
            openai.assert_not_called()
            sdk.return_value.close.assert_called_once()
