"""Sequential OpenAI prompt evaluations. Run from any working directory."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clients.openai.openai_client import OpenAIClient
from clients.openai.open_ai_configs import get_settings
from clients.prompts import get_active_prompts, _load_instructions
from entities.response.openai import ModerationOutput, TicketOutput, OutputModerationOutput

STAGES = {
    "input_moderation": ("input_moderation", "data_set.jsonl", ModerationOutput),
    "input_question": ("input_question", "data_set.jsonl", TicketOutput),
    "output": ("output", "data_set.jsonl", OutputModerationOutput),
}


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


def score(stage, case, output):
    if stage == "input_moderation":
        return output.allowed == case["expected_allowed"]
    if stage == "input_question":
        return output.category == case["expected_category"]
    text = output.model_dump_json().casefold()
    return all(value.casefold() not in text for value in case["forbidden_strings"])


def run_variant(client, stage, prompt, instructions, cases, sink):
    """Keep case failures isolated; persist no input or generated response text."""
    counts = Counter()
    elapsed = 0.0
    contract = STAGES[stage][2]
    for index, case in enumerate(cases, 1):
        started = perf_counter()
        valid = passed = False
        error = None
        try:
            text = json.dumps(case["input"], ensure_ascii=False) if stage == "output" else case["input"]
            response = client.generate_structured(
                text, instructions=instructions, output_model=contract,
                schema_name=f"eval_{stage}",
            )
            if response.status != "completed" or response.refused:
                raise RuntimeError("Incomplete or refused response")
            output = contract.model_validate_json(response.output_text)
            valid = True
            passed = score(stage, case, output)
        except Exception as exc:
            # Exception messages can contain provider payloads or sensitive data.
            error = type(exc).__name__
        duration = perf_counter() - started
        elapsed += duration
        counts["total"] += 1
        counts["valid"] += int(valid)
        counts["passed"] += int(passed)
        counts["errors"] += int(error is not None)
        sink.write(json.dumps({
            "stage": stage, "prompt": prompt, "case_index": index,
            "valid": valid, "passed": passed, "error": error,
            "duration_seconds": round(duration, 4),
        }, ensure_ascii=False) + "\n")
        sink.flush()
        print(f"{stage} | {prompt} | {index}/{len(cases)} | {'PASS' if passed else 'FAIL'}", file=sys.stderr)
    return {
        "stage": stage, "prompt": prompt,
        "prompt_sha256": hashlib.sha256(instructions.encode()).hexdigest(),
        **dict(counts), "pass_rate": counts["passed"] / counts["total"],
        "valid_rate": counts["valid"] / counts["total"],
        "mean_duration_seconds": elapsed / counts["total"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--stage", choices=STAGES)
    selection.add_argument("--all", action="store_true", help="Run all three stages independently")
    parser.add_argument("--prompt", action="append", help="YAML filename in the selected stage folder; repeat to compare")
    parser.add_argument("--all-prompts", action="store_true", help="Compare every YAML version, including legacy contracts")
    parser.add_argument("--limit", type=int, help="Use the first N cases per stage")
    parser.add_argument("--model", help="Override OPENAI_MODEL")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "metrics" / "eval_runs")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.prompt and (args.all or args.all_prompts):
        parser.error("--prompt requires --stage and cannot be combined with --all-prompts")

    # Validate every dataset and prompt before initializing a client or spending tokens.
    plans = []
    try:
        for stage in STAGES if args.all else [args.stage]:
            folder, dataset, _ = STAGES[stage]
            dataset_path = ROOT / "evals" / dataset
            cases = load_cases(dataset_path, stage)
            digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
            filenames = sorted(p.name for p in (ROOT / "prompts" / folder).rglob("*.yaml")) if args.all_prompts else args.prompt or [get_active_prompts()[folder]]
            for filename in dict.fromkeys(filenames):
                if Path(filename).name != filename or Path(filename).suffix != ".yaml":
                    raise ValueError("--prompt must be a YAML filename, without a directory")
                plans.append((stage, filename, _load_instructions(folder, filename), cases[:args.limit], digest))
    except (ValueError, OSError):
        parser.error("Invalid dataset or prompt configuration; check eval files and prompt filenames")

    settings = get_settings()
    if args.model:
        settings = type(settings).model_validate({**settings.model_dump(), "model": args.model})
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = args.output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    summaries = []
    client = OpenAIClient(settings)
    try:
        with (run_dir / "results.jsonl").open("w", encoding="utf-8") as sink:
            for stage, filename, instructions, cases, digest in plans:
                summary = run_variant(client, stage, filename, instructions, cases, sink)
                summary["dataset_sha256"] = digest
                summaries.append(summary)
    finally:
        client.close()
    report = {"run_id": run_id, "provider": "openai", "model": settings.model,
              "temperature": None if settings.model == "gpt-6-luna" else settings.temperature,
              "reasoning_effort": "max" if settings.model == "gpt-6-luna" else None,
              "max_output_tokens": settings.max_output_tokens, "limit": args.limit,
              "summaries": summaries}
    (run_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Results: {run_dir}", file=sys.stderr)
    return int(any(s["passed"] != s["total"] for s in summaries))


if __name__ == "__main__":
    raise SystemExit(main())
