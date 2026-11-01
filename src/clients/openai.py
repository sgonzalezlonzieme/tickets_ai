from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI
from openai.types.responses import Response

from entities.request import OpenAIRequest


class OpenAIClient:
    def __init__(self) -> None:
        try:
            env_path = Path(__file__).resolve().parents[2] / ".env"
            api_key = dotenv_values(env_path).get("OPENAI_API_KEY")

            if not api_key or not api_key.strip():
                raise RuntimeError("Failed to initialize OpenAI client.")

            self._client = OpenAI(api_key=api_key, timeout=60.0, max_retries=3)

        except Exception:
            raise RuntimeError("Failed to initialize OpenAI client.") from None


    def generate(self, request: OpenAIRequest) -> Response:
        payload = request.model_dump(exclude_none=True)

        return self._client.responses.create(**payload)

    def close(self) -> None:
        self._client.close()
