from .openai_response import OpenAIResponse
from .moderation_output import ModerationOutput
from .ticket_output import TicketOutput
from .output_moderation_output import OutputModerationOutput

RESPONSE_MODELS = {
    "moderate_input": ModerationOutput,
    "generate": TicketOutput,
    "moderate_output": OutputModerationOutput,
}

__all__ = ["OpenAIResponse", "ModerationOutput", "TicketOutput", "OutputModerationOutput", "RESPONSE_MODELS"]
