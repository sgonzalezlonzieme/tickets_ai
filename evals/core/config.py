"""Validated provider/model selection specific to evaluations, without credentials."""
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
import yaml

from evals.core.stages import ROOT

DEFAULT_CONFIG_PATH = ROOT / "evals" / "config.yaml"


class EvalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: Literal["open_ai", "gemini"]
    model: str = Field(min_length=1, pattern=r"\S")
    max_output_tokens: int = Field(default=4000, gt=0)
    temperature: float = Field(default=0.2, ge=0, le=2, allow_inf_nan=False)


def load_eval_config(path: Path = DEFAULT_CONFIG_PATH, *, model: str | None = None) -> EvalConfig:
    with path.open(encoding="utf-8") as source:
        data = yaml.safe_load(source)
    config = EvalConfig.model_validate(data)
    if model is not None:
        config = EvalConfig.model_validate({**config.model_dump(), "model": model})
    return config
