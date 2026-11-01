from pydantic import BaseModel, ConfigDict, Field


class GeminiModerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    allowed: bool = Field(description="Whether the input is safe to pass to the ticket classifier.")
