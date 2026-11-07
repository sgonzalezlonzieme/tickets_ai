"""Append-only, content-free usage metrics for OpenAI and Gemini responses."""
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import yaml
import json
import logging
from pathlib import Path

from utils.file_lock import exclusive_file_lock

ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = ROOT / "metrics"
STAGE_FILES = {"input": "input_moderation.jsonl", "generation": "input_question.jsonl", "output": "output_moderation.jsonl"}
PRICING_PATH = ROOT / "pricing" / "openai.json"
GEMINI_PRICING_PATH = ROOT / "pricing" / "gemini.json"
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


def record_openai_metrics(response, latency_s, *, stage, instructions=None):
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
    return _persist_metrics(record, stage, instructions=instructions)


def _metrics_json(record):
    # JSON numbers stay numeric; decimal notation makes small USD amounts readable.
    fields = []
    for key, value in record.items():
        if key == "cost_usd" and value is not None:
            encoded = format(Decimal(str(value)), "f")
        elif key == "latency_s" and value is not None:
            encoded = format(value, ".3f")
        else:
            encoded = json.dumps(value, ensure_ascii=False)
        fields.append(json.dumps(key) + ": " + encoded)
    return "{" + ", ".join(fields) + "}"


def _readable_metrics(record):
    def tokens(value):
        return "No disponible" if value is None else f"{value} tokens"

    cost = record["cost_usd"]
    return {
        "fecha_utc": datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "proveedor": {"openai": "OpenAI", "gemini": "Gemini"}.get(record["provider"], record["provider"]),
        "modelo": record["model"],
        "system_prompt": (
            record["system_prompt"]["stage"] + " — " +
            (record["system_prompt"]["version"] or "Versión no identificada")
        ),
        "huella_system_prompt": record["prompt_sha256"] or "No disponible",
        "tokens_entrada": tokens(record["prompt_tokens"]),
        "tokens_salida": tokens(record["completion_tokens"]),
        "tokens_totales": tokens(record["total_tokens"]),
        "duracion": f"{record['latency_s']:.3f} segundos",
        "costo_estimado": "No disponible" if cost is None else "USD " + format(Decimal(str(cost)), "f"),
    }


def _prompt_metadata(stage, instructions):
    folder = {"input": "input_moderation", "generation": "input_question", "output": "output"}[stage]
    metadata = {
        "system_prompt": {"stage": folder, "version": None},
        "prompt_file": None, "prompt_sha256": None,
    }
    if instructions is None:
        return metadata
    metadata["prompt_sha256"] = hashlib.sha256(instructions.encode("utf-8")).hexdigest()
    matches = []
    try:
        for path in (ROOT / "prompts" / folder).rglob("*.yaml"):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("instructions") == instructions:
                    matches.append(path.relative_to(ROOT).as_posix())
            except (OSError, ValueError, yaml.YAMLError):
                continue
    except OSError:
        pass
    if len(matches) == 1:
        metadata["prompt_file"] = matches[0]
        metadata["system_prompt"]["version"] = Path(matches[0]).stem
    return metadata


def _persist_metrics(record, stage, *, instructions=None):
    record = {**_prompt_metadata(stage, instructions), **record}
    record["readable"] = _readable_metrics(record)
    path = METRICS_DIR / STAGE_FILES[stage]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as sink:
            with exclusive_file_lock(sink):
                sink.write(_metrics_json(record) + "\n")
    except OSError:
        logger.warning("Unable to persist usage metrics.")
    return record


def record_gemini_metrics(response, latency_s, *, stage, requested_model, instructions=None):
    usage = response.usage_metadata
    model = response.model_version or requested_model
    prompt = usage.prompt_token_count if usage else None
    # Gemini reports generated answer and thinking tokens separately.
    completion = (
        usage.candidates_token_count + (usage.thoughts_token_count or 0)
        if usage and usage.candidates_token_count is not None else None
    )
    total = usage.total_token_count if usage else None
    cost = None
    if prompt is not None and completion is not None:
        try:
            with GEMINI_PRICING_PATH.open(encoding="utf-8") as source:
                prices = json.load(source)["models"].get(model)
            if prices is not None and prices.get("valid_until") is not None:
                if datetime.now(timezone.utc).date() > date.fromisoformat(prices["valid_until"]):
                    logger.warning("Gemini pricing expired; storing null cost.")
                    prices = None
            if prices is not None:
                cached = usage.cached_content_token_count or 0
                amounts = [prompt - cached, cached, completion]
                rates = [Decimal(str(prices[key])) for key in (
                    "input_per_million", "cached_input_per_million", "output_per_million"
                )]
                if cached > prompt or any(amount < 0 for amount in amounts) or any(
                    not rate.is_finite() or rate < 0 for rate in rates
                ):
                    raise ValueError("Invalid pricing or usage")
                cost = float(sum(amount * rate for amount, rate in zip(amounts, rates)) / Decimal(1_000_000))
        except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
            logger.warning("Unable to calculate Gemini metrics cost; storing null.")
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "gemini", "model": model,
        "prompt_tokens": prompt, "completion_tokens": completion,
        "total_tokens": total, "latency_s": round(latency_s, 3), "cost_usd": cost,
    }
    return _persist_metrics(record, stage, instructions=instructions)
