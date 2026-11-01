import argparse
import logging
import sys

from openai import APIError
import yaml

from configs import close_openai_client, get_openai_client, get_settings
from entities.response import TicketOutput
from services import TicketService
from utils.terminal_logging import configure_logging


def read_ticket() -> str:
    parser = argparse.ArgumentParser(description="Classify a support ticket.")
    parser.add_argument("ticket", nargs="?", help="Support ticket text.")
    parser.add_argument("--debug", action="store_true", help="Show extra diagnostics, including the output schema.")
    args = parser.parse_args()

    # TODO: TEMP_DEBUG_LOG — remove temporary diagnostic logging configuration.
    configure_logging(debug=args.debug)

    if args.ticket is not None:
        return args.ticket

    print("Ticket: ", file=sys.stderr, end="", flush=True)
    return input()


def classify_ticket(text: str) -> TicketOutput:
    service = TicketService()

    return service.classify(text)


def main() -> int:
    try:
        text = read_ticket()

        if not text.strip():
            raise ValueError("Ticket text must not be empty.")

        get_settings()
        get_openai_client()

        result = classify_ticket(text)
        print(result.model_dump_json(indent=2))

        return 0

    except (EOFError, KeyboardInterrupt):
        print("Operation cancelled.", file=sys.stderr)

        return 130

    except (APIError, OSError, ValueError, RuntimeError, yaml.YAMLError):
        # TODO: TEMP_DEBUG_LOG — remove diagnostic for errors outside the client.
        logging.getLogger(__name__).exception("Ticket classification failed.")
        print("Unable to classify ticket.", file=sys.stderr)

        return 1

    finally:
        close_openai_client()


if __name__ == "__main__":
    raise SystemExit(main())
