"""Project paths and the contract associated with each evaluation stage."""
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel
from entities.response.openai import ModerationOutput, TicketOutput, OutputModerationOutput

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class StageConfig:
    folder: str
    dataset: str
    output_model: type[BaseModel]


STAGES = {
    "input_moderation": StageConfig("input_moderation", "data_set.jsonl", ModerationOutput),
    "input_question": StageConfig("input_question", "data_set.jsonl", TicketOutput),
    "output": StageConfig("output", "data_set.jsonl", OutputModerationOutput),
}
