import json
import unittest
from unittest.mock import patch

import httpx
from openai import APIConnectionError
from google.genai import types

from tests.integration import test_pipeline as pipeline
from clients.gemini.settings import get_gemini_settings


def gemini_response(text, finish=types.FinishReason.STOP):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        finish_reason=finish,
        content=types.Content(parts=[types.Part(text=text)]),
    )])


class GeminiFailoverIntegrationTests(unittest.TestCase):
    def setUp(self):
        get_gemini_settings.cache_clear()
        self.addCleanup(get_gemini_settings.cache_clear)
        self.config={'GEMINI_API_KEY':'test-key','GEMINI_MODEL':'test-gemini-model',
                     'GEMINI_MAX_OUTPUT_TOKENS':'4000'}

    def test_fallback_works_at_each_stage_and_next_stage_retries_openai(self):
        for stage,text in enumerate(['{"allowed":true}',
              '{"answer":"Borrador","category":"account","confidence":0.95,"actions":[]}',
              '{"answer":"Revisada por Gemini","actions":[]}']):
            with self.subTest(stage=stage), \
                 patch('clients.gemini.gemini_client.genai.Client') as sdk, \
                 patch('clients.gemini.settings.dotenv_values',return_value=self.config), \
                 patch('clients.gemini.gemini_client.dotenv_values',return_value=self.config):
                get_gemini_settings.cache_clear()
                sdk.return_value.models.generate_content.return_value=gemini_response(text)
                harness=pipeline.PipelineIntegrationTests()
                bodies=harness.valid_bodies()
                bodies[stage]=APIConnectionError(request=httpx.Request('POST','https://example.invalid'))
                code,out,err,calls=harness.run_pipeline(bodies, gemini_config=self.config)
                self.assertEqual(code,0)
                self.assertEqual(len(calls),3)
                self.assertEqual(json.loads(out)['category'],'account')
                sdk.return_value.models.generate_content.assert_called_once()
                request=sdk.return_value.models.generate_content.call_args.kwargs
                self.assertEqual(request['model'],'test-gemini-model')
                self.assertEqual(request['config'].response_mime_type,'application/json')
                self.assertIs(request['config'].response_json_schema['additionalProperties'],False)
                sdk.return_value.close.assert_called_once()
                self.assertIn('trying Gemini',err)

    def test_gemini_rejection_stops_pipeline_after_failed_openai(self):
        with patch('clients.gemini.gemini_client.genai.Client') as sdk, \
             patch('clients.gemini.settings.dotenv_values',return_value=self.config), \
             patch('clients.gemini.gemini_client.dotenv_values',return_value=self.config):
            sdk.return_value.models.generate_content.return_value=gemini_response('{"allowed":false}')
            code,out,err,calls=pipeline.PipelineIntegrationTests().run_pipeline([
                APIConnectionError(request=httpx.Request('POST','https://example.invalid'))], gemini_config=self.config)
            self.assertEqual((code,out,len(calls)),(1,'',1))
            self.assertIn('No podemos procesar',err)

    def test_parse_exhaustion_switches_to_gemini_and_retries_its_parse(self):
        from tests.support import response_body
        for stage,text in enumerate(['{"allowed":true}',
                '{"answer":"Borrador","category":"account","confidence":0.95,"actions":[]}',
                '{"answer":"Revisada por Gemini","actions":[]}']):
            with self.subTest(stage=stage), patch('clients.gemini.gemini_client.genai.Client') as sdk:
                get_gemini_settings.cache_clear()
                sdk.return_value.models.generate_content.side_effect=[
                    gemini_response('invalid'),gemini_response(text)]
                harness=pipeline.PipelineIntegrationTests()
                valid=harness.valid_bodies()
                bodies=valid[:stage]+[response_body('invalid')]*3+valid[stage+1:]
                code,out,err,calls=harness.run_pipeline(bodies,gemini_config=self.config)
                self.assertEqual(code,0)
                self.assertEqual(len(calls),5)
                self.assertEqual(sdk.return_value.models.generate_content.call_count,2)
                self.assertEqual(json.loads(out)['category'],'account')
                self.assertNotIn('private@example.com',out+err)

    def test_both_providers_exhaust_parse_budget_without_unreviewed_output(self):
        from tests.support import response_body
        with patch('clients.gemini.gemini_client.genai.Client') as sdk:
            sdk.return_value.models.generate_content.return_value=gemini_response('invalid private-value')
            code,out,err,calls=pipeline.PipelineIntegrationTests().run_pipeline(
                [response_body('invalid private-value')]*3,gemini_config=self.config)
            self.assertEqual((code,out,len(calls)),(1,'',3))
            self.assertEqual(sdk.return_value.models.generate_content.call_count,3)
            self.assertNotIn('private-value',err)
