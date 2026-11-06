"""Entry point for sequential prompt evaluations."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from evals.core.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
