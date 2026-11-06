import unittest
from unittest.mock import Mock, patch

from clients.base import LLMClient
from clients.errors import ProviderConfigurationError, ProviderCredentialError, ProviderUnavailableError
from configs import clients


class ProviderSelectionTests(unittest.TestCase):
    def tearDown(self):
        clients.get_llm_client.cache_clear()

    def test_config_defaults_and_validates_provider(self):
        for config, expected in [({}, 'open_ai'), ({'LLM_PROVIDER': 'gemini'}, 'gemini'),
                                 ({'LLM_PROVIDER': 'open_ai'}, 'open_ai')]:
            with self.subTest(config=config), patch('configs.clients.dotenv_values', return_value=config):
                self.assertEqual(clients.get_primary_provider(), expected)
        with patch('configs.clients.dotenv_values', return_value={'LLM_PROVIDER': 'invalid'}):
            with self.assertRaises(ProviderConfigurationError):
                clients.get_primary_provider()

    def test_selected_provider_runs_first_and_retries_next_stage(self):
        for selected in ['open_ai', 'gemini']:
            with self.subTest(selected=selected):
                clients.get_llm_client.cache_clear()
                primary, backup = Mock(spec=LLMClient), Mock(spec=LLMClient)
                primary.moderate_input.side_effect = ProviderCredentialError()
                with patch('configs.clients.get_primary_provider', return_value=selected), \
                     patch('configs.clients.get_openai_client', return_value=primary if selected == 'open_ai' else backup), \
                     patch('configs.clients.get_gemini_client', return_value=primary if selected == 'gemini' else backup), \
                     patch('configs.clients.ParsingRetryClient', side_effect=lambda factory, models: factory()):
                    client = clients.get_llm_client()
                    with self.assertLogs(level='INFO') as logs:
                        client.moderate_input('Ticket')
                        client.generate('Ticket')
                    primary.moderate_input.assert_called_once_with('Ticket')
                    backup.moderate_input.assert_called_once_with('Ticket')
                    primary.generate.assert_called_once_with('Ticket')
                    backup.generate.assert_not_called()
                    name = 'Gemini' if selected == 'gemini' else 'OpenAI'
                    self.assertIn(f'Provider={name}', '\n'.join(logs.output))
                    client.close()
