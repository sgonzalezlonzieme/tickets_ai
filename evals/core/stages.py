"""Project paths and the prompt folder and dataset for each evaluation stage."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class StageConfig:
    folder: str
    dataset: str


STAGES = {
    "input_moderation": StageConfig("input_moderation", "data_set.jsonl"),
    "input_question": StageConfig("input_question", "data_set.jsonl"),
    "output": StageConfig("output", "data_set.jsonl"),
}
