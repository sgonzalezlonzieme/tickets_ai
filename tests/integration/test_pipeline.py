from contextlib import redirect_stderr, redirect_stdout
import io
import json
import logging
import unittest
from unittest.mock import Mock, patch

from tests.support import response_body, ticket_output
import main
from configs import clients as factory
from clients.lifecycle import close_llm_client
from clients.openai import open_ai_configs as config


class PipelineIntegrationTests(unittest.TestCase):
    def run_pipeline(self, responses, arguments=None, user_input='', gemini_config=None):
        close_llm_client()
        config.get_settings.cache_clear()
        settings={'OPENAI_API_KEY':'test-key','OPENAI_MODEL':'gpt-6-luna',
                  'OPENAI_TEMPERATURE':'0.2','OPENAI_MAX_OUTPUT_TOKENS':'4000'}
        stdout,stderr=io.StringIO(),io.StringIO()
        root=logging.getLogger()
        old_handlers,old_level=root.handlers[:],root.level
        wrapped=[]
        for body in responses:
            if isinstance(body,Exception):
                wrapped.append(body)
            else:
                item=Mock()
                item.model_dump.return_value=body
                wrapped.append(item)
        try:
            with patch('clients.openai.openai_client.OpenAI') as sdk, \
                 patch('clients.openai.openai_client.dotenv_values',return_value=settings), \
                 patch('clients.openai.open_ai_configs.dotenv_values',return_value=settings), \
                 patch('clients.gemini.settings.dotenv_values',return_value=gemini_config or {}), \
                 patch('clients.gemini.gemini_client.dotenv_values',return_value=gemini_config or {}), \
                 patch('sys.argv',['main.py',*(arguments if arguments is not None else ['Problema de acceso'])]), \
                 patch('sys.stdin',io.StringIO(user_input)), \
                 redirect_stdout(stdout),redirect_stderr(stderr):
                sdk.return_value.responses.create.side_effect=wrapped
                code=main.main()
                calls=[call.kwargs for call in sdk.return_value.responses.create.call_args_list]
                if calls:
                    sdk.return_value.close.assert_called_once()
                self.assertEqual(factory.get_openai_client.cache_info().currsize,0)
            return code,stdout.getvalue(),stderr.getvalue(),calls
        finally:
            close_llm_client()
            config.get_settings.cache_clear()
            for handler in root.handlers:
                handler.close()
            root.handlers=old_handlers
            root.setLevel(old_level)

    def valid_bodies(self):
        return [response_body('{"allowed":true}'),
                response_body(json.dumps(ticket_output(answer='private@example.com'))),
                response_body('{"answer":"Contactá al soporte oficial.","actions":[]}')]

    def test_three_calls_in_order_and_only_revised_output_is_printed(self):
        code,out,err,calls=self.run_pipeline(self.valid_bodies(),['--debug','Problema de acceso'])
        self.assertEqual(code,0)
        final=json.loads(out)
        self.assertEqual(final['answer'],'Contactá al soporte oficial.')
        self.assertEqual(final['category'],'account')
        self.assertEqual(final['confidence'],0.95)
        self.assertEqual([c['text']['format']['name'] for c in calls],
                         ['moderation_output','ticket_output','output_moderation'])
        self.assertEqual(len({c['instructions'] for c in calls}),3)
        self.assertEqual(calls[0]['input'],calls[1]['input'])
        self.assertEqual(set(json.loads(calls[2]['input'])),{'answer','actions'})
        self.assertNotIn('Problema de acceso',calls[2]['input'])
        self.assertNotIn('private@example.com',out+err)
        self.assertNotIn('test-encrypted-content',out+err)
        for call in calls:
            self.assertIs(call['text']['format']['strict'],True)
            self.assertIs(call['text']['format']['schema']['additionalProperties'],False)

    def test_denied_input_uses_one_call_and_spanish_message(self):
        code,out,err,calls=self.run_pipeline([response_body('{"allowed":false}')])
        self.assertEqual(code,1)
        self.assertEqual(out,'')
        self.assertIn('No podemos procesar esta consulta',err)
        self.assertEqual(len(calls),1)

    def test_failure_at_each_stage_stops_without_printing_draft(self):
        bad_bodies=[response_body('invalid private-value'),response_body('',status='incomplete'),
                    response_body('',refusal=True),{'invalid':'private-value'},
                    RuntimeError('private-value')]
        for stage in range(3):
            for bad in bad_bodies:
                with self.subTest(stage=stage,bad=type(bad).__name__):
                    attempts = 3 if bad is bad_bodies[0] or bad is bad_bodies[3] else 1
                    responses=self.valid_bodies()[:stage]+[bad]*attempts
                    code,out,err,calls=self.run_pipeline(responses)
                    self.assertEqual(code,1)
                    self.assertEqual(out,'')
                    self.assertEqual(len(calls),stage+attempts)
                    self.assertNotIn('private-value',err)
                    self.assertNotIn('private@example.com',err)

    def test_interactive_ticket_runs_pipeline(self):
        code,out,err,calls=self.run_pipeline(self.valid_bodies(),[], 'No puedo entrar\n')
        self.assertEqual(code,0)
        self.assertIn('Ticket:',err)
        self.assertEqual(calls[0]['input'],'No puedo entrar')
        json.loads(out)

    def test_empty_input_and_eof_make_no_calls(self):
        code,out,err,calls=self.run_pipeline([],['   '])
        self.assertEqual((code,out,calls),(1,'',[]))
        code,out,err,calls=self.run_pipeline([],[])
        self.assertEqual((code,out,calls),(130,'',[]))

    def test_invalid_output_recovers_on_third_attempt_at_each_stage(self):
        for stage in range(3):
            with self.subTest(stage=stage):
                valid=self.valid_bodies()
                bodies=valid[:stage]+[response_body('invalid')]*2+valid[stage:]
                code,out,err,calls=self.run_pipeline(bodies)
                self.assertEqual(code,0)
                self.assertEqual(len(calls),5)
                self.assertEqual(json.loads(out)['answer'],'Contactá al soporte oficial.')
                self.assertIn('Attempt=2/3',err)
