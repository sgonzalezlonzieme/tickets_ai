from pydantic import BaseModel, ConfigDict, Field


class OpenAIRequest(BaseModel):

    model_config = ConfigDict(extra="forbid", strict=True)

    # Modelo que se va a consultar.
    model: str = Field(
        min_length=1,
        pattern=r"\S",
        description="Identifier of the OpenAI model to use.",
    )

    # Texto de la consulta.
    input: str = Field(
        min_length=1,
        pattern=r"\S",
        description="Text input sent to the model.",
    )

    # System prompt: rol, tono, idioma o reglas de la respuesta.
    instructions: str = Field(
        min_length=1,
        pattern=r"\S",
        description="General instructions that guide the model response.",
    )

    # Menor valor reduce la variación; incluso 0 no garantiza determinismo.
    temperature: float = Field(
        ge=0,
        le=2,
        description="Sampling temperature; lower values do not guarantee determinism.",
    )

    # Límite de tokens generados, incluidos los de razonamiento.
    max_output_tokens: int = Field(
        gt=0,
        description="Maximum generated tokens, including reasoning tokens when applicable.",
    )

    # Muestreo por probabilidad acumulada; ajustar top_p o temperature.
    top_p: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Nucleus sampling probability; usually tuned instead of temperature.",
    )
