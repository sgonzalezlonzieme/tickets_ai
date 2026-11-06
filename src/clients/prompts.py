from functools import lru_cache
from pathlib import Path
import yaml

ACTIVE_PROMPTS_PATH = Path(__file__).resolve().parents[2] / "prompts" / "active_prompts.yaml"


@lru_cache(maxsize=1)
def get_active_prompts() -> dict[str, str]:
    with ACTIVE_PROMPTS_PATH.open(encoding="utf-8") as source:
        selection = yaml.safe_load(source)
    stages = {"input_moderation", "input_question", "output"}
    if not isinstance(selection, dict) or set(selection) != stages:
        raise ValueError("Active prompts must configure exactly the three pipeline stages.")
    if any(
        not isinstance(name, str) or not name.strip()
        or Path(name).name != name or Path(name).suffix != ".yaml"
        for name in selection.values()
    ):
        raise ValueError("Active prompts must be YAML filenames without directories.")
    return selection


def _load_instructions(folder: str = "input_question", filename: str | None = None) -> str:
    filename = filename if filename is not None else get_active_prompts()[folder]
    prompt_path = (
        Path(__file__).resolve().parents[2]
        / "prompts"
        / folder
        / filename
    )

    # Mantener selección por nombre para el CLI y el runner de evals.
    if not prompt_path.is_file():
        matches = list(prompt_path.parent.rglob(filename))
        if len(matches) != 1:
            raise ValueError("Prompt filename must identify exactly one file in its stage.")
        prompt_path = matches[0]

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
    return _load_instructions("input_moderation")


@lru_cache(maxsize=1)
def get_output_moderation_instructions() -> str:
    return _load_instructions("output")
