# Prompt evaluations with OpenAI or Gemini

The runner compares variants against the same cases for their stage, sequentially.
Select the provider and model in `config.yaml`, independently of `LLM_PROVIDER`,
`OPENAI_MODEL`, and `GEMINI_MODEL` in the CLI configuration. [Configuration](config.yaml).

```yaml
provider: gemini
model: gemini-3.8-flash
max_output_tokens: 4000
```

For OpenAI, use `provider: open_ai` with an OpenAI model such as `gpt-6-luna`.
The included configuration defaults to OpenAI/gpt-6-luna. `max_output_tokens`
is optional and defaults to 4000. `temperature` is optional and defaults to 0.2.
It applies to OpenAI except `gpt-6-luna`, which omits it and uses
`reasoning.effort=max`. Gemini uses its SDK/model default temperature. The
summary stores null for these settings when they are omitted from the request.

Credentials come from the root `.env` file. Provide the key for the selected
provider. Its rate limiter and SDK transport retries apply. Evaluation errors
are attributed to that provider, with **no cross-provider fallback or parsing
retries for invalid JSON**. Running evaluations makes real API calls and consumes
tokens. The configured model must be available to your account.

`--config PATH` selects another configuration. Relative paths are resolved from
the current directory. `--model MODEL_NAME` overrides the model for one run and
takes precedence over the YAML. Configuration is validated before creating a
client. Stage names and the dataset are shared. Each provider uses its own output
contracts for generation and validation.

The default prompts come from `prompts/active_prompts.yaml`, as in the CLI.
`--prompt` compares other variants without activating them.

## Code organization

`runner.py` delegates to `core/cli.py`. Internal modules are grouped in `core/`,
alongside the dataset and documentation at the evals root.

```text
evals/
├── runner.py
├── config.yaml
├── data_set.jsonl
├── README.md
└── core/
    ├── cli.py
    ├── config.py
    ├── providers.py
    ├── stages.py
    ├── dataset.py
    ├── planning.py
    ├── scoring.py
    ├── execution.py
    └── reports.py
```

| File | Responsibility |
| --- | --- |
| [runner.py](runner.py) | Entry point for the existing commands. |
| [core/cli.py](core/cli.py) | Arguments, run coordination, and exit status. |
| [core/config.py](core/config.py) | Validation of the evaluation provider, model, and settings. |
| [core/providers.py](core/providers.py) | Direct provider clients and their output contracts, with fallback disabled. |
| [core/stages.py](core/stages.py) | Project paths and stage configuration, including folder, dataset, and contract. |
| [core/dataset.py](core/dataset.py) | Unified JSONL validation and case selection by stage. |
| [core/planning.py](core/planning.py) | Prompts, cases, limits, and dataset hash, validated before calls. |
| [core/scoring.py](core/scoring.py) | Automatic pass/fail criteria. |
| [core/execution.py](core/execution.py) | Sequential calls, response validation, partial results, and client cleanup. |
| [core/reports.py](core/reports.py) | Run directories and summary configuration and metrics. |

The flow is `runner → core/cli → planning → dataset/prompts → execution → scoring/reports`.
Individual results are written during execution. The summary is written at the
end. All cases remain in the single `data_set.jsonl` file.

Both providers use the same scoring criteria and result formats. The summary
identifies the selected provider (`openai` or `gemini`) and requested model.
Per-case consumption in eval reports and additional quality criteria are pending.
The global metrics files record responses from both providers.

## Commands

Run from the project root. The commands below use macOS/Linux paths. On Windows,
activate the environment and replace `.venv/bin/python` with `python`, or use
`.\.venv\Scripts\python.exe` directly.

```bash
# Classification using the active prompt
.venv/bin/python evals/runner.py --stage input_question

# All three stages with their active prompts, evaluated independently
.venv/bin/python evals/runner.py --all

# Compare specific variants for one stage
.venv/bin/python evals/runner.py --stage input_question \
  --prompt version_3_31_10.yaml --prompt version_4_31_10.yaml

# All versions and stages with a small number of cases
.venv/bin/python evals/runner.py --all --all-prompts --limit 2

# Override the YAML model for one run
.venv/bin/python evals/runner.py --stage input_moderation --model MODEL_NAME
```

`--prompt` accepts a filename. The runner searches the selected stage and its
technique subdirectories. Filenames must be unique within the stage.
`--all-prompts` searches these subdirectories and includes historical versions.
Classifier v1 requests a plain category and is incompatible with the current
JSON contract. Its failures reflect that mismatch and cannot establish relative
model quality. The runner evaluates variants without selecting an active prompt.

## Cases and criteria

| Stage | Dataset | Automatic criterion |
| --- | --- | --- |
| `input_moderation` | `data_set.jsonl` | `allowed` equals `expected_allowed`. |
| `input_question` | `data_set.jsonl` | `category` equals `expected_category`. |
| `output` | `data_set.jsonl` | Every `forbidden_strings` value is absent from `answer` and `actions`, using a case-insensitive comparison. |

Each result must first be complete, unrefused, and valid against its stage's
Pydantic contract. Errors count in the denominator of the pass rate.
The dataset contains 72 cases with an `id` and `stage`, filtered by stage from
one file. There are 40 classification cases, 4 output review cases, and 28 input
moderation cases. The latter include 8 original cases, 16 synthetic attacks,
and 4 legitimate defensive controls to check false positives.

Adversarial cases also include a `scenario` field. The runner currently records
the case index. Coverage includes instruction overrides, role spoofing, prompt
and secret extraction, phishing, unauthorized access, fraud, requests for
third-party data, and attacks mixed with legitimate support. Defensive controls
include phishing reports, credential rotation, account recovery, and an attack
quoted inside a defensive report.

Adversarial cases are stored in `data_set.jsonl` with `stage: input_moderation`
and `expected_allowed: false`. Run them with `--stage input_moderation` or `--all`.
Their expected outcome is input rejection. Add cases to this same JSONL file
with the fields required by their stage.

Category accuracy covers the category field. Answer and action quality require
additional criteria. Removing literal strings alone provides limited evidence
about sensitive-data detection and meaning preservation. Human review and
broader evaluation criteria are still needed. `--all` runs independent stage
checks, with a fixed dataset per stage.

## Results and comparison

Each run creates `metrics/eval_runs/<UTC_timestamp>/` and writes two files.

- `results.jsonl` records the case index, stage, prompt, validity, pass/fail,
  error type, and duration after each case.
- `summary.json` records model settings and metrics per variant, with SHA-256
  hashes of the instructions and dataset to identify the comparison.

Records omit tickets and complete generated responses. Git ignores the default
results directory. `--output-dir PATH` selects another destination. A failed case
allows subsequent cases to continue. An interruption may leave partial results
without a summary. Exit codes are `0` when every case passes, `1` when any case
fails, and `2` for invalid arguments or datasets.

Duration includes rate-limit waits and transport retries. The global `metrics/`
files record tokens and estimated cost for OpenAI and Gemini responses using
`pricing/openai.json` and `pricing/gemini.json`. These fields are still pending
in per-variant summaries and are not linked to case IDs. Eval reports currently
retain pass/fail metrics and duration.

Compare the same model, settings, and cases, then record the evidence and
selection rationale in `CHANGELOG.md`. Model responses can vary between runs,
so a single execution offers limited evidence of a stable improvement.
