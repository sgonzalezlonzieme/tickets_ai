from configs import get_openai_client
from entities.response import TicketOutput


class TicketService:
    def classify(self, text: str) -> TicketOutput:
        response = get_openai_client().generate(text)

        if response.status != "completed":
            raise RuntimeError("Ticket classification did not complete.")

        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "refusal":
                        raise RuntimeError("OpenAI refused ticket classification.")

        return TicketOutput.model_validate_json(response.output_text)
