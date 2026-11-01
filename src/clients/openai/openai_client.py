import logging
from pathlib import Path
from time import perf_counter

from dotenv import dotenv_values
from openai import APIConnectionError, APIStatusError, OpenAI
from openai.types.responses import ResponseFormatTextJSONSchemaConfig, ResponseTextConfig
from openai.types.shared import Reasoning
from pydantic import ValidationError

from entities.request import OpenAIRequest
from entities.response import OpenAIResponse, TicketOutput
from utils.terminal_logging import format_json

from .open_ai_configs import Settings

# TODO: TEMP_DEBUG_LOG — remove temporary diagnostic logging when error handling is replaced.
logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        try:
            env_path = Path(__file__).resolve().parents[3] / ".env"
            api_key = dotenv_values(env_path).get("OPENAI_API_KEY")

            if not api_key or not api_key.strip():
                raise RuntimeError("OPENAI_API_KEY is missing or empty in .env.")

            self._client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)

        except Exception:
            # TODO: TEMP_DEBUG_LOG — remove initialization diagnostic.
            logger.exception("Failed to initialize OpenAI client.")
            raise RuntimeError("Failed to initialize OpenAI client.") from None

    def _build_request(self, text: str) -> OpenAIRequest:
        return OpenAIRequest(
            model=self._settings.model,
            input=text,
            instructions=self._settings.instructions,
            text=ResponseTextConfig(
                format=ResponseFormatTextJSONSchemaConfig(
                    type="json_schema",
                    name="ticket_output",
                    strict=True,
                    schema=TicketOutput.model_json_schema(),
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

    def generate(self, text: str) -> OpenAIResponse:
        request = self._build_request(text)
        payload = request.model_dump(exclude_none=True, by_alias=True)

        # TODO: TEMP_DEBUG_LOG — remove request summary and timing.
        logger.info(
            "OpenAI request\nModel: %s | Reasoning effort: %s | Token limit: %s",
            request.model,
            request.reasoning.effort if request.reasoning else "default",
            request.max_output_tokens,
        )
        # TODO: TEMP_DEBUG_LOG — remove schema diagnostic.
        logger.debug("Output schema sent to OpenAI:\n%s", format_json(payload["text"]))
        started = perf_counter()
        try:
            response = self._client.responses.create(**payload)
        except APIStatusError as exc:
            # TODO: TEMP_DEBUG_LOG — remove API error body logging.
            logger.error(
                "OpenAI error\nType: %s | HTTP: %s\nRequest ID: %s\nBody:\n%s",
                type(exc).__name__,
                exc.status_code,
                exc.request_id,
                format_json(exc.body) if exc.body is not None else exc.response.text,
            )
            raise
        except APIConnectionError as exc:
            # TODO: TEMP_DEBUG_LOG — remove connection diagnostic.
            logger.error("OpenAI connection error: type=%s", type(exc).__name__)
            raise

        # TODO: TEMP_DEBUG_LOG — remove formatted response body diagnostic.
        data = response.model_dump()
        logger.info(
            "Complete OpenAI response body before validation:\n%s",
            format_json(data, abbreviate_encrypted=False),
        )
        try:
            parsed = OpenAIResponse.model_validate(data)
        except ValidationError:
            # TODO: TEMP_DEBUG_LOG — remove validation diagnostic.
            logger.exception("Unable to validate OpenAI response as OpenAIResponse.")
            raise

        # TODO: TEMP_DEBUG_LOG — remove response summary.
        usage = parsed.usage
        logger.info(
            "OpenAI response\n"
            "Status: %s | Model: %s | Duration: %.2f s\n"
            "ID: %s\nText: %s\n"
            "Tokens — input: %s | output: %s | reasoning: %s | total: %s",
            parsed.status,
            parsed.model,
            perf_counter() - started,
            parsed.id,
            parsed.output_text or "(no text)",
            usage.input_tokens if usage else "N/A",
            usage.output_tokens if usage else "N/A",
            usage.output_tokens_details.reasoning_tokens if usage else "N/A",
            usage.total_tokens if usage else "N/A",
        )
        if parsed.error or parsed.incomplete_details:
            logger.warning(
                "Response details:\n%s",
                format_json({"error": data.get("error"), "incomplete_details": data.get("incomplete_details")}),
            )
        return parsed

    def close(self) -> None:
        self._client.close()
