from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return ModelClient(
        lambda: ParsingRetryClient(get_openai_client, OPENAI_RESPONSE_MODELS),
        FallbackHandler(lambda: ParsingRetryClient(get_gemini_client, GEMINI_RESPONSE_MODELS)),
    )
