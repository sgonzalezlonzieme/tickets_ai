import unittest
from unittest.mock import Mock,patch

from clients.base import LLMClient
from configs import clients, services
from clients.lifecycle import close_llm_client, close_openai_client


class SingletonTests(unittest.TestCase):
    def tearDown(self):
        close_llm_client()
        services.get_ticket_service.cache_clear()

    def test_openai_factory_reuses_one_instance(self):
        clients.get_openai_client.cache_clear()
        with patch('configs.clients.OpenAIClient') as constructor, \
             patch('configs.clients.get_settings',return_value=Mock()):
            first=clients.get_openai_client()
            self.assertIs(first,clients.get_openai_client())
            constructor.assert_called_once()
            close_openai_client()
            constructor.return_value.close.assert_called_once()

    def test_model_factory_reuses_instance_without_creating_providers(self):
        close_llm_client()
        with patch('configs.clients.get_openai_client') as primary, \
             patch('configs.clients.get_gemini_client') as backup:
            first=clients.get_llm_client()
            self.assertIs(first,clients.get_llm_client())
            self.assertIsInstance(first,LLMClient)
            primary.assert_not_called()
            backup.assert_not_called()
            close_llm_client()

    def test_service_factory_reuses_one_instance(self):
        services.get_ticket_service.cache_clear()
        with patch('services.TicketService') as constructor:
            first=services.get_ticket_service()
            self.assertIs(first,services.get_ticket_service())
            constructor.assert_called_once()
