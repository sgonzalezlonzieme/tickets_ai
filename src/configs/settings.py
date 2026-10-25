from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field
import yaml


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(min_length=1, pattern=r"\S")

    temperature: float = Field(ge=0, le=2, allow_inf_nan=False)

    max_output_tokens: int = Field(gt=0)

    instructions: str = Field(min_length=1, pattern=r"\S")


def _load_instructions() -> str:
    prompt_path = (
        Path(__file__).resolve().parents[2] / "prompts" / "version_1_25_10.yaml"
    )

    with prompt_path.open(encoding="utf-8") as file:
        prompt = yaml.safe_load(file)

    if not isinstance(prompt, dict):
        raise ValueError("Invalid prompt configuration.")

    instructions = prompt.get("instructions")

    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("Invalid prompt instructions.")

    return instructions


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    config = dotenv_values(env_path)

    return Settings.model_validate(
        {
            "model": config.get("OPENAI_MODEL"),
            "temperature": config.get("OPENAI_TEMPERATURE"),
            "max_output_tokens": config.get("OPENAI_MAX_OUTPUT_TOKENS"),
            "instructions": _load_instructions(),
        }
    )
