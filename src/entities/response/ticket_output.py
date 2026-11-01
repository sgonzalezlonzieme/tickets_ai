from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TicketOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    answer: str = Field(description="A brief Spanish response to the user about their ticket.")
    confidence: float = Field(
        ge=0,
        le=1,
        description="Estimated confidence in the selected category, between 0 and 1.",
    )
    category: Literal["billing", "technical", "account", "other"]
    actions: list[str] = Field(
        description="Suggested actions in Spanish for the human support agent; an empty list if none apply."
    )
