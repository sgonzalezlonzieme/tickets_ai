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

Run the commands from the project root, which contains `requirements.txt`.
For an existing environment, start with activation and then install dependencies.

### macOS and Linux

Use a bash or zsh terminal.

1. Create the virtual environment.

```bash
python3 -m venv .venv
```

2. Activate it in the terminal you will use.

```bash
source .venv/bin/activate
```

3. Install the dependencies.

```bash
python -m pip install -r requirements.txt
```

### Windows

PowerShell virtual environment paths use `Scripts`. Create the environment with
Python on each computer to generate the paths for its operating system.

1. Create the virtual environment using the Python launcher.

```powershell
py -m venv .venv
```

2. Activate the environment.

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Install the dependencies.

```powershell
python -m pip install -r requirements.txt
```

Metrics locking detects the system through `os.name` and uses `msvcrt` on
Windows or `fcntl` on macOS/Linux. The suite checks the Windows branch with
mocks and concurrent writes on macOS. Running the suite on an actual Windows
machine is still pending. With WSL, follow the Linux steps using `bin`.

Use the activation command for your Windows terminal.

| Windows terminal | Activation command |
| --- | --- |
| PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Command Prompt (cmd) | `.venv\Scripts\activate.bat` |
| Git Bash | `source .venv/Scripts/activate` |

### Credentials and first run

1. If `.env` does not exist yet, copy `.env.example` using your terminal's command.

| Terminal | Command to create `.env` |
| --- | --- |
| macOS / Linux / WSL / Git Bash | `cp .env.example .env` |
| Windows PowerShell | `Copy-Item .env.example .env` |
| Windows cmd | `copy .env.example .env` |

If the file already exists, edit it and preserve its credentials. Keep it private.

2. Set the provider in `.env` with `LLM_PROVIDER=open_ai` or
   `LLM_PROVIDER=gemini` and its corresponding key, `OPENAI_API_KEY` or
   `GEMINI_API_KEY`. Available variables are listed below.
3. With the environment active on macOS, Linux, or Windows, process a ticket.

```bash
python src/main.py "I was charged twice for this month's subscription."
```

4. Activate the environment again whenever you open another terminal.

Commands in this guide that use `.venv/bin/python` apply to macOS, Linux, and
WSL. The equivalent executable on native Windows is
`.\.venv\Scripts\python.exe`. After activation, `python` selects the environment's
interpreter in the current terminal.

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

Select the primary provider in `.env`.

```dotenv
LLM_PROVIDER=gemini
```

Set `LLM_PROVIDER=open_ai` to switch back to OpenAI. The next CLI execution
loads the change. Each stage tries the selected provider first and uses the
other as backup for eligible failures. A Gemini run can therefore use OpenAI
after retry exhaustion or a transient failure. Diagnostics on stderr identify
the provider used by each stage.


```bash
python src/main.py "I was charged twice for my subscription."
python src/main.py --debug "Payments have not synchronized since this morning."
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
pipeline and prints the application's Spanish rejection message.

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

Each stage groups versions under `zero_shot/`, `few_shots/`, and
`chain_of_thought/`. Filenames identify the version and date. The directory
identifies the technique. The CLI and evals locate each unique filename within
its stage, including subdirectories.
Input moderation and classification use the brief few-shot variants selected
for a manual trial. Output review uses zero-shot v1. Other variants are available
for comparison. Guided candidates combine internal analysis and examples.
Read the complete review and inventory for details. [Prompt review](prompts/README.md).

| Stage | File |
| --- | --- |
| Input moderation | `prompts/input_moderation/few_shots/version_4_06_11.yaml` |
| Classification | `prompts/input_question/few_shots/version_7_06_11.yaml` |
| Output review | `prompts/output/zero_shot/version_1_01_11.yaml` |

Instructions are in Spanish; JSON keys and category values stay in English.
The active selection is shared by both providers and the runner defaults.
`get_active_prompts()` in `src/clients/prompts.py` reads and validates the three
stages. Edit the YAML to select versions. The next CLI execution loads the
selection. Restart persistent processes because instructions and clients are
cached. [Active selection](prompts/active_prompts.yaml).

### Prompting technique decision

Input moderation and classification use brief few-shot candidates with two
examples per stage and condensed instructions. The goal is to compare them with
the previous baselines, input v1 and classification v4. Output review keeps
zero-shot v1 for its detailed privacy and review rules.

The selection supports a manual trial. Comparative model evaluation with the
same cases and conditions is pending. Token use, cost, latency, quality, and
security differences have yet to be measured. Other variants remain candidates.
Replaced baselines are historical references whose explanations are preserved
in the changelog.

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
coordination. The runner filters this single dataset by stage. The evaluation runner selects OpenAI or Gemini and its model in
`evals/config.yaml`, independently of the CLI provider, without fallback. It
compares prompt variants sequentially by stage,
with input and output moderation cases in the same dataset. See [evals/README.md](evals/README.md) for commands,
metrics, and limitations. Running evals makes real API calls; offline tests do not
measure model quality.

## Running evaluations

From the project root, select a provider (`open_ai` or `gemini`) and model in the
eval configuration. Store the corresponding key in `.env` as `OPENAI_API_KEY` or
`GEMINI_API_KEY`. Evaluations use the selected provider directly, independently
of `LLM_PROVIDER`. [Evaluation configuration](evals/config.yaml).

```bash
# Small run using the first two cases from each stage
.venv/bin/python evals/runner.py --all --limit 2

# All cases with one active prompt per stage
.venv/bin/python evals/runner.py --all

# All cases for one stage
.venv/bin/python evals/runner.py --stage input_moderation
.venv/bin/python evals/runner.py --stage input_question
.venv/bin/python evals/runner.py --stage output

# Compare two versions using the same classification cases
.venv/bin/python evals/runner.py --stage input_question \
  --prompt version_4_31_10.yaml --prompt version_7_06_11.yaml

# All versions using two cases per stage and version
.venv/bin/python evals/runner.py --all --all-prompts --limit 2
```

`--limit 2` selects the first two cases of each stage. With one prompt per stage,
`--all --limit 2` normally makes 6 calls. An unrestricted `--all` uses all 72
cases, with 28 input moderation cases, 40 classification cases, and 4 output
review cases. Transport retries can increase HTTP attempts. Each additional
variant runs its stage's cases again. `--all` evaluates stages independently.

The default prompt selection comes from `prompts/active_prompts.yaml`.
`--all-prompts` includes historical versions. Classifier v1 requests a plain
category and is incompatible with the current JSON contract. Its failures
reflect that contract mismatch.

Additional options let you select another configuration, override the model
for one run, or choose a results directory.

```bash
# Another provider/model configuration
.venv/bin/python evals/runner.py --all --config evals/config.yaml

# Another model of the selected provider for this run
.venv/bin/python evals/runner.py --stage input_question --model MODEL_NAME

# Another results directory
.venv/bin/python evals/runner.py --all --limit 2 --output-dir /tmp/my_evals
```

Results are saved under `metrics/eval_runs/<UTC_timestamp>/`.
`results.jsonl` contains the result of each case, and `summary.json` contains
summaries by variant with model and provider information. Git ignores the default
results directory. **These commands make real API calls and consume tokens.**
The unit tests use mocked APIs. See the evaluation guide for scoring criteria
and limitations. [Evaluation guide](evals/README.md).

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

The field guide explains units and examples. New records include `readable`
with Spanish labels, duration in seconds, and an explicit USD cost. The original
fields remain numeric. `cost_usd` uses decimal notation and `latency_s` uses
three decimal places. Records begin with `system_prompt`, containing `stage`
and `version` (the filename without `.yaml`). They also include `prompt_file`
and `prompt_sha256`, based on the actual instructions sent, including eval
variants. If a unique file cannot be identified, its path is null and the hash
is retained. Historical records preserve their original fields and values.
[Metrics field guide](metrics/README.md).

Latency measures the SDK call, including rate-limit waits and transport retries.
A record corresponds to the returned response, not each internal HTTP attempt.
Requests that fail without a validated response cannot provide usage and do not
produce a record. Missing usage is stored as null, not zero. Concurrent local
writers coordinate with a file lock selected by `os.name`: `fcntl.flock` on
macOS/Linux and a shared byte lock via `msvcrt.locking` on Windows. Buffered
writes are flushed before releasing the lock. A validated API envelope is recorded even
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
