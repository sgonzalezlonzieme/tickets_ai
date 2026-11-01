from .gemini_response import GeminiResponse
from .moderation_output import GeminiModerationOutput
from .ticket_output import GeminiTicketOutput
from .output_moderation_output import GeminiOutputModerationOutput

RESPONSE_MODELS = {
    "moderate_input": GeminiModerationOutput,
    "generate": GeminiTicketOutput,
    "moderate_output": GeminiOutputModerationOutput,
}

__all__ = ["GeminiResponse", "GeminiModerationOutput", "GeminiTicketOutput", "GeminiOutputModerationOutput", "RESPONSE_MODELS"]
