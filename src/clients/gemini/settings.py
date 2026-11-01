from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from clients.errors import ProviderConfigurationError


class GeminiSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(min_length=1, pattern=r"\S")
    max_output_tokens: int = Field(default=4000, gt=0)


@lru_cache(maxsize=1)
def get_gemini_settings() -> GeminiSettings:
    config = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
    try:
        return GeminiSettings.model_validate({
            "model": config.get("GEMINI_MODEL") or "gemini-flash-latest",
            "max_output_tokens": config.get("GEMINI_MAX_OUTPUT_TOKENS", "4000"),
        })
    except ValidationError:
        raise ProviderConfigurationError("Configure GEMINI_MODEL and GEMINI_MAX_OUTPUT_TOKENS.") from None
