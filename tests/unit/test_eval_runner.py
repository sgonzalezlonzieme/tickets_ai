import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from clients.result import ProviderResponse

spec = importlib.util.spec_from_file_location('eval_runner', Path(__file__).resolve().parents[2] / 'evals/runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class EvalRunnerTests(unittest.TestCase):
    def test_all_datasets_validate(self):
        for stage, (_, filename, _) in runner.STAGES.items():
            cases = runner.load_cases(runner.ROOT / 'evals' / filename, stage)
            self.assertTrue(cases)
            self.assertTrue(all(case['stage'] == stage for case in cases))
            self.assertEqual(len(cases), {'input_question': 40, 'input_moderation': 28, 'output': 4}[stage])

    def test_failure_isolated_and_no_response_text_saved(self):
        client = Mock()
        client.generate_structured.side_effect = [
            ValueError('private-secret'),
            ProviderResponse(status='completed', output_text='{"allowed":true}', refused=False),
            ProviderResponse(status='completed', output_text='{"allowed":false}', refused=False),
        ]
        sink = io.StringIO()
        with patch('sys.stderr', io.StringIO()):
            summary = runner.run_variant(client, 'input_moderation', 'test.yaml', 'instructions',
                [{'input': 'private-secret', 'expected_allowed': True}] * 3, sink)
        self.assertEqual((summary['total'], summary['valid'], summary['passed'], summary['errors']), (3, 2, 1, 1))
        self.assertEqual(client.generate_structured.call_count, 3)
        self.assertNotIn('private-secret', sink.getvalue())

    def test_refusal_and_invalid_schema_fail(self):
        for response in [
            ProviderResponse(status='incomplete', output_text='{"allowed":true}', refused=False),
            ProviderResponse(status='completed', output_text='{"allowed":true}', refused=True),
            ProviderResponse(status='completed', output_text='{"allowed":"true"}', refused=False),
        ]:
            client = Mock()
            client.generate_structured.return_value = response
            with patch('sys.stderr', io.StringIO()):
                result = runner.run_variant(client, 'input_moderation', 'test.yaml', 'instructions',
                    [{'input': 'ticket', 'expected_allowed': True}], io.StringIO())
            self.assertEqual(result['passed'], 0)
            self.assertEqual(result['errors'], 1)

    def test_output_scores_answer_and_actions(self):
        contract = runner.STAGES['output'][2]
        for text in [{'answer': 'Safe', 'actions': ['SECRET']}, {'answer': 'secret', 'actions': []}]:
            self.assertFalse(runner.score('output', {'forbidden_strings': ['secret']}, contract(**text)))
        self.assertTrue(runner.score('output', {'forbidden_strings': ['secret']}, contract(answer='Safe', actions=[])))

    def test_cli_runs_all_stages_and_closes_client(self):
        from clients.openai.open_ai_configs import Settings
        settings = Settings(model='test-model', temperature=0, max_output_tokens=100, instructions='test')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(runner, 'get_settings', return_value=settings), \
             patch.object(runner, 'OpenAIClient') as factory, \
             patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
            factory.return_value.generate_structured.side_effect = [
                ProviderResponse(status='completed', output_text='{"allowed":true}', refused=False),
                ProviderResponse(status='completed', output_text='{"answer":"Revisar cobro","category":"billing","confidence":0.9,"actions":[]}', refused=False),
                ProviderResponse(status='completed', output_text='{"answer":"Contactá a soporte","actions":[]}', refused=False),
            ]
            self.assertEqual(runner.main(['--all', '--limit', '1', '--output-dir', directory]), 0)
            factory.return_value.close.assert_called_once()
            report = json.loads(next(Path(directory).glob('*/summary.json')).read_text())
            self.assertEqual(len(report['summaries']), 3)
            self.assertEqual(report['provider'], 'openai')
            from clients.prompts import get_active_prompts
            self.assertEqual({row['stage']: row['prompt'] for row in report['summaries']}, get_active_prompts())

    def test_all_prompts_discovers_technique_subfolders(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(runner, 'OpenAIClient') as factory, \
             patch.object(runner, 'get_settings', return_value=Mock(model='test', temperature=0.2, max_output_tokens=4000)), \
             patch('sys.stdout', io.StringIO()):
            factory.return_value.generate_structured.return_value = ProviderResponse(
                status='completed', output_text='{"allowed":true}', refused=False)
            self.assertEqual(runner.main([
                '--stage', 'input_moderation', '--all-prompts', '--limit', '1',
                '--output-dir', directory,
            ]), 0)
            report = json.loads(next(Path(directory).glob('*/summary.json')).read_text())
            self.assertEqual(len(report['summaries']), 7)
            self.assertEqual(factory.return_value.generate_structured.call_count, 7)

    def test_invalid_options_do_not_initialize_client(self):
        with patch.object(runner, 'OpenAIClient') as factory, patch('sys.stderr', io.StringIO()):
            for args in [['--all', '--limit', '0'], ['--all', '--prompt', 'test.yaml'],
                         ['--stage', 'output', '--prompt', '../test.yaml']]:
                with self.assertRaises(SystemExit):
                    runner.main(args)
            factory.assert_not_called()


    def test_missing_empty_and_duplicate_ids_are_rejected(self):
        base = {'input': 'Ticket', 'stage': 'input_moderation', 'expected_allowed': True}
        for rows in [[base], [{**base, 'id': ' '}],
                     [{**base, 'id': 'same'}, {**base, 'id': 'same'}]]:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'data_set.jsonl'
                path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
                with self.assertRaises(ValueError):
                    runner.load_cases(path, 'input_moderation')
