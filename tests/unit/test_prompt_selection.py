from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from clients import prompts


class PromptSelectionTests(unittest.TestCase):
    def tearDown(self):
        prompts.get_active_prompts.cache_clear()
        prompts.get_moderation_instructions.cache_clear()
        prompts.get_output_moderation_instructions.cache_clear()

    def test_yaml_selection_resolves_all_active_stages(self):
        prompts.get_active_prompts.cache_clear()
        for stage, filename in prompts.get_active_prompts().items():
            self.assertEqual(prompts._load_instructions(stage), prompts._load_instructions(stage, filename))

    def test_invalid_selection_is_rejected(self):
        cases = [
            'input_moderation: version_4_06_11.yaml\n',
            'input_moderation: ../test.yaml\ninput_question: test.yaml\noutput: test.yaml\n',
            'input_moderation: null\ninput_question: test.yaml\noutput: test.yaml\n',
            'input_moderation: test.txt\ninput_question: test.yaml\noutput: test.yaml\n',
            '- test.yaml\n',
        ]
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'active_prompts.yaml'
            with patch.object(prompts, 'ACTIVE_PROMPTS_PATH', config):
                for text in cases:
                    with self.subTest(text=text):
                        config.write_text(text)
                        prompts.get_active_prompts.cache_clear()
                        with self.assertRaises(ValueError):
                            prompts.get_active_prompts()

    def test_selection_change_is_loaded_after_cache_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'active_prompts.yaml'
            config.write_text('input_moderation: version_4_06_11.yaml\ninput_question: version_7_06_11.yaml\noutput: version_1_01_11.yaml\n')
            with patch.object(prompts, 'ACTIVE_PROMPTS_PATH', config):
                prompts.get_active_prompts.cache_clear()
                first = prompts._load_instructions()
                config.write_text(config.read_text().replace('version_7_06_11', 'version_4_31_10'))
                prompts.get_active_prompts.cache_clear()
                second = prompts._load_instructions()
                self.assertNotEqual(first, second)
                self.assertEqual(second, prompts._load_instructions('input_question', 'version_4_31_10.yaml'))
