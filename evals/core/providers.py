"""Direct provider adapters for evals; no fallback or parsing retries."""
from clients.gemini.gemini_client import GeminiClient
from clients.gemini.settings import GeminiSettings
from clients.openai.openai_client import OpenAIClient
from clients.openai.open_ai_configs import Settings
from clients.prompts import _load_instructions
from entities.response.gemini import RESPONSE_MODELS as GEMINI_MODELS
from entities.response.openai import RESPONSE_MODELS as OPENAI_MODELS


def get_eval_settings(config):
    if config.provider == "gemini":
        return GeminiSettings(model=config.model, max_output_tokens=config.max_output_tokens)
    return Settings(
        model=config.model, temperature=config.temperature,
        max_output_tokens=config.max_output_tokens, instructions=_load_instructions(),
    )


def create_eval_client(provider, settings):
    if provider == "gemini":
        return GeminiClient(settings)
    if provider == "open_ai":
        return OpenAIClient(settings)
    raise ValueError("Unsupported eval provider.")


def get_output_model(stage, provider):
    operation = {
        "input_moderation": "moderate_input", "input_question": "generate", "output": "moderate_output",
    }[stage]
    if provider not in {"open_ai", "gemini"}:
        raise ValueError("Unsupported eval provider.")
    return (GEMINI_MODELS if provider == "gemini" else OPENAI_MODELS)[operation]
