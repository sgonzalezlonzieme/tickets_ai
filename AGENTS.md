# Project instructions

## Context and purpose

This project is an AI-assisted support ticket tool for Nubbix, its services, and
integrations. It helps a human agent classify inquiries, draft responses, and
suggest next steps. It currently runs as a Python command-line application (CLI).
Suggested actions require a human agent to execute them.

Each ticket is processed through three sequential stages.

1. The input guardrail checks safety and relevance to Nubbix support.
   Rejection stops processing.
2. Classification and response generation produce `answer`, `category`,
   `confidence`, and `actions`. Categories are `billing`, `technical`, `account`,
   and `other`. Responses and suggestions are written in Spanish.
3. The output guardrail reviews `answer` and `actions` to improve wording and
   remove sensitive information while preserving the original category and confidence.

Select the primary provider through `LLM_PROVIDER=open_ai|gemini` in `.env`,
with OpenAI as the default. The other provider serves as a per-stage fallback
for failures supported by the implementation. These include credential or access
errors (missing keys, HTTP 401/403, and invalid or expired keys identified by
Gemini), transient errors, and exhausted validation retries. Each new stage
tries the selected primary first. Both providers use the shared project prompts.

Pydantic validates the contracts. Print only the final validated JSON. If any
stage fails, never display an unreviewed draft. Diagnostics go to stderr and
must avoid exposing tickets, responses, or credentials.

## Naming convention

- Separate words in project filenames and directories with underscores (`_`).
  Do not use hyphens (`-`). Follow this convention when creating or renaming
  files and update their references.

## Organization and validation

- `src/clients/` contains provider adapters, fallback, retries, and rate limiting.
- `src/services/ticket_service.py` coordinates the three stages.
- `src/entities/` contains data contracts and request/response models.
- `prompts/` contains versioned instructions. `src/clients/prompts.py` selects
  the active versions.
- `pricing/` contains provider prices. `openai.json` and `gemini.json` support
  cost estimates when verified rates exist for the exact model.
- `metrics/` contains shared per-stage JSONL records for OpenAI and Gemini,
  including provider, model, tokens, latency, and estimated cost (null when
  pricing is unavailable). `src/utils/file_lock.py` selects exclusive locking
  through `os.name`, using `fcntl` on macOS/Linux and `msvcrt` on Windows.
  Preserve concurrent-write protection and lock release on errors.
- `tests/` contains unit and integration tests with mocked APIs.
- Keep all eval cases in `evals/data_set.jsonl`, with `id` and `stage` fields.
  Create separate per-stage datasets only at the user's request.
- `evals/` contains the unified dataset and sequential OpenAI or Gemini runner
  for comparing prompt variants by stage. `runner.py` is the minimal entry point
  and `core/cli.py` coordinates the CLI. `core/stages.py`, `core/dataset.py`,
  `core/planning.py`, `core/scoring.py`, `core/execution.py`, and `core/reports.py`
  separate configuration, loading, planning, scoring, execution, and reporting.
  `config.yaml` selects the eval provider/model independently of the CLI.
  `core/config.py` validates it and `core/providers.py` creates a direct client
  with fallback and parsing retries disabled. See `evals/README.md` for commands,
  criteria, and limitations.
- `README.md` describes setup, usage, and current behavior.

For behavior changes, update affected tests and run
`.venv/bin/python -B -m unittest discover -s tests -v`. Tests with mocked APIs
verify functionality. Model quality and guardrail effectiveness with real
requests require separate evaluation.

## Running evals

- Run `.venv/bin/python evals/runner.py` from the project root. Select the
  provider and model in `evals/config.yaml`, independently of `LLM_PROVIDER`,
  and configure its credential in `.env`. Evals use the selected provider directly.
- Use these reference commands.

```bash
# Two cases per stage with active prompts
.venv/bin/python evals/runner.py --all --limit 2

# All 72 cases with active prompts
.venv/bin/python evals/runner.py --all

# One stage, selected from input_moderation, input_question, or output
.venv/bin/python evals/runner.py --stage input_question

# Compare prompt versions for one stage
.venv/bin/python evals/runner.py --stage input_question \
  --prompt version_4_31_10.yaml --prompt version_7_06_11.yaml

# All versions with two cases per stage and version
.venv/bin/python evals/runner.py --all --all-prompts --limit 2
```

- `--limit` takes the first N cases per stage for each variant. Selection follows
  dataset order. The dataset currently contains 28 input, 40 classification, and
  4 output cases. With one prompt per stage, the limited example normally makes
  6 calls and the full run makes 72. Retries and extra variants increase requests.
- `--all` evaluates independent stages. `--all-prompts` includes historical
  versions. Classifier v1 is incompatible with the current JSON contract.
- `--config PATH`, `--model MODEL_NAME`, and `--output-dir PATH` override the
  configuration, model for that run, and output directory respectively.
  The default prompts come from `prompts/active_prompts.yaml`.
- Read `results.jsonl` and `summary.json` under
  `metrics/eval_runs/<UTC_timestamp>/`, which Git ignores. Evals make real API
  calls and consume tokens. Distinguish their results from offline tests, and
  avoid paid runs as routine validation of documentation changes. See the main
  README and `evals/README.md` for full instructions and scoring criteria.

## Current prompt selection

- Use harmless examples in prompts. Use ordinary support inquiries for acceptance
  and unrelated stories, cooking, or general knowledge for scope rejection.
  Do not include demonstrations of violence, aggression, attacks, theft, or
  secret extraction. Preserve safety rules. This example preference does not
  change those rules or demonstrate their effectiveness. Changes to the eval
  dataset for this reason require a specific user request.
- Organize each stage under `prompts/` into `zero_shot/`, `few_shots/`, and
  `chain_of_thought/`, keeping filenames unique per stage. The directory indicates
  the predominant technique. Guided input analysis retains its baseline examples.
  Do not request disclosure of internal reasoning.
- Identify techniques through directories and use version/date filenames without
  technique suffixes. Guided-analysis candidates now include examples and combine
  both techniques.
- Keep `input_moderation/few_shots/version_4_06_11.yaml`,
  `input_question/few_shots/version_7_06_11.yaml`, and
  `output/zero_shot/version_1_01_11.yaml` active. Their selection is stored in
  `prompts/active_prompts.yaml`, read and validated by `src/clients/prompts.py`,
  and shared by both providers and eval defaults.
- Input and classification use brief few-shot variants by user decision.
  Output keeps zero-shot v1 for its detailed privacy rules. The goal is to test
  compact instructions with two examples. Claims of better quality, safety,
  token usage, cost, or latency require comparable measurements.
- Previous input v1 and classification v4 remain historical baselines for
  comparison. Other variants, including guided variants, remain candidates.
  Preserve files, descriptions, and history. Do not change the active selection
  automatically. See `prompts/README.md` for the inventory and length review.
  Character and word counts cannot establish measured token savings or quality.
- Before proposing a replacement, compare the same cases for each stage under
  the same provider/model conditions and record the evidence and decision in
  `CHANGELOG.md`, distinguishing goals from demonstrated results.

## Change history and prompt decisions

- Update `CHANGELOG.md` for every project change, including code, prompts,
  configuration, tests, and documentation.
- Record changes under the current date in `YYYY-MM-DD` format, newest dates
  first. Use existing categories where appropriate.
- Briefly describe the change and its effect. Do not invent historical changes
  or record file-free reviews as modifications.
- Maintain the inventory of every prompt version in `CHANGELOG.md`, with file
  links, stage, differences, and active or historical status. Update it whenever
  a version is added, edited, deleted, or activated, without waiting for a request.
- Preserve each prompt's function, input, output, rules, difference from the
  preceding version, and status. When replacing a version, retain its description
  and replacement rationale as history. Do not delete that information or replace
  previous evidence with new results.
- For every prompt change or selection, record the stage, compared versions,
  problem, introduced difference, evaluation evidence, and decision (active,
  candidate, or discarded), including its rationale in `CHANGELOG.md`.
- Compare candidates using the same cases and provider/model conditions.
  Document quality, safety, contract compliance, and measured cost/latency.
  Distinguish expected improvements from demonstrated improvements. Explicitly
  state when evals are pending. A higher version number alone cannot establish
  that a prompt is better.
