from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values

from clients.errors import ProviderConfigurationError

from clients import OpenAIClient
from clients.base import LLMClient
from clients.fallback import FallbackHandler
from clients.model_client import ModelClient
from clients.openai.open_ai_configs import get_settings
from clients.parsing_retry import ParsingRetryClient
from entities.response.openai import RESPONSE_MODELS as OPENAI_RESPONSE_MODELS
from entities.response.gemini import RESPONSE_MODELS as GEMINI_RESPONSE_MODELS


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    return OpenAIClient(get_settings())


@lru_cache(maxsize=1)
def get_gemini_client() -> LLMClient:

    from clients.gemini import GeminiClient
    from clients.gemini.settings import get_gemini_settings

    return GeminiClient(get_gemini_settings())


def get_primary_provider() -> str:
    config = dotenv_values(Path(__file__).resolve().parents[2] / ".env")
    provider = (config.get("LLM_PROVIDER") or "open_ai").strip().lower()
    if provider not in {"open_ai", "gemini"}:
        raise ProviderConfigurationError("Configure LLM_PROVIDER as open_ai or gemini.")
    return provider


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    providers = {
        "open_ai": (get_openai_client, OPENAI_RESPONSE_MODELS, "OpenAI"),
        "gemini": (get_gemini_client, GEMINI_RESPONSE_MODELS, "Gemini"),
    }
    selected = get_primary_provider()
    primary, primary_models, primary_name = providers[selected]
    backup, backup_models, backup_name = providers[
        "gemini" if selected == "open_ai" else "open_ai"
    ]
    return ModelClient(
        lambda: ParsingRetryClient(primary, primary_models),
        FallbackHandler(
            lambda: ParsingRetryClient(backup, backup_models),
            primary_name=primary_name, backup_name=backup_name,
        ),
        primary_name=primary_name,
    )
