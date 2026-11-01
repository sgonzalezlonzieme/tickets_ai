from contextlib import redirect_stderr, redirect_stdout
import io
import json
import logging
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from clients.openai.open_ai_configs import Settings
from clients.openai.openai_client import OpenAIClient
import main
from services import TicketService


from tests.support import response_body, ticket_output, provider_response


class StructuredOutputTests(unittest.TestCase):
    def setUp(self):
        sdk_patch = patch("clients.openai.openai_client.OpenAI")
        self.sdk = sdk_patch.start().return_value
        self.addCleanup(sdk_patch.stop)
        env_patch = patch(
            "clients.openai.openai_client.dotenv_values",
            return_value={"OPENAI_API_KEY": "test-key"},
        )
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.client = OpenAIClient(
            Settings(
                model="gpt-6-luna",
                temperature=0.2,
                max_output_tokens=4000,
                instructions="Return answer, confidence, category, and actions as JSON in English.",
            )
        )
        self.addCleanup(self.client.close)
        from entities.response import OpenAIResponse
        moderation_patch = patch.object(
            self.client, "moderate_input",
            return_value=provider_response(response_body('{"allowed":true}')),
        )
        output_patch = patch.object(
            self.client, "moderate_output",
            side_effect=lambda draft: provider_response(response_body(
                draft.model_dump_json(include={"answer", "actions"})
            )),
        )
        output_patch.start()
        self.addCleanup(output_patch.stop)
        moderation_patch.start()
        self.addCleanup(moderation_patch.stop)
        factory_patch = patch(
            "services.ticket_service.get_llm_client", return_value=self.client
        )
        factory_patch.start()
        self.addCleanup(factory_patch.stop)
        self.sdk.responses.create.return_value.model_dump.return_value = response_body()

    def test_sends_strict_schema_and_preserves_reasoning_settings(self):
        self.assertEqual(TicketService().classify("I cannot sign in").model_dump(), ticket_output())
        payload = self.sdk.responses.create.call_args.kwargs
        output_format = payload["text"]["format"]
        self.assertEqual(output_format["type"], "json_schema")
        self.assertIs(output_format["strict"], True)
        schema = output_format["schema"]
        self.assertEqual(schema["required"], ["answer", "confidence", "category", "actions"])
        self.assertEqual(set(schema["properties"]), set(schema["required"]))
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(
            schema["properties"]["category"]["enum"],
            ["billing", "technical", "account", "other"],
        )
        self.assertEqual(schema["properties"]["confidence"]["minimum"], 0)
        self.assertEqual(schema["properties"]["confidence"]["maximum"], 1)
        self.assertEqual(schema["properties"]["actions"]["items"]["type"], "string")
        self.assertNotIn("schema_", output_format)
        self.assertEqual(payload["reasoning"], {"effort": "max"})
        self.assertNotIn("temperature", payload)
        self.assertNotIn("top_p", payload)

    def test_returns_each_valid_category(self):
        for category in ("billing", "technical", "account", "other"):
            with self.subTest(category=category):
                self.sdk.responses.create.return_value.model_dump.return_value = response_body(
                    json.dumps(ticket_output(category))
                )
                self.assertEqual(TicketService().classify("Ticket").category, category)

    def test_rejects_invalid_structured_output(self):
        invalid_outputs = [
            ticket_output("unknown"),
            ticket_output(extra=True),
            ticket_output(confidence=-0.1),
            ticket_output(confidence=1.1),
            ticket_output(confidence="0.95"),
            ticket_output(confidence=True),
            ticket_output(answer=123),
            ticket_output(actions="Reset the password"),
            ticket_output(actions=[123]),
        ]
        for key in ticket_output():
            missing_field = ticket_output()
            del missing_field[key]
            invalid_outputs.append(missing_field)
        invalid_texts = ["account", "{}", '{"classification":"account"}']
        invalid_texts.extend(json.dumps(value) for value in invalid_outputs)
        for text in invalid_texts:
            with self.subTest(text=text):
                self.sdk.responses.create.return_value.model_dump.return_value = response_body(text)
                with self.assertRaises(ValidationError):
                    TicketService().classify("Ticket")

    def test_accepts_empty_actions_and_confidence_boundaries(self):
        for confidence in (0, 1):
            with self.subTest(confidence=confidence):
                self.sdk.responses.create.return_value.model_dump.return_value = response_body(
                    json.dumps(ticket_output("other", confidence=confidence, actions=[]))
                )
                self.assertEqual(TicketService().classify("Ticket").category, "other")

    def test_handles_incomplete_response_and_refusal_before_parsing_json(self):
        for body, error in (
            (response_body(text="", status="incomplete"), "did not complete"),
            (response_body(refusal=True), "refused"),
        ):
            with self.subTest(error=error):
                self.sdk.responses.create.return_value.model_dump.return_value = body
                with self.assertRaisesRegex(RuntimeError, error):
                    TicketService().classify("Ticket")

    def test_logs_do_not_expose_unmoderated_body(self):
        body = response_body(json.dumps(ticket_output(answer="private-value@example.com")))
        self.sdk.responses.create.return_value.model_dump.return_value = body
        with self.assertLogs("clients.openai.openai_client", level="INFO") as logs:
            TicketService().classify("Ticket")
        self.assertNotIn("private-value@example.com", "\n".join(logs.output))
        self.assertNotIn("test-encrypted-content", "\n".join(logs.output))

    def run_cli(self, arguments, interactive=False, user_input=""):
        class OutputStream(io.StringIO):
            def isatty(self):
                return interactive

        stdout, stderr = OutputStream(), OutputStream()
        root = logging.getLogger()
        previous_handlers, previous_level = root.handlers[:], root.level
        try:
            with (
                patch("sys.argv", ["main.py", *arguments]),
                patch("sys.stdin", io.StringIO(user_input)),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
                                patch("main.get_llm_client", return_value=self.client),
                patch("main.close_llm_client") as close,
            ):
                exit_code = main.main()
                close.assert_called_once()
            return exit_code, stdout.getvalue(), stderr.getvalue()
        finally:
            for handler in root.handlers:
                handler.close()
            root.handlers = previous_handlers
            root.setLevel(previous_level)

    def test_cli_prints_complete_json_without_labels_or_colors(self):
        for interactive in (False, True):
            with self.subTest(interactive=interactive):
                exit_code, stdout, stderr = self.run_cli(["I cannot sign in"], interactive)
                self.assertEqual(exit_code, 0)
                self.assertEqual(json.loads(stdout), ticket_output())
                self.assertNotIn("\033[", stdout)
                self.assertIn("OpenAI response", stderr)

    def test_interactive_prompt_stays_on_stderr(self):
        exit_code, stdout, stderr = self.run_cli([], user_input="I cannot sign in\n")
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout), ticket_output())
        self.assertIn("Ticket: ", stderr)

    def test_cli_rejects_invalid_output_without_printing_json(self):
        self.sdk.responses.create.return_value.model_dump.return_value = response_body(
            json.dumps(ticket_output("unknown"))
        )
        exit_code, stdout, stderr = self.run_cli(["Test ticket"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Unable to classify ticket.", stderr)



if __name__ == "__main__":
    unittest.main()
