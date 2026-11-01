from configs import get_llm_client
from clients.base import LLMClient
from clients.result import ProviderResponse
from entities.ticket_contracts import TicketOutput
from entities.ticket_contracts import OutputModerationOutput
from entities.ticket_contracts import ModerationOutput


class InputRejectedError(ValueError):
    pass


def _validated_text(response: ProviderResponse) -> str:
    if response.status != "completed":
        raise RuntimeError("Model request did not complete.")
    if response.refused:
        raise RuntimeError("Model refused the request.")
    return response.output_text


class TicketService:
    def classify(self, text: str) -> TicketOutput:
        if not text.strip():
            raise ValueError("Ticket text must not be empty.")

        client: LLMClient = get_llm_client()

        moderation = ModerationOutput.model_validate_json(_validated_text(client.moderate_input(text)))

        if not moderation.allowed:
            raise InputRejectedError("Input rejected by safety moderation.")

        draft = TicketOutput.model_validate_json(_validated_text(client.generate(text)))

        revised = OutputModerationOutput.model_validate_json(
            _validated_text(client.moderate_output(draft))
        )

        return TicketOutput(
            answer=revised.answer, actions=revised.actions,
            category=draft.category, confidence=draft.confidence,
        )
