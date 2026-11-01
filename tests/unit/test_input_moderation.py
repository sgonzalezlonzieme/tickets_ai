import json
import unittest
from unittest.mock import Mock, patch

from tests.support import response_body, ticket_output, provider_response
from clients.openai.open_ai_configs import Settings
from clients.openai.openai_client import OpenAIClient
from entities.response import OpenAIResponse
from services.ticket_service import TicketService, InputRejectedError


def response(text, **kwargs):
    return provider_response(response_body(text, **kwargs))


class InputModerationTests(unittest.TestCase):
    def test_denied_or_invalid_moderation_never_classifies(self):
        cases = [response('{"allowed":false}'), response('{"allowed":"true"}'),
                 response('{}'), response('{"allowed":true,"extra":1}'),
                 response('invalid'), response('', status='incomplete'),
                 response('', refusal=True)]
        for moderation in cases:
            with self.subTest(moderation=moderation.output_text):
                client = Mock()
                client.moderate_input.return_value = moderation
                with patch('services.ticket_service.get_llm_client', return_value=client):
                    with self.assertRaises((ValueError, RuntimeError)):
                        TicketService().classify('Ticket')
                client.generate.assert_not_called()

    def test_moderation_connection_failure_never_classifies(self):
        client = Mock()
        client.moderate_input.side_effect = RuntimeError('Connection failed')
        with patch('services.ticket_service.get_llm_client', return_value=client):
            with self.assertRaises(RuntimeError):
                TicketService().classify('Ticket')
        client.generate.assert_not_called()
