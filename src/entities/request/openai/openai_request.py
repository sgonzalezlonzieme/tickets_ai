from openai.types.responses import ResponseTextConfig
from openai.types.shared import Reasoning
from pydantic import BaseModel, ConfigDict, Field


class OpenAIRequest(BaseModel):

    model_config = ConfigDict(extra="forbid", strict=True)


    model: str = Field(
        min_length=1,
        pattern=r"\S",
        description="Identifier of the OpenAI model to use.",
    )


    input: str = Field(
        min_length=1,
        pattern=r"\S",
        description="Text input sent to the model.",
    )


    instructions: str = Field(
        min_length=1,
        pattern=r"\S",
        description="General instructions that guide the model response.",
    )


    reasoning: Reasoning | None = None


    text: ResponseTextConfig | None = None


    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Sampling temperature; lower values do not guarantee determinism.",
    )


    max_output_tokens: int = Field(
        gt=0,
        description="Maximum generated tokens, including reasoning tokens when applicable.",
    )


    top_p: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Nucleus sampling probability; usually tuned instead of temperature.",
    )
