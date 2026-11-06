import logging
from pathlib import Path
from time import perf_counter

from dotenv import dotenv_values
from openai import APIConnectionError, APIStatusError, DefaultHttpxClient, OpenAI
from openai.types.responses import ResponseFormatTextJSONSchemaConfig, ResponseTextConfig
from openai.types.shared import Reasoning
from pydantic import BaseModel, ValidationError

from clients.base import LLMClient
from clients.rate_limit import get_rate_limiter
from clients.errors import ProviderCredentialError, ProviderUnavailableError
from clients.result import ProviderResponse
from entities.request.openai import OpenAIRequest
from entities.response.openai import OutputModerationOutput
from entities.response.openai import OpenAIResponse
from entities.response.openai import TicketOutput
from entities.response.openai import ModerationOutput
from utils.terminal_logging import format_json
from utils.metrics import record_openai_metrics

from .open_ai_configs import Settings
from clients.prompts import get_moderation_instructions, get_output_moderation_instructions


logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        try:
            env_path = Path(__file__).resolve().parents[3] / ".env"
            api_key = dotenv_values(env_path).get("OPENAI_API_KEY")

            if not api_key or not api_key.strip():
                raise ProviderCredentialError("Configure OPENAI_API_KEY in .env.")

            self._http_client = DefaultHttpxClient(
                event_hooks={"request": [get_rate_limiter("openai")]},
            )
            self._client = OpenAI(
                api_key=api_key, timeout=60.0, max_retries=2, http_client=self._http_client,
            )

        except ProviderCredentialError:
            raise
        except Exception:
            if hasattr(self, "_http_client"):
                self._http_client.close()
            logger.exception("Failed to initialize OpenAI client.")
            raise RuntimeError("Failed to initialize OpenAI client.") from None

    def _build_request(self, text: str, *, instructions: str | None = None, output_model: type[BaseModel] = TicketOutput, schema_name: str = "ticket_output") -> OpenAIRequest:
        return OpenAIRequest(
            model=self._settings.model,
            input=text,
            instructions=instructions if instructions is not None else self._settings.instructions,
            text=ResponseTextConfig(
                format=ResponseFormatTextJSONSchemaConfig(
                    type="json_schema",
                    name=schema_name,
                    strict=True,
                    schema=output_model.model_json_schema(),
                )
            ),
            reasoning=(
                Reasoning(effort="max")
                if self._settings.model == "gpt-6-luna"
                else None
            ),
            temperature=(
                None
                if self._settings.model == "gpt-6-luna"
                else self._settings.temperature
            ),
            max_output_tokens=self._settings.max_output_tokens,
        )

    def generate(self, text: str) -> ProviderResponse:
        return self._send(self._build_request(text))

    def generate_structured(self, text: str, *, instructions: str,
                            output_model: type[BaseModel], schema_name: str) -> ProviderResponse:
        """Execute an explicit prompt/contract, including offline-configured eval variants."""
        return self._send(self._build_request(
            text, instructions=instructions, output_model=output_model,
            schema_name=schema_name,
        ))

    def moderate_input(self, text: str) -> ProviderResponse:
        return self._send(self._build_request(
            text, instructions=get_moderation_instructions(), output_model=ModerationOutput,
            schema_name="moderation_output",
        ))

    def moderate_output(self, draft: TicketOutput) -> ProviderResponse:

        text = draft.model_dump_json(include={"answer", "actions"})
        return self._send(self._build_request(
            text, instructions=get_output_moderation_instructions(),
            output_model=OutputModerationOutput,
            schema_name="output_moderation",
        ))

    def _send(self, request: OpenAIRequest) -> ProviderResponse:
        payload = request.model_dump(exclude_none=True, by_alias=True)


        logger.info(
            "OpenAI request\nModel: %s | Reasoning effort: %s | Token limit: %s",
            request.model,
            request.reasoning.effort if request.reasoning else "default",
            request.max_output_tokens,
        )

        logger.debug("Output schema sent to OpenAI:\n%s", format_json(payload["text"]))
        started = perf_counter()
        try:
            response = self._client.responses.create(**payload)
        except APIStatusError as exc:

            logger.error("OpenAI error: type=%s | HTTP=%s", type(exc).__name__, exc.status_code)
            if exc.status_code in {401, 403}:
                raise ProviderCredentialError("OpenAI rejected credentials or access.") from None
            if exc.status_code in {408, 409, 429} or exc.status_code >= 500:
                raise ProviderUnavailableError("OpenAI is temporarily unavailable.") from None
            raise
        except APIConnectionError as exc:

            logger.error("OpenAI connection error: type=%s", type(exc).__name__)
            raise ProviderUnavailableError("OpenAI connection failed.") from None


        latency_s = perf_counter() - started
        data = response.model_dump()
        try:
            parsed = OpenAIResponse.model_validate(data)
        except ValidationError:

            logger.error("Unable to validate OpenAI response envelope.")
            raise


        stage = {
            "moderation_output": "input", "eval_input_moderation": "input",
            "ticket_output": "generation", "eval_input_question": "generation",
            "output_moderation": "output", "eval_output": "output",
        }.get(request.text.format.name, "generation")
        record_openai_metrics(parsed, latency_s, stage=stage, instructions=request.instructions)
        usage = parsed.usage
        logger.info(
            "OpenAI response\n"
            "Status: %s | Model: %s | Duration: %.2f s\n"
            "ID: %s\n"
            "Tokens — input: %s | output: %s | reasoning: %s | total: %s",
            parsed.status,
            parsed.model,
            latency_s,
            parsed.id,
            usage.input_tokens if usage else "N/A",
            usage.output_tokens if usage else "N/A",
            usage.output_tokens_details.reasoning_tokens if usage else "N/A",
            usage.total_tokens if usage else "N/A",
        )
        if parsed.error or parsed.incomplete_details:
            logger.warning(
                "Response details:\n%s",
                "Response failed or was incomplete; body omitted for privacy.",
            )
        if parsed.status == "failed" and parsed.error and parsed.error.code in {
            "server_error", "rate_limit_exceeded",
        }:
            raise ProviderUnavailableError("OpenAI is temporarily unavailable.")
        return ProviderResponse(
            status=parsed.status,
            output_text=parsed.output_text,
            refused=any(
                content.type == "refusal"
                for item in parsed.output if item.type == "message"
                for content in item.content
            ),
        )

    def close(self) -> None:
        try:
            self._client.close()
        finally:
            self._http_client.close()
