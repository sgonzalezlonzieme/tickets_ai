from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    allowed: bool = Field(description="Whether the input is safe to pass to the ticket classifier.")

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

class OutputModerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    answer: str = Field(min_length=1, pattern=r"\S", description="Revised Spanish answer without sensitive data.")
    actions: list[str] = Field(description="Revised Spanish suggestions without sensitive data.")
