from functools import lru_cache
from pathlib import Path
import yaml

def _load_instructions(folder: str = "input_question", filename: str = "version_4_31_10.yaml") -> str:
    prompt_path = (
        Path(__file__).resolve().parents[2]
        / "prompts"
        / folder
        / filename
    )

    with prompt_path.open(encoding="utf-8") as file:
        prompt = yaml.safe_load(file)

    if not isinstance(prompt, dict):
        raise ValueError("Invalid prompt configuration.")

    instructions = prompt.get("instructions")

    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("Invalid prompt instructions.")

    return instructions


@lru_cache(maxsize=1)
def get_moderation_instructions() -> str:
    return _load_instructions("input_moderation", "version_1_01_11.yaml")


@lru_cache(maxsize=1)
def get_output_moderation_instructions() -> str:
    return _load_instructions("output", "version_1_01_11.yaml")
