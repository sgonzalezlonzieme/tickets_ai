from pydantic import BaseModel, ConfigDict, Field


class OutputModerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    answer: str = Field(min_length=1, pattern=r"\S", description="Revised Spanish answer without sensitive data.")
    actions: list[str] = Field(description="Revised Spanish suggestions without sensitive data.")
