from google.genai import types
from pydantic import BaseModel, ConfigDict


class GeminiResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    candidates: list[types.Candidate] | None
    prompt_feedback: types.GenerateContentResponsePromptFeedback | None = None
    usage_metadata: types.GenerateContentResponseUsageMetadata | None = None

    @property
    def output_text(self) -> str:
        if not self.candidates or not self.candidates[0].content:
            return ""
        return "".join(
            part.text for part in self.candidates[0].content.parts or []
            if part.text is not None and not part.thought
        )
