# OpenAI M1 Project

A Python CLI for Nubbix support tickets. It moderates the input, classifies the
ticket, and reviews the generated response before printing the final JSON.
OpenAI is the primary provider. Gemini is the backup for transient technical
failures.

## Change history

See [CHANGELOG.md](CHANGELOG.md) for the project change history. Update it with
every change to code, prompts, configuration, tests, or documentation, using the
current date and a brief description of the change and its effect.

## Setup

Use a Python virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For an existing environment, activate it and install the requirements without
recreating it. Copy `.env.example` to `.env` only if `.env` does not already exist;
otherwise add missing settings to the existing file, preserving its credentials.
Keep `.env` private.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Required for the primary provider. |
| `OPENAI_MODEL` | Primary model; the example uses `gpt-6-luna`. |
| `OPENAI_TEMPERATURE` | Required setting; omitted from requests to `gpt-6-luna`. |
| `OPENAI_MAX_OUTPUT_TOKENS` | Positive token limit for each OpenAI request. |
| `GEMINI_API_KEY` | Required only when the Gemini backup is used. |
| `GEMINI_MODEL` | Optional; defaults to `gemini-flash-latest` when absent or empty. |
| `GEMINI_MAX_OUTPUT_TOKENS` | Optional; defaults to `4000` when absent. |
| `OPENAI_REQUESTS_PER_MINUTE` | Optional positive integer; defaults to `10`. |
| `GEMINI_REQUESTS_PER_MINUTE` | Optional positive integer; defaults to `10`. |

Gemini is initialized lazily. Its key can remain unset while OpenAI works.
The model alias can change over time; set an explicit available model if a
fixed model is needed. The client reads configuration from the root `.env`.

## Usage

```bash
python src/main.py "Me cobraron dos veces la suscripción."
python src/main.py --debug "Los pagos no se sincronizan desde esta mañana."
python src/main.py
```

Without a ticket argument, the CLI prompts for input. Successful execution prints
only the final validated JSON to stdout. Prompts, diagnostics, and errors go to
stderr, allowing stdout to be redirected to a JSON file.

| Exit code | Meaning |
| --- | --- |
| `0` | All three stages completed successfully. |
| `1` | Rejected input, invalid configuration, or processing failure. |
| `130` | Input cancelled or interrupted. |

## Processing flow

```text
User ticket
    → Input moderation
    → Ticket classification
    → Output review
    → Final JSON
```

Each stage waits for the preceding stage to finish and validates its result.
A healthy successful run makes three model requests. SDK retries and provider
failover can increase the actual number of requests.

### 1. Input moderation

`moderate_input(text)` checks safety and whether the input is related to Nubbix
support. The response must contain exactly one boolean field:

```json
{"allowed": true}
```

Only a validated `true` proceeds to classification. A `false` result stops the
pipeline and prints:

> No podemos procesar esta consulta: debe estar relacionada con soporte de Nubbix y cumplir las reglas de seguridad.

Out-of-scope questions, including harmless veterinary questions, are rejected.
Valid support tickets do not have to mention Nubbix by name. The prompt also
covers instruction override attempts and harmful requests.

### 2. Ticket classification

`generate(text)` produces all four required fields:

```json
{
  "answer": "Podemos revisar los cargos para confirmar si hubo un cobro duplicado.",
  "confidence": 0.98,
  "category": "billing",
  "actions": ["Verificar los cargos de la suscripción."]
}
```

| Field | Contract |
| --- | --- |
| `answer` | Response text requested in Spanish. |
| `confidence` | Number between `0` and `1`. |
| `category` | `billing`, `technical`, `account`, or `other`. |
| `actions` | List of suggested actions in Spanish; may be empty. |

Additional fields and invalid values are rejected. Actions are suggestions for a
human support agent, not operations that have been executed. Confidence is the
model's estimate, not a measured or calibrated probability.

### 3. Output review

`moderate_output(draft)` revises wording and requests removal of personal data,
credentials, and other sensitive information. It receives only the generated
`answer` and `actions`, without resending the original ticket. Its schema requires
exactly those two fields, with a nonempty answer and a list of string actions.

The service combines the revised text with the classifier's original `category`
and `confidence`. If review fails, refuses, is incomplete, or returns invalid
JSON, the unreviewed draft is not printed. Model-based review does not guarantee
that every sensitive value is detected.

## Parsing retries

`ParsingRetryClient` wraps either provider behind the same `LLMClient` interface.
For each stage and provider, it permits three attempts total: the initial model
call plus two retries if Pydantic rejects the JSON or its fields. Every retry
makes a new model call using the same input, instructions, and schema. A valid
response ends the retry loop immediately.

After OpenAI exhausts its parsing budget, `ParsingRetriesExhaustedError` activates
Gemini backup. Gemini has its own three-attempt budget. If both exhaust their
budgets, processing stops without printing a draft. Rejections, refusals,
incomplete responses, configuration errors, and network errors do not trigger
parsing retries; transport failures are handled by SDK retries and failover.
Logs show the stage and attempt number without invalid response contents.
Transport retries can multiply actual HTTP attempts beyond these model-call
budgets. The rate limiter below counts every actual HTTP attempt, including SDK retries.

## Provider interface and backup

`LLMClient` is the abstract interface implemented by `OpenAIClient`, `GeminiClient`,
and `ModelClient`. It defines input moderation, classification, output review,
and cleanup. The service uses this common interface rather than selecting a
provider itself.

For every stage, `ModelClient` calls OpenAI first. If `ProviderUnavailableError`
is raised, it delegates to `FallbackHandler`, which initializes Gemini and executes
the same stage. `FallbackHandler.execute()` is only called on an eligible failure;
it is not part of healthy requests. `ParsingRetryClient` independently handles
invalid model output using the response-model registry for the selected provider.
The next stage attempts OpenAI first again. There is no third provider. A shared parsing retry layer handles invalid model output independently of SDK transport retries.

| Outcome | Behavior |
| --- | --- |
| OpenAI succeeds | Use its result; Gemini is not called. |
| OpenAI connection failure, timeout, HTTP 408/409/429 or 5xx | Try Gemini for the same stage after the SDK's own retries. |
| OpenAI failed response with `server_error` or `rate_limit_exceeded` | Try Gemini for that stage. |
| Input rejected, model refusal, or incomplete output | Stop without switching providers. |
| Invalid JSON, missing/extra fields, or wrong types | Initial call plus two parsing retries with the same provider; after OpenAI exhausts its three attempts, try Gemini with its own three-attempt budget. |
| Invalid credentials, configuration, or nontransient API error | Stop; do not treat it as an outage. |
| Gemini also fails or is not configured when needed | Stop with an error and no final JSON. |

OpenAI uses Responses API with strict JSON Schema generated from Pydantic.
With `gpt-6-luna`, the adapter sends `reasoning.effort="max"` and omits
`temperature` and `top_p`. Its SDK has a 60-second HTTP timeout and two retries.

Gemini uses the official `google-genai` SDK, `models.generate_content`, system
instructions, JSON Schema, and local validation. Its HTTP timeout is 60 seconds
and SDK attempts are limited to three. Retries can increase elapsed time;
there is no overall deadline for the full pipeline.

Both adapters return a neutral `ProviderResponse` containing status, text, and
refusal state. The provider-specific request and response envelopes stay inside
their respective adapters. Only `openai/` and `gemini/` appear as provider subfolders inside
`entities/request/` and `entities/response/`. Each provider has its own request,
API response envelope, and structured output models. OpenAI's existing generated
schemas are unchanged. Gemini uses its own schemas through generation config.
Application-level ticket validation lives in `entities/ticket_contracts.py`; it is not
sent as a shared provider schema. The internal adapter result lives in
`clients/result.py`. Gemini requests and response envelopes are validated before
content is used.

## Rate limiting

`clients/rate_limit/` provides a separate sliding-window limit for each provider.
The default is ten HTTP requests per sixty seconds for OpenAI and ten for Gemini.
All three stages, parsing retries, and SDK transport retries share their provider's
quota. HTTP request hooks reserve a slot immediately before each network attempt.

If the quota is exhausted, the caller waits until a slot expires and then
continues. Waiting does not activate backup. This is a rate limiter, not a circuit
breaker that opens after repeated failures. It does not limit tokens or daily
usage; the account's provider quotas still apply.

Reservations are stored as provider names and timestamps in
`.runtime/rate_limits.sqlite3`, ignored by Git. SQLite transactions coordinate
clients and separate CLI processes using the same project directory. Waiting
happens outside the database transaction. Separate project copies and computers
do not share this quota. The process remains synchronous while waiting.

## Project structure

```text
src/
├── main.py
├── clients/
│   ├── base.py
│   ├── errors.py
│   ├── model_client.py
│   ├── lifecycle.py
│   ├── fallback.py
│   ├── rate_limit/
│   ├── parsing_retry.py
│   ├── prompts.py
│   ├── openai/
│   │   ├── openai_client.py
│   │   └── open_ai_configs.py
│   └── gemini/
│       ├── gemini_client.py
│       └── settings.py
├── configs/
│   ├── clients.py
│   └── services.py
├── entities/
│   ├── request/
│   │   ├── openai/openai_request.py
│   │   └── gemini/gemini_request.py
│   └── response/
│       ├── openai/openai_response.py
│       ├── gemini/gemini_response.py
│       ├── openai/moderation_output.py
│       ├── openai/ticket_output.py
│       ├── openai/output_moderation_output.py
│       ├── gemini/moderation_output.py
│       ├── gemini/ticket_output.py
│       └── gemini/output_moderation_output.py
├── services/ticket_service.py
└── utils/
    ├── terminal_logging.py
    └── validation/
prompts/
├── input_moderation/
├── input_question/
└── output/
tests/
├── unit/
├── integration/
└── support.py
evals/
metrics/
```

`clients/base.py` defines the interface; each provider adapter handles its own SDK.
`clients/model_client.py` handles normal calls and delegates errors to
`clients/fallback.py`. `configs/clients.py` creates cached client instances lazily.
`clients/lifecycle.py` coordinates shutdown and clears client caches. `configs/services.py` provides the cached
`TicketService` instance used by the CLI. Singleton factories are grouped by
layer rather than by provider. `services/ticket_service.py` runs the three
stages and validates their outputs. `clients/prompts.py` loads the shared YAML
instructions.

### Active prompts

| Stage | File |
| --- | --- |
| Input moderation | `prompts/input_moderation/version_1_01_11.yaml` |
| Classification | `prompts/input_question/version_4_31_10.yaml` |
| Output review | `prompts/output/version_1_01_11.yaml` |

Instructions are in Spanish; JSON keys and category values stay in English.
Earlier classification prompts are retained as versions but are not active.

## Diagnostics

Logs identify the stage and provider, request settings, response status, duration,
and token usage where available. Generated text and complete response bodies are
omitted. `--debug` includes the output schema without printing the ticket or draft.
Colors apply to interactive stderr; `NO_COLOR` disables them.

## Validation, tests, and evaluations

Shared Pydantic validation lives in `src/utils/validation/`. `validate_data()`
accepts objects or JSON and raises `DataValidationError` with structured details
that omit the original input. Error categories include invalid JSON, missing or
extra fields, invalid types, parsing errors, and invalid values.

Run all tests, or either group separately:

```bash
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s tests/unit -v
python -B -m unittest discover -s tests/integration -v
```

The suite includes offline unit and integration tests. Unit tests cover contracts, configuration,
validation, provider errors, and isolated service and failover behavior.
Integration tests exercise the CLI, service, provider adapters, real prompt files,
schemas, cleanup, three-stage ordering, and fallback at each stage.

Both SDK boundaries are mocked: tests run offline, require no real API key, and
consume no model tokens. They do not measure live model accuracy, sensitive-data
detection. Dedicated transport tests exercise real SDK retries against local
mock HTTP transports and verify that each attempt passes through the limiter;
they make no external requests. No live Gemini request has been verified.
Update affected tests with behavior changes. See [tests/README.md](tests/README.md).

`evals/data_set.jsonl` contains all 72 eval cases with an `id` and `stage`:
40 classification tickets (ten per category), 28 input moderation cases, and
4 output review cases. The runner filters this single dataset by stage. The OpenAI evaluation runner compares prompt variants sequentially by stage,
with input and output moderation cases in the same dataset. The adversarial dataset
remains a placeholder. See [evals/README.md](evals/README.md) for commands,
metrics, and limitations. Running evals makes real API calls; offline tests do not
measure model quality.

## Official references

- [OpenAI Python API reference](https://developers.openai.com/api/reference/python)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting)

## Persistent usage metrics

Every validated OpenAI response appends a record to
[`metrics/`](metrics/), including moderation,
classification, output review, and eval calls. Each stage uses its own file:
`input_moderation.jsonl` (input guardrail), `input_question.jsonl` (classification and response),
and `output_moderation.jsonl` (output guardrail). Existing lines are preserved.
Records contain UTC `timestamp`, `provider`, returned `model`, `prompt_tokens`,
`completion_tokens`, `total_tokens`, `latency_s`, and estimated `cost_usd`.
No ticket text, credentials, or response text is stored here.

Latency measures the SDK call, including rate-limit waits and transport retries.
A record corresponds to the returned response, not each internal HTTP attempt.
Requests that fail without a validated response cannot provide usage and do not
produce a record. Missing usage is stored as null, not zero. Gemini metrics are
not included yet. Concurrent local writers coordinate with a file lock.

Costs use editable per-model USD/million-token rates from
[`pricing/openai.json`](pricing/openai.json), distinguishing cached
input from other input and output. The initial table covers `gpt-6-luna` at
standard short-context rates from the
[official OpenAI pricing documentation](https://developers.openai.com/api/docs/pricing),
verified on 2026-11-03. Add exact returned model names and current rates when
using another model. Missing or invalid pricing produces `cost_usd: null`.
Estimates exclude tool charges, cache writes, taxes and regional surcharges;
they do not replace the provider invoice. A persistence failure logs a warning
without discarding the ticket response.
