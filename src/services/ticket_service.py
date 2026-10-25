from configs import get_openai_client, get_settings
from entities.request import OpenAIRequest


class TicketService:
    def __init__(self) -> None:
        self._settings = get_settings()

    def _build_request(self, text: str) -> OpenAIRequest:
        return OpenAIRequest(
            model=self._settings.model,
            input=text,
            instructions=self._settings.instructions,
            temperature=self._settings.temperature,
            max_output_tokens=self._settings.max_output_tokens,
        )

    def classify(self, text: str) -> str:
        request = self._build_request(text)
        response = get_openai_client().generate(request)

        if response.status != "completed":
            raise RuntimeError("Ticket classification did not complete.")

        return self._validate_category(response.output_text)

    def _validate_category(self, text: str) -> str:
        category = text.strip()

        if category not in {"acceso", "facturacion", "tecnico", "otros"}:
            raise ValueError("Invalid ticket classification response.")

        return category
