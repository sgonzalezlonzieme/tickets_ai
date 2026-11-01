import logging
from pathlib import Path
from time import perf_counter

from dotenv import dotenv_values
from google import genai
from google.genai import errors, types
import httpx
from pydantic import BaseModel

from entities.request.gemini import GeminiRequest
from entities.response.gemini import GeminiResponse
from clients.base import LLMClient
from clients.rate_limit import get_rate_limiter
from clients.errors import ProviderConfigurationError, ProviderUnavailableError
from clients.prompts import (
    _load_instructions, get_moderation_instructions, get_output_moderation_instructions,
)
from entities.response.gemini import GeminiModerationOutput as ModerationOutput
from entities.response.gemini import GeminiTicketOutput
from entities.response.gemini import GeminiOutputModerationOutput as OutputModerationOutput
from clients.result import ProviderResponse
from .settings import GeminiSettings

logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):
    def __init__(self, settings: GeminiSettings) -> None:
        self._settings = settings
        config = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
        key = config.get("GEMINI_API_KEY")
        if not key or not key.strip():
            raise ProviderConfigurationError("Configure GEMINI_API_KEY in .env.")
        self._client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(
                timeout=60000,
                client_args={"event_hooks": {"request": [get_rate_limiter("gemini")]}},
                retry_options=types.HttpRetryOptions(attempts=3),
            ),
        )

    def moderate_input(self, text: str) -> ProviderResponse:
        return self._send(text, get_moderation_instructions(), ModerationOutput)

    def generate(self, text: str) -> ProviderResponse:
        return self._send(text, _load_instructions(), GeminiTicketOutput)

    def moderate_output(self, draft: BaseModel) -> ProviderResponse:
        text = draft.model_dump_json(include={"answer", "actions"})
        return self._send(text, get_output_moderation_instructions(), OutputModerationOutput)

    def _send(self, text: str, instructions: str, output_model: type[BaseModel]) -> ProviderResponse:
        started = perf_counter()
        logger.info("Gemini request | Model=%s | Contract=%s", self._settings.model, output_model.__name__)
        request = GeminiRequest(
            model=self._settings.model,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=instructions,
                response_mime_type="application/json",
                response_json_schema=output_model.model_json_schema(),
                max_output_tokens=self._settings.max_output_tokens,
            ),
        )
        try:
            raw_response = self._client.models.generate_content(
                model=request.model, contents=request.contents, config=request.config,
            )
        except errors.APIError as exc:
            logger.error("Gemini error | HTTP=%s", exc.code)
            if exc.code in {408, 409, 429} or (exc.code is not None and exc.code >= 500):
                raise ProviderUnavailableError("Gemini is temporarily unavailable.") from None
            raise ProviderConfigurationError("Gemini rejected the API request; check configuration.") from None
        except (httpx.TransportError, ConnectionError, TimeoutError):
            raise ProviderUnavailableError("Gemini connection failed.") from None

        response = GeminiResponse.model_validate(raw_response.model_dump())
        candidates = response.candidates or []
        blocked = bool(response.prompt_feedback and response.prompt_feedback.block_reason)
        complete = len(candidates) == 1 and candidates[0].finish_reason == types.FinishReason.STOP

        result = ProviderResponse(
            status="completed" if complete and not blocked else "incomplete",
            output_text=response.output_text if complete and not blocked else "",
            refused=blocked or any(c.finish_reason == types.FinishReason.SAFETY for c in candidates),
        )
        usage = response.usage_metadata
        logger.info(
            "Gemini response | Status=%s | Duration=%.2f s | Total tokens=%s",
            result.status, perf_counter() - started,
            usage.total_token_count if usage else "N/A",
        )
        return result

    def close(self) -> None:
        self._client.close()
