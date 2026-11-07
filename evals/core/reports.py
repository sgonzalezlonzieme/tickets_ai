"""Create run directories and persist summary metadata without ticket content."""
from datetime import datetime, timezone
import json


def create_run_directory(output_dir):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_id, run_dir


def write_summary(run_id, run_dir, settings, limit, summaries, *, provider="open_ai"):
    is_openai = provider == "open_ai"
    is_luna = is_openai and settings.model == "gpt-6-luna"
    report = {
        "run_id": run_id, "provider": "openai" if is_openai else "gemini", "model": settings.model,
        "temperature": settings.temperature if is_openai and not is_luna else None,
        "reasoning_effort": "max" if is_luna else None,
        "max_output_tokens": settings.max_output_tokens, "limit": limit,
        "summaries": summaries,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return report
