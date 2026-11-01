from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, ConfigDict, Field


class GeminiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    model: str = Field(min_length=1, pattern=r"\S")
    contents: str = Field(min_length=1, pattern=r"\S")
    config: GenerateContentConfig
