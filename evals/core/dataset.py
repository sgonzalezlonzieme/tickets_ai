"""Validate the unified JSONL dataset and select cases for one stage."""
import json

from entities.response.openai import OutputModerationOutput
from evals.core.stages import STAGES


def load_cases(path, stage):
    cases = []
    seen_ids = set()
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
                if not isinstance(case, dict):
                    raise ValueError()
                case_id = case["id"]
                if not isinstance(case_id, str) or not case_id.strip() or case_id in seen_ids:
                    raise ValueError()
                seen_ids.add(case_id)
                case_stage = case["stage"]
                if case_stage not in STAGES:
                    raise ValueError()
                if case_stage == "output":
                    draft = OutputModerationOutput.model_validate(case["input"])
                    forbidden = case["forbidden_strings"]
                    if not isinstance(forbidden, list) or not forbidden or any(
                        not isinstance(value, str) or not value.strip() for value in forbidden
                    ):
                        raise ValueError()
                    original = draft.model_dump_json().casefold()
                    if any(value.casefold() not in original for value in forbidden):
                        raise ValueError()
                else:
                    if not isinstance(case["input"], str) or not case["input"].strip():
                        raise ValueError()
                    if case_stage == "input_moderation" and type(case["expected_allowed"]) is not bool:
                        raise ValueError()
                    if case_stage == "input_question" and case["expected_category"] not in {
                        "billing", "technical", "account", "other"
                    }:
                        raise ValueError()
                if case_stage == stage:
                    cases.append(case)
            except (ValueError, KeyError, TypeError):
                raise ValueError(f"Invalid case: {path.name}:{line_number}") from None
    if not cases:
        raise ValueError(f"Empty dataset: {path.name}")
    return cases

