from pydantic import BaseModel, ConfigDict


class ProviderResponse(BaseModel):

    model_config = ConfigDict(extra="forbid", strict=True)

    status: str | None
    output_text: str
    refused: bool = False
