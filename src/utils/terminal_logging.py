"""TODO: TEMP_DEBUG_LOG — temporary terminal diagnostics."""

import json
import logging
import os
import sys
from textwrap import indent


class TerminalFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[34m",
        logging.INFO: "\033[36m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }

    def __init__(self, use_color: bool) -> None:
        super().__init__("%(message)s")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        level = f"{record.levelname:<7}"
        if self.use_color:
            level = f"{self.COLORS.get(record.levelno, '')}{level}\033[0m"
        header = f"{self.formatTime(record, '%H:%M:%S')} | {level} | {record.name}"
        return f"{header}\n{indent(super().format(record), '  ')}"


def configure_logging(debug: bool = False) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        TerminalFormatter(use_color=sys.stderr.isatty() and "NO_COLOR" not in os.environ)
    )
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        handlers=[handler],
        force=True,
    )
    # Keep SDK/HTTP internals out of the application's diagnostic output.
    for name in ("openai", "httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def format_json(data: object, *, abbreviate_encrypted: bool = True) -> str:
    """Format a log copy; never change the response used for validation."""
    def readable(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: (
                    f"[encrypted content omitted: {len(item)} characters]"
                    if abbreviate_encrypted and key == "encrypted_content" and isinstance(item, str)
                    else readable(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [readable(item) for item in value]
        return value

    return json.dumps(readable(data), indent=2, ensure_ascii=False, default=str)
