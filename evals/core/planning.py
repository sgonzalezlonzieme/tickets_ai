"""Resolve and validate all requested cases and prompts before spending tokens."""
from dataclasses import dataclass
import hashlib
from pathlib import Path

from clients.prompts import get_active_prompts, _load_instructions
from evals.core.dataset import load_cases
from evals.core.stages import ROOT, STAGES


@dataclass(frozen=True)
class EvaluationPlan:
    stage: str
    prompt: str
    instructions: str
    cases: list[dict]
    dataset_sha256: str


def build_plans(args) -> list[EvaluationPlan]:
    plans = []
    for stage in STAGES if args.all else [args.stage]:
        config = STAGES[stage]
        dataset_path = ROOT / "evals" / config.dataset
        cases = load_cases(dataset_path, stage)
        digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        if args.all_prompts:
            filenames = sorted(path.name for path in (ROOT / "prompts" / config.folder).rglob("*.yaml"))
        else:
            filenames = args.prompt or [get_active_prompts()[config.folder]]
        for filename in dict.fromkeys(filenames):
            if Path(filename).name != filename or Path(filename).suffix != ".yaml":
                raise ValueError("--prompt must be a YAML filename, without a directory")
            plans.append(EvaluationPlan(
                stage=stage, prompt=filename,
                instructions=_load_instructions(config.folder, filename),
                cases=cases[:args.limit], dataset_sha256=digest,
            ))
    return plans
