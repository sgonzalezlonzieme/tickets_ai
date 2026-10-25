from typing import Literal

from openai.types.responses import ResponseError, ResponseOutputItem, ResponseUsage
from openai.types.responses.response import IncompleteDetails
from pydantic import BaseModel, ConfigDict, Field


class OpenAIResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    id: str = Field(min_length=1)

    object: Literal["response"]

    created_at: float = Field(ge=0)

    model: str = Field(min_length=1)

    status: Literal[
        "completed", "failed", "in_progress", "cancelled", "queued", "incomplete"
    ] | None = None

    output: list[ResponseOutputItem]

    usage: ResponseUsage | None = None

    error: ResponseError | None = None

    incomplete_details: IncompleteDetails | None = None

    @property
    def output_text(self) -> str:
        return "".join(
            content.text
            for item in self.output
            if item.type == "message"
            for content in item.content
            if content.type == "output_text"
        )
