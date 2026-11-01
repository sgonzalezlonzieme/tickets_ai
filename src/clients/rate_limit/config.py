from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel, Field

from .limiter import RateLimiter
from .store import RateLimitStore


class RateLimitSettings(BaseModel):
    requests_per_minute: int = Field(default=10, gt=0)


@lru_cache(maxsize=2)
def get_rate_limiter(provider: Literal["openai", "gemini"]) -> RateLimiter:
    if provider not in {"openai", "gemini"}:
        raise ValueError("Unsupported provider.")
    root = Path(__file__).resolve().parents[3]
    config = dotenv_values(root / ".env")
    setting = f"{provider.upper()}_REQUESTS_PER_MINUTE"
    settings = RateLimitSettings.model_validate({
        "requests_per_minute": config.get(setting, "10"),
    })
    return RateLimiter(provider, settings.requests_per_minute,
                       RateLimitStore(root / ".runtime" / "rate_limits.sqlite3"))
