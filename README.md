# OpenAI M1 Project

A Python CLI for Nubbix support tickets. It moderates the input, classifies the
ticket, and reviews the generated response before printing the final JSON.
The primary provider is selected with `LLM_PROVIDER`; OpenAI is the default.
The other provider is the backup for eligible failures.

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
| `LLM_PROVIDER` | `open_ai` (default) or `gemini`; selects the primary provider. |
| `OPENAI_API_KEY` | Required when OpenAI is used, as primary or backup. |
| `OPENAI_MODEL` | OpenAI model; the example uses `gpt-6-luna`. |
| `OPENAI_TEMPERATURE` | Required setting; omitted from requests to `gpt-6-luna`. |
| `OPENAI_MAX_OUTPUT_TOKENS` | Positive token limit for each OpenAI request. |
| `GEMINI_API_KEY` | Required when Gemini is used, as primary or backup. |
| `GEMINI_MODEL` | `.env.example` selects `gemini-3.8-flash`; defaults to `gemini-flash-latest` when absent or empty. |
| `GEMINI_MAX_OUTPUT_TOKENS` | Optional; defaults to `4000` when absent. |
| `OPENAI_REQUESTS_PER_MINUTE` | Optional positive integer; `.env.example` uses `30`; defaults to `10` when absent. |
| `GEMINI_REQUESTS_PER_MINUTE` | Optional positive integer; `.env.example` uses `30`; defaults to `10` when absent. |

Both providers are initialized lazily. The backup key can remain unset while the
primary works.
The model alias can change over time; set an explicit available model if a
fixed model is needed. The client reads configuration from the root `.env`.

## Usage

Elegí el proveedor principal en `.env`:

```dotenv
LLM_PROVIDER=gemini
```

Usá `LLM_PROVIDER=open_ai` para volver a OpenAI. El cambio se aplica en la
próxima ejecución del CLI. El proveedor elegido se intenta primero en las tres
etapas; el otro queda como respaldo ante fallos habilitados. Por eso una prueba
con Gemini puede usar OpenAI si Gemini agota sus reintentos o falla de forma
transitoria. Los diagnósticos de stderr indican qué proveedor atendió cada etapa.


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

After the primary exhausts its parsing budget, `ParsingRetriesExhaustedError`
activates the backup, which has its own three-attempt budget. If both exhaust their
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

For every stage, `ModelClient` calls the selected primary first. If `ProviderUnavailableError`
is raised, it delegates to `FallbackHandler`, which initializes the other provider and executes
the same stage. `FallbackHandler.execute()` is only called on an eligible failure;
it is not part of healthy requests. `ParsingRetryClient` independently handles
invalid model output using the response-model registry for the selected provider.
The next stage attempts the selected primary first again. There is no third provider. A shared parsing retry layer handles invalid model output independently of SDK transport retries.

| Outcome | Behavior |
| --- | --- |
| Primary succeeds | Use its result; backup is not called. |
| Primary connection failure, timeout, HTTP 408/409/429 or 5xx | Try the backup for the same stage after the SDK's own retries. |
| OpenAI response (when primary) with `server_error` or `rate_limit_exceeded` | Try Gemini for that stage. |
| Input rejected, model refusal, or incomplete output | Stop without switching providers. |
| Invalid JSON, missing/extra fields, or wrong types | Initial call plus two parsing retries with the same provider; after the primary exhausts its three attempts, try the backup with its own three-attempt budget. |
| Missing API key, HTTP 401/403, or Gemini HTTP 400 with `API_KEY_INVALID` / `API_KEY_EXPIRED` | Try the backup for the same stage; includes authentication and access failures. |
| Other invalid configuration or nontransient API error | Stop without switching providers. |
| Backup also fails or is not configured when needed | Stop with an error and no final JSON. |

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
├── input_moderation/  # few_shots/, chain_of_thought/
├── input_question/    # zero_shot/, few_shots/, chain_of_thought/
└── output/            # zero_shot/, few_shots/, chain_of_thought/
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

Cada etapa organiza sus versiones en `zero_shot/`, `few_shots/` y
`chain_of_thought/`. Los archivos identifican versión y fecha, sin sufijos de técnica; el CLI y las evals
los buscan por nombre único dentro de la etapa, incluyendo sus subcarpetas.
Entrada y clasificación usan ahora los candidatos few-shot breves para una
prueba manual autorizada; salida conserva zero-shot v1. Las otras variantes
siguen disponibles para comparación. Los candidatos guiados combinan análisis
interno y ejemplos, sin pedir que se muestre razonamiento.
Ver la [revisión completa e inventario](prompts/README.md).

| Stage | File |
| --- | --- |
| Input moderation | `prompts/input_moderation/few_shots/version_4_06_11.yaml` |
| Classification | `prompts/input_question/few_shots/version_7_06_11.yaml` |
| Output review | `prompts/output/zero_shot/version_1_01_11.yaml` |

Instructions are in Spanish; JSON keys and category values stay in English.
La selección está centralizada en [`prompts/active_prompts.yaml`](prompts/active_prompts.yaml),
compartida por ambos proveedores y por los valores predeterminados del runner.
`get_active_prompts()` en `src/clients/prompts.py` lee y valida las tres etapas;
para cambiar de versión editá el YAML, sin modificar código Python.
La próxima ejecución del CLI carga estas versiones; reiniciá cualquier proceso
persistente, ya que las instrucciones y clientes se almacenan en caché.

### Decisión sobre la técnica de prompting

Se prueban few-shot breve para entrada y clasificación, con dos ejemplos por
etapa e instrucciones condensadas. La motivación es comparar una alternativa
más compacta con las bases anteriores (entrada v1 y clasificación v4), sin
atribuir a menor longitud una mejora de calidad o seguridad. Salida mantiene
zero-shot v1 para conservar sus reglas detalladas de privacidad y revisión.

Es una selección para prueba manual, no una superioridad demostrada: la
comparación con los mismos casos y condiciones por proveedor/modelo está
pendiente. No se midieron diferencias de tokens, costo o latencia con modelos.
Las otras variantes siguen candidatas; las bases reemplazadas quedan como
históricas para comparación, con su explicación conservada en el changelog.

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
4 output review cases. `evals/runner.py` is the CLI entry point; dataset loading,
planning, scoring, execution, stage configuration, and reporting live in separate
modules under `evals/core/` (see its README); `core/cli.py` handles arguments and
coordination. The runner filters this single dataset by stage. The OpenAI evaluation runner compares prompt variants sequentially by stage,
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

Every validated OpenAI or Gemini API response envelope appends a record to
[`metrics/`](metrics/), including moderation,
classification, output review, and eval calls. Each stage uses its own file:
`input_moderation.jsonl` (input guardrail), `input_question.jsonl` (classification and response),
and `output_moderation.jsonl` (output guardrail). Existing lines are preserved.
Records contain UTC `timestamp`, `provider` (`openai` or `gemini`), returned `model`, `prompt_tokens`,
`completion_tokens`, `total_tokens`, `latency_s`, and estimated `cost_usd`.
No ticket text, credentials, or response text is stored here.

Ver [cómo leer cada campo](metrics/README.md), con unidades y ejemplos. Los
registros nuevos incluyen `readable` con etiquetas en castellano, duración en
segundos y costo explícito en USD. Los valores originales siguen siendo números:
`cost_usd` se escribe en decimal sin notación científica y `latency_s` con tres
decimales. Comienzan con `system_prompt`, con `stage` (etapa) y `version` (archivo sin
`.yaml`). También incluyen `prompt_file` y `prompt_sha256`, calculados con las
instrucciones efectivamente enviadas (incluidas variantes de evals). Si el archivo
no puede identificarse de forma única, queda null y se conserva la huella.
Los registros históricos no se modifican.

Latency measures the SDK call, including rate-limit waits and transport retries.
A record corresponds to the returned response, not each internal HTTP attempt.
Requests that fail without a validated response cannot provide usage and do not
produce a record. Missing usage is stored as null, not zero. Concurrent local
writers coordinate with a file lock. A validated API envelope is recorded even
if its text later fails the ticket contract or is blocked/incomplete, since the
request may have consumed tokens. Retries can therefore produce multiple records.

For Gemini, `model` uses the returned `model_version`, falling back to the
configured model when absent. `prompt_tokens` comes from `prompt_token_count`,
`completion_tokens` sums `candidates_token_count` and `thoughts_token_count`
(when the latter is absent it adds zero), and `total_tokens` preserves the
provider's `total_token_count`. Missing candidate counts remain null; the total
is not reconstructed from partial counts.

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

Gemini costs use [`pricing/gemini.json`](pricing/gemini.json), with the same
`models` mapping and `input_per_million`, `cached_input_per_million`, and
`output_per_million` fields. Cached input uses `cached_content_token_count`;
output includes thinking tokens. The table includes paid Standard introductory
rates for `gemini-3.8-flash`, verified on 2026-11-06 against the
[official Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash):
USD 0.75 input, USD 0.075 cached input, and USD 3.75 output per million tokens,
through 2026-12-31. Optional `valid_until` prevents using expired rates: expired
or unknown models produce null cost. Google announces higher rates starting
2027-01-01; update and verify the table before then. Estimates assume paid
Standard usage even when the account has free-tier allowance; they are not an
invoice. Existing JSONL records are preserved, including previous null costs.
The table assumes a flat per-token rate for the configured workload; it does not
model context tiers or additional charges.
