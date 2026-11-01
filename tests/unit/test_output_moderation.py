import json
import unittest
from unittest.mock import Mock, patch

from tests.support import response_body, ticket_output, provider_response
from entities.response import OpenAIResponse
from services.ticket_service import TicketService


def response(text, **kwargs):
    return provider_response(response_body(text, **kwargs))


class OutputModerationTests(unittest.TestCase):
    def client(self):
        client = Mock()
        client.moderate_input.return_value = response('{"allowed":true}')
        client.generate.return_value = response(json.dumps(ticket_output(
            answer='Contact private@example.com', actions=['Use secret-value'])))
        return client

    def test_returns_revised_text_and_preserves_classification(self):
        client = self.client()
        client.moderate_output.return_value = response(json.dumps({
            'answer': 'Contactá al soporte oficial.', 'actions': ['Usá un canal seguro.']}))
        with patch('services.ticket_service.get_llm_client', return_value=client):
            output = TicketService().classify('Ticket')
        self.assertEqual(output.answer, 'Contactá al soporte oficial.')
        self.assertEqual(output.actions, ['Usá un canal seguro.'])
        self.assertEqual(output.category, 'account')
        self.assertEqual(output.confidence, 0.95)
        self.assertEqual([call[0] for call in client.method_calls],
                         ['moderate_input', 'generate', 'moderate_output'])
        self.assertNotIn('private@example.com', output.model_dump_json())

    def test_invalid_or_failed_output_does_not_return_draft(self):
        for body in [response('{}'), response('{"answer":"", "actions":[]}'),
                     response('{"answer":"safe", "actions":[], "category":"other"}'),
                     response('', status='incomplete'), response('', refusal=True)]:
            with self.subTest(body=body.output_text):
                client = self.client()
                client.moderate_output.return_value = body
                with patch('services.ticket_service.get_llm_client', return_value=client):
                    with self.assertRaises((ValueError, RuntimeError)):
                        TicketService().classify('Ticket')

    def test_api_failure_does_not_return_draft(self):
        client = self.client()
        client.moderate_output.side_effect = RuntimeError('Unavailable')
        with patch('services.ticket_service.get_llm_client', return_value=client):
            with self.assertRaises(RuntimeError):
                TicketService().classify('Ticket')
