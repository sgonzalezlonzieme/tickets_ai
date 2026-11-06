import unittest
from unittest.mock import patch

import httpx
from openai import APIConnectionError, APIStatusError
from google.genai import errors, types

from clients.errors import ProviderConfigurationError, ProviderCredentialError, ProviderUnavailableError
from clients.openai.openai_client import OpenAIClient
from clients.openai.open_ai_configs import Settings
from clients.gemini.gemini_client import GeminiClient
from clients.gemini.settings import GeminiSettings, get_gemini_settings


class ProviderAdapterTests(unittest.TestCase):
    def test_openai_transient_http_errors_are_eligible_for_fallback(self):
        with patch('clients.openai.openai_client.OpenAI') as sdk, \
             patch('clients.openai.openai_client.dotenv_values',return_value={'OPENAI_API_KEY':'test'}):
            client=OpenAIClient(Settings(model='test',temperature=0.2,max_output_tokens=4000,instructions='test'))
            for code in [401,403,408,409,429,500,503]:
                with self.subTest(code=code):
                    response=httpx.Response(code,request=httpx.Request('POST','https://example.invalid'))
                    sdk.return_value.responses.create.side_effect=APIStatusError('test',response=response,body={})
                    with self.assertRaises(ProviderUnavailableError):
                        client.generate('Ticket')
            response=httpx.Response(400,request=httpx.Request('POST','https://example.invalid'))
            sdk.return_value.responses.create.side_effect=APIStatusError('test',response=response,body={})
            with self.assertRaises(APIStatusError):
                client.generate('Ticket')
            client.close()

    def test_gemini_errors_are_normalized_without_raw_body(self):
        with patch('clients.gemini.gemini_client.genai.Client') as sdk, \
             patch('clients.gemini.gemini_client.dotenv_values',return_value={'GEMINI_API_KEY':'test'}):
            client=GeminiClient(GeminiSettings(model='test'))
            for code,expected in [(429,ProviderUnavailableError),(503,ProviderUnavailableError),
                                  (400,ProviderConfigurationError),(401,ProviderCredentialError),(403,ProviderCredentialError)]:
                sdk.return_value.models.generate_content.side_effect=errors.APIError(
                    code,{'error':{'message':'private-value','code':code,'status':'TEST'}})
                with self.subTest(code=code), self.assertRaises(expected) as caught:
                    client.generate('Ticket')
                self.assertNotIn('private-value',str(caught.exception))
            sdk.return_value.models.generate_content.side_effect=httpx.ConnectError('private-value')
            with self.assertRaises(ProviderUnavailableError):
                client.generate('Ticket')
            client.close()

    def test_gemini_partial_or_blocked_text_is_not_returned(self):
        with patch('clients.gemini.gemini_client.genai.Client') as sdk, \
             patch('clients.gemini.gemini_client.dotenv_values',return_value={'GEMINI_API_KEY':'test'}):
            client=GeminiClient(GeminiSettings(model='test'))
            for reason in [types.FinishReason.MAX_TOKENS,types.FinishReason.SAFETY]:
                sdk.return_value.models.generate_content.return_value=types.GenerateContentResponse(
                    candidates=[types.Candidate(finish_reason=reason,
                        content=types.Content(parts=[types.Part(text='private-value')]))])
                result=client.generate('Ticket')
                self.assertNotEqual(result.status,'completed')
                self.assertEqual(result.output_text,'')
            client.close()

    def test_missing_gemini_key_has_clear_error_and_model_has_default(self):
        with patch('clients.gemini.gemini_client.dotenv_values',return_value={}):
            with self.assertRaises(ProviderConfigurationError):
                GeminiClient(GeminiSettings(model='test'))
        get_gemini_settings.cache_clear()
        with patch('clients.gemini.settings.dotenv_values',return_value={}):
            self.assertEqual(get_gemini_settings().model, 'gemini-flash-latest')
        get_gemini_settings.cache_clear()

    def test_gemini_invalid_key_http_400_activates_fallback(self):
        with patch('clients.gemini.gemini_client.genai.Client') as sdk, \
             patch('clients.gemini.gemini_client.dotenv_values', return_value={'GEMINI_API_KEY': 'test'}):
            client = GeminiClient(GeminiSettings(model='test'))
            sdk.return_value.models.generate_content.side_effect = errors.APIError(400, {
                'error': {'message': 'private-value', 'details': [{'reason': 'API_KEY_INVALID'}]},
            })
            with self.assertRaises(ProviderCredentialError) as caught:
                client.generate('Ticket')
            self.assertNotIn('private-value', str(caught.exception))
            client.close()

    def test_missing_openai_key_is_eligible_for_fallback(self):
        with patch('clients.openai.openai_client.dotenv_values', return_value={}):
            with self.assertRaises(ProviderCredentialError):
                OpenAIClient(Settings(model='test', temperature=0.2, max_output_tokens=4000, instructions='test'))
