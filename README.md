# OpenAI M1 Project

A support ticket classification CLI. It accepts a query and writes a validated JSON object to stdout:

```json
{
  "answer": "Podemos revisar el cobro duplicado de tu suscripción.",
  "confidence": 0.98,
  "category": "billing",
  "actions": ["Verificar ambos cobros y evaluar si corresponde un reintegro."]
}
```

All four fields are required. `category` must be `billing`, `technical`, `account`,
or `other`; `confidence` is a number between 0 and 1. `actions` is a list of
suggested actions for a human support agent and may be empty. Additional fields
are rejected. Answers and suggested actions are requested in Spanish, regardless
of the ticket's language.

## Setup and usage

Install dependencies with `python -m pip install -r requirements.txt`.
Copy `.env.example` to `.env` and set `OPENAI_API_KEY` in the project root.

```bash
python src/main.py "I was charged twice for this month's subscription."
python src/main.py --debug "The reporting dashboard returns error 500."
python src/main.py
```

Without a query argument, the CLI prompts for a ticket. Successful runs write only
validated JSON to stdout, even in an interactive terminal. Prompts, diagnostics,
and errors go to stderr, so stdout can be redirected to a JSON file.
Exit codes are `0` for success, `1` for a classification failure, and `130` for
cancellation.

## Project structure

```text
src/
├── main.py                         # CLI entry point and JSON output
├── clients/
│   ├── __init__.py
│   └── openai/
│       ├── __init__.py
│       ├── openai_client.py         # Request construction and SDK calls
│       └── open_ai_configs.py       # Settings and prompt loading
├── configs/                        # Shared client factory and lifecycle
├── entities/
│   ├── request/openai_request.py    # Validated API request
│   └── response/
│       ├── openai_response.py       # API response envelope
│       └── ticket_output.py         # Structured output contract
├── services/ticket_service.py      # Response status and output validation
└── utils/
    ├── terminal_logging.py         # Temporary terminal diagnostics
    └── validation/                 # Shared Pydantic validation
prompts/
├── input_moderation/               # Reserved for input moderation prompts
├── input_question/                 # Existing ticket classification prompts
└── output/                         # Reserved for output prompts
evals/                             # Evaluation data and runner placeholder
metrics_data/                       # Metrics placeholder
tests/                             # Automated tests
.env.example                        # Configuration template
requirements.txt                    # Dependencies
```

## OpenAI client

`TicketService` passes the ticket text to `OpenAIClient.generate(text)`.
The client constructs an `OpenAIRequest` from its settings and sends it through
Responses API. Request fields with a value of `None` are omitted.
The service validates the response status, checks for refusals, and parses the
model's JSON into `TicketOutput`. The CLI serializes that complete validated object.

`src/clients/openai/open_ai_configs.py` reads model settings from `.env` and loads
instructions from `prompts/input_question/version_4_31_10.yaml`. The client factory creates
`OpenAIClient(get_settings())`, reuses the instance, and closes it at shutdown.
The client also reads `OPENAI_API_KEY` from the root `.env`.

`prompts/input_question/version_1_25_10_es.yaml` is a Spanish translation of the
original category-only prompt. The active version still requests the full JSON contract.
Version 4 instructs the model to decline requests unrelated to Nubbix support,
using its own wording in Spanish, `category="other"`, and `actions=[]`. No exact
refusal phrase is required. Valid support
inquiries such as discounts, plans, demos, and documentation remain in scope.

With `gpt-6-luna`, the client sends `reasoning.effort="max"` and omits `temperature`
and `top_p`. `text.format` contains a strict JSON Schema generated from
`TicketOutput`. The schema requires the English keys and category values shown
above. Incomplete responses, refusals, and invalid JSON are treated as failures.

## Temporary logs

Logs marked `TEMP_DEBUG_LOG` show the model, reasoning effort, status, duration,
and token usage. The complete OpenAI response body is logged as indented JSON
before validation, including encrypted content when present. `--debug` also shows
the output schema sent to OpenAI. Colors apply to stderr logs in interactive
terminals; redirected streams and `NO_COLOR` disable colors. JSON on stdout
never contains color codes or a result label.

HTTP errors include their type, status, request ID, and body. Validation errors
include diagnostic details. API keys are not deliberately logged.

The SDK uses `max_retries=2` and `timeout=60.0`. Retryable failures include
connection errors, timeouts, HTTP 408, 409, 429, and 5xx. Avoid adding another
retry loop without accounting for the SDK's retries. The timeout applies to HTTP
operations rather than the entire classification process including retries.
Initialization failures become a `RuntimeError`; API exceptions propagate to the CLI.

## Shared validation

`validate_data()` in `src/utils/validation/` validates objects or JSON with
Pydantic v2. Import examples assume `PYTHONPATH=src`:

```python
from pydantic import BaseModel
from utils.validation import DataValidationError, validate_data

class Person(BaseModel):
    name: str
    age: int

try:
    person = validate_data(Person, '{"name": "Alex", "age": "invalid"}')
except DataValidationError as error:
    print(error.errors)
```

Each error includes `category`, `type`, `loc`, and `msg`. Error categories are
`invalid_json`, `missing_field`, `extra_field`, `invalid_type`, `parsing_error`,
and `invalid_value`. Model conversion rules remain in effect; use
`extra="forbid"` in a model to reject additional fields.

## Evaluation data and tests

`evals/dataset.jsonl` contains 40 Spanish tickets with `input` and
`expected_category`, ten per category. It includes the eight original user-provided
tickets and 32 synthetic examples. Original ticket text is preserved as
customer input; all labels, JSON keys, and category values use English.
The evaluation runner is currently a placeholder.

```bash
python -m unittest discover -s tests -v
```

Tests use mocked SDK responses and make no network calls.

Reference: [Official OpenAI Python SDK documentation](https://developers.openai.com/api/reference/python).
