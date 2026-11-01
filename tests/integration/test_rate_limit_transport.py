import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx
import httpx2
from google import genai
from google.genai import types
from openai import DefaultHttpxClient

from clients.openai.openai_client import OpenAIClient
from clients.openai.open_ai_configs import Settings
from clients.gemini.gemini_client import GeminiClient
from clients.gemini.settings import GeminiSettings
from clients.rate_limit import RateLimiter,RateLimitStore
from tests.support import response_body
from tests.unit.test_rate_limit import Clock


class RateLimitTransportTests(unittest.TestCase):
    def setUp(self):
        self.directory=TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.clock=Clock()
        self.store=RateLimitStore(Path(self.directory.name)/'requests.sqlite3')

    def test_openai_transport_retries_pass_through_limiter(self):
        sent=[]
        def handler(request):
            payload=json.loads(request.content)
            self.assertIn('input',payload)
            self.assertNotIn('contents',payload)
            self.assertEqual(payload['text']['format']['type'],'json_schema')
            self.assertIs(payload['text']['format']['strict'],True)
            sent.append(request)
            if len(sent)==1:
                return httpx2.Response(429,headers={'retry-after-ms':'1'},json={'error':{'message':'retry','type':'rate_limit','code':'rate_limit'}})
            return httpx2.Response(200,json=response_body('{"allowed":true}'))
        def transport(**kwargs):
            return DefaultHttpxClient(transport=httpx2.MockTransport(handler),**kwargs)
        limiter=RateLimiter('openai',1,self.store,self.clock.time,self.clock.sleep)
        with patch('clients.openai.openai_client.dotenv_values',return_value={'OPENAI_API_KEY':'test'}), \
             patch('clients.openai.openai_client.get_rate_limiter',return_value=limiter), \
             patch('clients.openai.openai_client.DefaultHttpxClient',side_effect=transport):
            client=OpenAIClient(Settings(model='test',temperature=0.2,max_output_tokens=100,instructions='test'))
            try:
                self.assertEqual(client.moderate_input('Ticket').output_text,'{"allowed":true}')
            finally:
                client.close()
        self.assertEqual(len(sent),2)
        self.assertEqual(self.clock.waits,[60.0])

    def test_gemini_transport_retries_pass_through_limiter(self):
        sent=[]
        def handler(request):
            payload=json.loads(request.content)
            self.assertIn('contents',payload)
            self.assertNotIn('input',payload)
            self.assertEqual(payload['generationConfig']['responseMimeType'],'application/json')
            self.assertIn('responseJsonSchema',payload['generationConfig'])
            sent.append(request)
            if len(sent)==1:
                return httpx.Response(503,json={'error':{'code':503,'message':'retry','status':'UNAVAILABLE'}})
            return httpx.Response(200,json={'candidates':[{'content':{
                'parts':[{'text':'{"allowed":true}'}],'role':'model'},'finishReason':'STOP'}]})
        real_client=genai.Client
        def sdk_factory(**kwargs):
            options=kwargs['http_options']
            options.client_args['transport']=httpx.MockTransport(handler)
            options.retry_options=types.HttpRetryOptions(attempts=3,initial_delay=0.001,max_delay=0.001,jitter=0)
            return real_client(**kwargs)
        limiter=RateLimiter('gemini',1,self.store,self.clock.time,self.clock.sleep)
        with patch('clients.gemini.gemini_client.dotenv_values',return_value={'GEMINI_API_KEY':'test'}), \
             patch('clients.gemini.gemini_client.get_rate_limiter',return_value=limiter), \
             patch('clients.gemini.gemini_client.genai.Client',side_effect=sdk_factory):
            client=GeminiClient(GeminiSettings(model='test'))
            try:
                self.assertEqual(client.moderate_input('Ticket').output_text,'{"allowed":true}')
            finally:
                client.close()
        self.assertEqual(len(sent),2)
        self.assertEqual(self.clock.waits,[60.0])
