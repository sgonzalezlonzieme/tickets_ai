import argparse
import logging
import sys

from openai import APIError
import yaml

from clients.lifecycle import close_llm_client
from configs import get_llm_client, get_ticket_service
from entities.ticket_contracts import TicketOutput
from services.ticket_service import InputRejectedError
from utils.terminal_logging import configure_logging


def read_ticket() -> str:
    parser = argparse.ArgumentParser(description="Classify a support ticket.")
    parser.add_argument("ticket", nargs="?", help="Support ticket text.")
    parser.add_argument("--debug", action="store_true", help="Show extra diagnostics, including the output schema.")
    args = parser.parse_args()


    configure_logging(debug=args.debug)

    if args.ticket is not None:
        return args.ticket

    print("Ticket: ", file=sys.stderr, end="", flush=True)
    return input()


def classify_ticket(text: str) -> TicketOutput:
    service = get_ticket_service()

    return service.classify(text)


def main() -> int:
    try:
        text = read_ticket()

        if not text.strip():
            raise ValueError("Ticket text must not be empty.")

        get_llm_client()

        result = classify_ticket(text)
        print(result.model_dump_json(indent=2))

        return 0

    except (EOFError, KeyboardInterrupt):
        print("Operation cancelled.", file=sys.stderr)

        return 130

    except InputRejectedError:
        print("No podemos procesar esta consulta: debe estar relacionada con soporte de Nubbix y cumplir las reglas de seguridad.", file=sys.stderr)
        return 1

    except (APIError, OSError, ValueError, RuntimeError, yaml.YAMLError):

        logging.getLogger(__name__).error("Ticket processing failed; details omitted for privacy.")
        print("Unable to classify ticket.", file=sys.stderr)

        return 1

    finally:
        close_llm_client()


if __name__ == "__main__":
    raise SystemExit(main())
