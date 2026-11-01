from openai.types.responses import ResponseTextConfig
from openai.types.shared import Reasoning
from pydantic import BaseModel, ConfigDict, Field


class OpenAIRequest(BaseModel):

    model_config = ConfigDict(extra="forbid", strict=True)

    # Model to query.
    model: str = Field(
        min_length=1,
        pattern=r"\S",
        description="Identifier of the OpenAI model to use.",
    )

    # User query text.
    input: str = Field(
        min_length=1,
        pattern=r"\S",
        description="Text input sent to the model.",
    )

    # System prompt: role, tone, language, and response rules.
    instructions: str = Field(
        min_length=1,
        pattern=r"\S",
        description="General instructions that guide the model response.",
    )

    # Reasoning effort; "max" requires omitting temperature and top_p.
    reasoning: Reasoning | None = None

    # Structured model output format (text.format).
    text: ResponseTextConfig | None = None

    # Lower values reduce variation; even 0 does not guarantee determinism.
    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Sampling temperature; lower values do not guarantee determinism.",
    )

    # Generated token limit, including reasoning tokens.
    max_output_tokens: int = Field(
        gt=0,
        description="Maximum generated tokens, including reasoning tokens when applicable.",
    )

    # Nucleus sampling; adjust either top_p or temperature.
    top_p: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Nucleus sampling probability; usually tuned instead of temperature.",
    )
