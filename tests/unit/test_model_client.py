import unittest
from unittest.mock import Mock

from clients.base import LLMClient
from clients.errors import ProviderUnavailableError, ProviderConfigurationError
from clients.model_client import ModelClient
from clients.fallback import FallbackHandler
from clients.result import ProviderResponse
from entities.ticket_contracts import TicketOutput
from tests.support import ticket_output


class ModelClientTests(unittest.TestCase):
    def setUp(self):
        self.primary=Mock(spec=LLMClient)
        self.backup=Mock(spec=LLMClient)
        self.primary_factory=Mock(return_value=self.primary)
        self.backup_factory=Mock(return_value=self.backup)
        self.client=ModelClient(self.primary_factory,FallbackHandler(self.backup_factory))

    def test_abstract_interface_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            LLMClient()

    def test_healthy_openai_never_initializes_gemini(self):
        expected=ProviderResponse(status='completed',output_text='{}')
        self.primary.moderate_input.return_value=expected
        self.assertIs(self.client.moderate_input('Ticket'),expected)
        self.backup_factory.assert_not_called()

    def test_transient_failure_retries_same_stage_with_gemini(self):
        for method,value in [('moderate_input','Ticket'),('generate','Ticket'),
                             ('moderate_output',TicketOutput(**ticket_output()))]:
            with self.subTest(method=method):
                self.setUp()
                getattr(self.primary,method).side_effect=ProviderUnavailableError('Unavailable')
                expected=ProviderResponse(status='completed',output_text='{}')
                getattr(self.backup,method).return_value=expected
                self.assertIs(getattr(self.client,method)(value),expected)
                getattr(self.primary,method).assert_called_once_with(value)
                getattr(self.backup,method).assert_called_once_with(value)

    def test_next_operation_always_tries_openai_again(self):
        self.primary.moderate_input.side_effect=ProviderUnavailableError()
        self.client.moderate_input('Ticket')
        self.client.generate('Ticket')
        self.primary.generate.assert_called_once_with('Ticket')
        self.backup.generate.assert_not_called()

    def test_rejection_refusal_and_incomplete_do_not_switch_provider(self):
        for result in [ProviderResponse(status='completed',output_text='{"allowed":false}'),
                       ProviderResponse(status='completed',output_text='',refused=True),
                       ProviderResponse(status='incomplete',output_text='')]:
            self.primary.moderate_input.return_value=result
            self.assertIs(self.client.moderate_input('Ticket'),result)
        self.backup_factory.assert_not_called()

    def test_nontransient_errors_do_not_switch_provider(self):
        for error in [ValueError('Invalid output'),ProviderConfigurationError('Config'),RuntimeError('Bug')]:
            self.primary.moderate_input.side_effect=error
            with self.assertRaises(type(error)):
                self.client.moderate_input('Ticket')
        self.backup_factory.assert_not_called()

    def test_both_providers_failing_propagates_without_loop(self):
        self.primary.moderate_input.side_effect=ProviderUnavailableError()
        self.backup.moderate_input.side_effect=ProviderUnavailableError()
        with self.assertRaises(ProviderUnavailableError):
            self.client.moderate_input('Ticket')
        self.primary.moderate_input.assert_called_once()
        self.backup.moderate_input.assert_called_once()

    def test_cleanup_attempts_both_even_if_primary_close_fails(self):
        self.primary.moderate_input.side_effect=ProviderUnavailableError()
        self.client.moderate_input('Ticket')
        self.primary.close.side_effect=RuntimeError('Close failed')
        with self.assertRaises(RuntimeError):
            self.client.close()
        self.backup.close.assert_called_once()

    def test_healthy_request_does_not_execute_fallback_handler(self):
        handler=Mock(spec=FallbackHandler)
        client=ModelClient(self.primary_factory,handler)
        client.generate('Ticket')
        handler.execute.assert_not_called()

    def test_transient_failure_delegates_to_fallback_handler(self):
        handler=Mock(spec=FallbackHandler)
        client=ModelClient(self.primary_factory,handler)
        self.primary.generate.side_effect=ProviderUnavailableError()
        expected=ProviderResponse(status='completed',output_text='{}')
        handler.execute.return_value=expected
        self.assertIs(client.generate('Ticket'),expected)
        handler.execute.assert_called_once_with('generate','Ticket')
