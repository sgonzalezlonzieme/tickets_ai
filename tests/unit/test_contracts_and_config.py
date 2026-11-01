import json
from pathlib import Path
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from clients.openai import open_ai_configs as config
from entities.request import OpenAIRequest
from entities.ticket_contracts import TicketOutput
from entities.ticket_contracts import ModerationOutput
from entities.ticket_contracts import OutputModerationOutput
from utils.validation import validate_data, DataValidationError
from tests.support import ticket_output


class ContractTests(unittest.TestCase):
    def test_moderation_requires_boolean_and_no_extras(self):
        for value in [True, False]:
            self.assertIs(ModerationOutput(allowed=value).allowed, value)
        for value in [{}, {'allowed':'true'}, {'allowed':1}, {'allowed':None}, {'allowed':True,'reason':'x'}]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ModerationOutput.model_validate(value)

    def test_output_requires_nonempty_answer_and_string_actions(self):
        self.assertEqual(OutputModerationOutput(answer='Listo',actions=[]).actions, [])
        for value in [{'answer':' ', 'actions':[]}, {'answer':'x'}, {'answer':'x','actions':[1]},
                      {'answer':'x','actions':[], 'category':'other'}]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                OutputModerationOutput.model_validate(value)

    def test_request_models_reject_empty_input_and_extra_fields(self):
        for model in [OpenAIRequest]:
            base=dict(model='test-model', input='Ticket', instructions='Instructions', max_output_tokens=100)
            self.assertEqual(model(**base).input, 'Ticket')
            for update in [{'input':' '}, {'max_output_tokens':0}, {'unexpected':True}]:
                with self.subTest(model=model.__name__, update=update), self.assertRaises(ValidationError):
                    model(**(base|update))

    def test_dataset_has_valid_labels_and_balanced_examples(self):
        rows=[json.loads(line) for line in (Path(__file__).resolve().parents[2]/'evals/dataset.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows),40)
        counts={category:0 for category in ['billing','technical','account','other']}
        for row in rows:
            self.assertTrue(row['input'].strip())
            TicketOutput.model_validate(ticket_output(row['expected_category']))
            counts[row['expected_category']]+=1
        self.assertEqual(set(counts.values()),{10})

    def test_validation_errors_omit_input(self):
        with self.assertRaises(DataValidationError) as caught:
            validate_data(ModerationOutput, {'allowed':'private-value'})
        self.assertNotIn('private-value', repr(caught.exception.errors))
        self.assertEqual(caught.exception.errors[0]['category'],'invalid_type')


class ConfigTests(unittest.TestCase):
    def tearDown(self):
        config.get_settings.cache_clear()

    def test_all_three_prompts_load_from_disk(self):
        prompts=[config._load_instructions(), config.get_moderation_instructions(),
                 config.get_output_moderation_instructions()]
        self.assertEqual(len(set(prompts)),3)
        self.assertTrue(all(isinstance(prompt,str) and prompt.strip() for prompt in prompts))

    def test_missing_or_invalid_prompt_instructions_fail(self):
        for value in [None, [], {}, {'instructions': ''}, {'instructions': 123}]:
            with patch('clients.prompts.yaml.safe_load',return_value=value):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    config._load_instructions()

    def test_settings_validate_env_and_are_cached(self):
        config.get_settings.cache_clear()
        with patch('clients.openai.open_ai_configs.dotenv_values',return_value={
            'OPENAI_MODEL':'test-model','OPENAI_TEMPERATURE':'0.2','OPENAI_MAX_OUTPUT_TOKENS':'4000'}):
            first=config.get_settings()
            self.assertEqual(first.max_output_tokens,4000)
            self.assertIs(first,config.get_settings())
        config.get_settings.cache_clear()
        with patch('clients.openai.open_ai_configs.dotenv_values',return_value={}):
            with self.assertRaises(ValidationError):
                config.get_settings()

class GeminiEntityTests(unittest.TestCase):
    def test_request_validates_model_input_and_rejects_extra_fields(self):
        from google.genai.types import GenerateContentConfig
        from entities.request.gemini import GeminiRequest
        base={'model':'test','contents':'Ticket','config':GenerateContentConfig()}
        self.assertEqual(GeminiRequest(**base).contents,'Ticket')
        for update in [{'contents':' '},{'model':''},{'extra':True}]:
            with self.subTest(update=update),self.assertRaises(ValidationError):
                GeminiRequest(**(base|update))

    def test_response_extracts_text_without_thought_parts(self):
        from google.genai import types
        from entities.response.gemini import GeminiResponse
        sdk=types.GenerateContentResponse(candidates=[types.Candidate(
            content=types.Content(parts=[types.Part(text='internal',thought=True),
                                         types.Part(text='visible')]))])
        self.assertEqual(GeminiResponse.model_validate(sdk.model_dump()).output_text,'visible')
        self.assertEqual(GeminiResponse(candidates=None).output_text,'')

    def test_response_rejects_malformed_candidate_envelope(self):
        from entities.response.gemini import GeminiResponse
        for body in [{},{'candidates':'invalid'}]:
            with self.subTest(body=body),self.assertRaises(ValidationError):
                GeminiResponse.model_validate(body)
