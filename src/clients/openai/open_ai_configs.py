from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field

from clients.prompts import _load_instructions, get_moderation_instructions, get_output_moderation_instructions


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(min_length=1, pattern=r"\S")

    temperature: float = Field(ge=0, le=2, allow_inf_nan=False)

    max_output_tokens: int = Field(gt=0)

    instructions: str = Field(min_length=1, pattern=r"\S")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    config = dotenv_values(env_path)

    return Settings.model_validate(
        {
            "model": config.get("OPENAI_MODEL"),
            "temperature": config.get("OPENAI_TEMPERATURE"),
            "max_output_tokens": config.get("OPENAI_MAX_OUTPUT_TOKENS"),
            "instructions": _load_instructions(),
        }
    )
