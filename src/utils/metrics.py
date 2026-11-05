"""Append-only, content-free usage metrics for OpenAI responses."""
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = ROOT / "metrics"
STAGE_FILES = {"input": "input_moderation.jsonl", "generation": "input_question.jsonl", "output": "output_moderation.jsonl"}
PRICING_PATH = ROOT / "pricing" / "openai.json"
logger = logging.getLogger(__name__)


def estimate_cost(model, usage):
    if usage is None:
        return None
    with PRICING_PATH.open(encoding="utf-8") as source:
        prices = json.load(source)["models"].get(model)
    if prices is None:
        return None
    cached = usage.input_tokens_details.cached_tokens
    amounts = [usage.input_tokens - cached, cached, usage.output_tokens]
    rates = [Decimal(str(prices[key])) for key in (
        "input_per_million", "cached_input_per_million", "output_per_million"
    )]
    if any(not rate.is_finite() or rate < 0 for rate in rates):
        raise ValueError("Invalid pricing")
    return float(sum(amount * rate for amount, rate in zip(amounts, rates)) / Decimal(1_000_000))


def record_openai_metrics(response, latency_s, *, stage):
    path = METRICS_DIR / STAGE_FILES[stage]
    usage = response.usage
    try:
        cost = estimate_cost(response.model, usage)
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        logger.warning("Unable to calculate metrics cost; storing null.")
        cost = None
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "openai", "model": response.model,
        "prompt_tokens": usage.input_tokens if usage else None,
        "completion_tokens": usage.output_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
        "latency_s": round(latency_s, 3), "cost_usd": cost,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as sink:
            fcntl.flock(sink.fileno(), fcntl.LOCK_EX)
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            sink.flush()
    except OSError:
        logger.warning("Unable to persist usage metrics.")
    return record
