"""Execute prepared OpenAI variants sequentially and isolate case failures."""
from collections import Counter
import hashlib
import json
import sys
from time import perf_counter

from clients.openai.openai_client import OpenAIClient
from evals.core.reports import create_run_directory, write_summary
from evals.core.scoring import score
from evals.core.stages import STAGES


def run_variant(client, stage, prompt, instructions, cases, sink):
    """Keep case failures isolated; persist no input or generated response text."""
    counts = Counter()
    elapsed = 0.0
    contract = STAGES[stage].output_model
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



def execute_run(plans, settings, *, output_dir, limit):
    run_id, run_dir = create_run_directory(output_dir)
    summaries = []
    client = OpenAIClient(settings)
    try:
        with (run_dir / "results.jsonl").open("w", encoding="utf-8") as sink:
            for plan in plans:
                summary = run_variant(
                    client, plan.stage, plan.prompt, plan.instructions, plan.cases, sink,
                )
                summary["dataset_sha256"] = plan.dataset_sha256
                summaries.append(summary)
    finally:
        client.close()
    report = write_summary(run_id, run_dir, settings, limit, summaries)
    return report, run_dir
