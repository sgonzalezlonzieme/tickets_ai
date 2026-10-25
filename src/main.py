import argparse
import sys

from openai import APIError
import yaml

from configs import close_openai_client, get_openai_client, get_settings
from services import TicketService


def read_ticket() -> str:
    parser = argparse.ArgumentParser(description="Classify a support ticket.")
    parser.add_argument("ticket", nargs="?", help="Support ticket text.")
    args = parser.parse_args()

    if args.ticket is not None:
        return args.ticket

    return input("Ticket: ")


def classify_ticket(text: str) -> str:
    service = TicketService()

    return service.classify(text)


def main() -> int:
    try:
        text = read_ticket()

        if not text.strip():
            raise ValueError("Ticket text must not be empty.")

        get_settings()
        get_openai_client()

        category = classify_ticket(text)
        print(category)

        return 0

    except (EOFError, KeyboardInterrupt):
        print("Operation cancelled.", file=sys.stderr)

        return 130

    except (APIError, OSError, ValueError, RuntimeError, yaml.YAMLError):
        print("Unable to classify ticket.", file=sys.stderr)

        return 1

    finally:
        close_openai_client()


if __name__ == "__main__":
    raise SystemExit(main())
