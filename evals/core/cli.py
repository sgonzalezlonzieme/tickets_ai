"""Sequential OpenAI or Gemini prompt evaluations. Run from any working directory."""
import argparse
import json
from pathlib import Path
import sys

import yaml

from evals.core.config import DEFAULT_CONFIG_PATH, load_eval_config
from evals.core.providers import get_eval_settings
from evals.core.execution import execute_run
from evals.core.planning import build_plans
from evals.core.stages import ROOT, STAGES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--stage", choices=STAGES)
    selection.add_argument("--all", action="store_true", help="Run all three stages independently")
    parser.add_argument("--prompt", action="append", help="YAML filename in the selected stage folder; repeat to compare")
    parser.add_argument("--all-prompts", action="store_true", help="Compare every YAML version, including legacy contracts")
    parser.add_argument("--limit", type=int, help="Use the first N cases per stage")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Evaluation provider/model YAML")
    parser.add_argument("--model", help="Override the model in the evaluation config")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "metrics" / "eval_runs")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.prompt and (args.all or args.all_prompts):
        parser.error("--prompt requires --stage and cannot be combined with --all-prompts")

    try:
        config = load_eval_config(args.config, model=args.model)
        plans = build_plans(args)
        settings = get_eval_settings(config)
    except (ValueError, OSError, yaml.YAMLError):
        parser.error("Invalid eval configuration, dataset or prompt; check eval files")
    report, run_dir = execute_run(
        plans, settings, output_dir=args.output_dir, limit=args.limit, provider=config.provider,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Results: {run_dir}", file=sys.stderr)
    return int(any(summary["passed"] != summary["total"] for summary in report["summaries"]))

