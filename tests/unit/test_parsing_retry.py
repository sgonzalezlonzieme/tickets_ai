import unittest
from unittest.mock import Mock

from pydantic import ValidationError

from clients.base import LLMClient
from entities.response.openai import RESPONSE_MODELS
from clients.errors import ParsingRetriesExhaustedError, ProviderUnavailableError
from clients.parsing_retry import ParsingRetryClient
from entities.ticket_contracts import ModerationOutput
from entities.ticket_contracts import TicketOutput
from clients.result import ProviderResponse
from tests.support import ticket_output


def result(text, **kwargs):
    return ProviderResponse(status=kwargs.pop('status','completed'),output_text=text,**kwargs)


class ParsingRetryTests(unittest.TestCase):
    def setUp(self):
        self.provider=Mock(spec=LLMClient)
        self.factory=Mock(return_value=self.provider)
        self.client=ParsingRetryClient(self.factory, RESPONSE_MODELS)

    def test_each_stage_recovers_on_third_attempt(self):
        cases=[('moderate_input','Ticket','{"allowed":true}'),
               ('generate','Ticket',TicketOutput(**ticket_output()).model_dump_json()),
               ('moderate_output',TicketOutput(**ticket_output()),'{"answer":"Revisada","actions":[]}')]
        for operation,value,valid in cases:
            with self.subTest(operation=operation):
                self.setUp()
                method=getattr(self.provider,operation)
                method.side_effect=[result('invalid'),result('{}'),result(valid)]
                self.assertEqual(getattr(self.client,operation)(value).output_text,valid)
                self.assertEqual(method.call_count,3)
                self.assertTrue(all(call.args==(value,) for call in method.call_args_list))

    def test_exhaustion_makes_exactly_three_calls(self):
        self.provider.moderate_input.return_value=result('{"allowed":"yes"}')
        with self.assertRaises(ParsingRetriesExhaustedError):
            self.client.moderate_input('Ticket')
        self.assertEqual(self.provider.moderate_input.call_count,3)

    def test_recovers_on_second_attempt_without_third_call(self):
        self.provider.moderate_input.side_effect=[result('{}'),result('{"allowed":true}')]
        self.client.moderate_input('Ticket')
        self.assertEqual(self.provider.moderate_input.call_count,2)

    def test_rejection_refusal_and_partial_response_do_not_retry(self):
        for value in [result('{"allowed":false}'), result('',refused=True), result('',status='incomplete')]:
            self.setUp()
            self.provider.moderate_input.return_value=value
            self.assertIs(self.client.moderate_input('Ticket'),value)
            self.provider.moderate_input.assert_called_once()

    def test_network_failure_is_left_to_failover(self):
        self.provider.moderate_input.side_effect=ProviderUnavailableError()
        with self.assertRaises(ProviderUnavailableError):
            self.client.moderate_input('Ticket')
        self.provider.moderate_input.assert_called_once()

    def test_invalid_provider_envelope_also_retries(self):
        try:
            ModerationOutput.model_validate({})
        except ValidationError as error:
            validation_error=error
        self.provider.moderate_input.side_effect=[validation_error,result('{"allowed":true}')]
        self.client.moderate_input('Ticket')
        self.assertEqual(self.provider.moderate_input.call_count,2)

    def test_configuration_validation_failure_does_not_retry(self):
        try:
            ModerationOutput.model_validate({})
        except ValidationError as error:
            self.factory.side_effect=error
        with self.assertRaises(ValidationError):
            self.client.moderate_input('Ticket')
        self.factory.assert_called_once()

    def test_attempt_budget_resets_for_next_operation(self):
        self.provider.moderate_input.side_effect=[result('{}'),result('{"allowed":true}')]*2
        self.client.moderate_input('First')
        self.client.moderate_input('Second')
        self.assertEqual(self.provider.moderate_input.call_count,4)
