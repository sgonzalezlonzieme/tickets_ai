# Changelog

Project changes have been recorded since 2026-11-03. Earlier changes are outside
this record.

Record each change under its date (`YYYY-MM-DD`), with the newest dates first.
Use **Added**, **Changed**, **Fixed**, or **Removed** where appropriate, briefly
describing the change and its effect.

The active, candidate, and historical states in each entry describe the state
at that point in time. The current selection is available in the configuration
file. [Active prompts](prompts/active_prompts.yaml).

## Recording prompt decisions

Every prompt change or selection must include the following information.

- **Stage and versions** identify the active file and compared candidate.
- **Problem** describes the case or behavior to improve.
- **Change and expected improvement** explain which instructions differ and why
  they might help.
- **Evidence** identifies the dataset/cases, provider, model, conditions, eval
  results, failures, regressions, and measured cost/latency. State "Pending
  evaluation" when evaluation has not occurred.
- **Decision and rationale** identify the version as active, candidate, or
  discarded and explain the benefits and compromises behind the decision.

Identify eval runs using their `run_id` from `summary.json` and results path
under `metrics/eval_runs/`. Git ignores these files. Keep tickets, responses,
and credentials out of this history.

Compare versions with the same cases and provider/model conditions. Prioritize
safety and contract compliance, then assess response quality and classification.
Document cost or latency tradeoffs. Distinguish expected improvements from
measured results. Version numbering alone provides no evidence of improvement.

## 2026-11-07

### Changed — Spanish CLI example

- Translated the README's subscription billing ticket example into Spanish.

### Removed — obsolete files and evaluation configuration

- Removed the legacy `src/clients/openai.py` module, shadowed by the active
  `src/clients/openai/` package, and the redundant prompt directory `.gitkeep` files.
- Removed the tracked macOS `.DS_Store` artifact and ignored future copies.
- Removed `StageConfig.output_model`, unused by evaluation execution. Updated the
  scoring test to obtain contracts through the provider registry for both OpenAI
  and Gemini.
- Validation passed with all 110 unit and integration tests using simulated APIs.
  Redirected test metrics to a temporary directory.

### Removed — existing usage records

- Cleared the three tracked per-stage metrics files at the user's request,
  removing 43 input moderation, 53 classification, and 17 output review records.
  The empty JSONL files are ready to collect usage from each new repository copy.

### Changed — project instructions and history in English

- Translated `AGENTS.md` and `CHANGELOG.md` into English, including project
  instructions, prompt inventories, decisions, historical explanations, and
  validation records. Checked dates, technical references, links, and documented
  test counts against the original documents.

### Changed — README documentation in English

- Translated the main README and the eval, metrics, prompt, and test guides into
  English, including headings, instructions, tables, and command comments.
  The guide covers macOS/Linux and Windows setup.
- Message examples, support JSON, and readable fields reflect the application's
  Spanish output. Reviewed local links, code blocks, filenames, and runner options.

### Added — Windows-compatible metrics locking

- Added `os.name` selection in `src/utils/file_lock.py`, using `fcntl.flock` on
  macOS/Linux and `msvcrt.locking` on Windows. The writer appends to the same
  JSONL files, protects writes across processes, and flushes before releasing
  the lock. Windows locks a fixed byte even in an empty file and waits while
  another writer holds it.
- Updated the OpenAI and Gemini metrics writer to import the platform's locking
  mechanism when acquiring the lock. Updated Windows installation and execution
  instructions, the metrics guide, and test documentation.
- Validation passed 110 offline tests covering locking branches, contention,
  release on errors, empty files, UTF-8 preservation, and four concurrent
  processes. Actual execution used macOS. The Windows branch was mocked.
  Validation on an actual Windows machine is pending.

### Changed — installation steps by platform

- Split README setup into macOS/Linux and Windows PowerShell steps, including
  cmd and Git Bash activation alternatives, initial `.env` copying, credentials,
  and the first run.
- Documented the then-current Unix requirement from `fcntl` in metrics and WSL
  execution on Windows. Distinguished Unix/WSL `bin` paths from native Windows
  `Scripts` paths. Checked the documentation against the code and reviewed the diff.

### Changed — virtual environment activation by operating system

- Documented README activation commands for macOS/Linux and Windows using
  PowerShell, cmd, or Git Bash. Clarified the Windows Python executable path
  for interpreting application and eval commands.

### Changed — evaluation traceability

- Clarified how to reference a run using `run_id` and its results directory when
  documenting decisions, while keeping sensitive content out of the changelog.
  This documentation update changed no code and executed no evals.

### Added

- Added eval execution instructions to the main README and `AGENTS.md`, covering
  provider/model selection, credentials, stage/all-stage commands, variant
  comparisons, `--limit`, case counts, and result paths. Clarified real API use,
  disabled eval fallback, and incompatible historical versions. Removed the
  obsolete README reference to a separate adversarial dataset. This documentation
  change executed no real evals and changed no code.
- Added independent eval configuration in `evals/config.yaml` for provider
  (`open_ai` or `gemini`), model, output limit, and OpenAI temperature. The initial
  selection is OpenAI/gpt-6-luna, independent of `LLM_PROVIDER` and CLI model
  settings. `--config` selects another YAML and `--model` overrides the model
  for one run. [Eval configuration](evals/config.yaml).
- `evals/core/config.py` validates settings before client initialization.
  `providers.py` creates only the selected provider with its contracts. Gemini
  adds `generate_structured` to evaluate explicit instructions for all three
  stages and record metrics, matching OpenAI's evaluation entry point.
- The runner retains sequential execution, scoring criteria, and one dataset.
  Provider failures are attributed to the selected provider with cross-provider
  fallback and parsing retries disabled. SDK transport retries and rate limits
  still apply. The summary records the requested provider/model and effective
  settings. Omitted Gemini temperature and reasoning-effort settings are null.
- Updated documentation and project instructions. Mocked SDK tests cover both
  providers, all three Gemini stages, invalid configuration, model override
  precedence, cleanup, and disabled fallback. Prompts, active selection, and
  dataset were preserved. This implementation made no real API calls or model
  quality/safety evaluations. Prompt comparisons remain pending under matching
  provider/model conditions. Validation passed 104 offline tests and checked
  command help.

## 2026-11-06

### Changed — interpreting historical prompt status

- Clarified that each entry's status applies at the time of the change and
  linked the current selection to distinguish historical versions from active
  prompts. This documentation change preserved prompt instructions.

### Changed — rate-limit configuration explanation

- Clarified in the README table that `.env.example` uses 30 RPM for both
  providers while omitted variables default to 10 RPM. Documentation-only
  change with no API calls.

### Changed — local limit of 30 requests per minute

- Set `OPENAI_REQUESTS_PER_MINUTE=30` and `GEMINI_REQUESTS_PER_MINUTE=30` in the
  local `.env` and `.env.example` at the user's request. Omitted variables still
  default to 10 RPM, and provider quotas still apply. Verified both files load
  correctly without real API calls.

### Changed — eval internals grouped under core

- Grouped evaluation helpers in `evals/core/` and moved argument handling and
  coordination into `core/cli.py`. `evals/runner.py` became a minimal 12-line
  entry point compatible with the existing command and execution from other
  directories. Updated imports and project-root resolution.
- Preserved the dataset, criteria, provider, prompts, report formats, and runner
  behavior. Updated tests and documentation for the new structure, retaining
  the history of the earlier split. Validation passed 99 offline tests, with
  no real API calls.

### Changed — evaluation runner split into modules

- Reduced `evals/runner.py` to arguments and coordination. Moved responsibilities
  into `stages.py` for paths/contracts, `dataset.py` for unified dataset validation,
  `planning.py` for selection and preflight validation, `scoring.py` for criteria,
  `execution.py` for calls, per-case results and cleanup, and `reports.py` for
  run directories and summaries. Configuration and plans use named fields.
- Preserved commands, options, sequence, pass/fail criteria, file formats, error
  isolation, and then-exclusive OpenAI execution. Kept `evals/data_set.jsonl`
  unified and preserved active prompts. This refactor executed no evals.
- Adapted tests to their responsible modules while preserving coverage of
  contracts, scoring, IDs, privacy, shared defaults, and errors. Added a `--help`
  check from another directory without real calls. Documented responsibilities
  and flow in the README and project instructions.
- Validation passed 99 offline tests. Mocked-provider tests provide evidence of
  functionality rather than model quality or safety.

### Changed — prompt selection stored alongside prompt files

- Moved version selection from a Python dictionary to a YAML file.
  `get_active_prompts()` validates exactly three stages and YAML filenames
  without directories. Loading is deferred and cached per process.
  [Selection file](prompts/active_prompts.yaml).
- Both CLI providers and runner defaults read the same configuration, removing
  duplicated version names from Python. Restart the process after changing
  the YAML. Explicit eval variants remain available for comparison.
- Preserved the active selection and instructions. Brief few-shot input v4,
  brief few-shot classification v7, and zero-shot output v1 remain selected
  for the authorized manual trial. Candidates and history were retained.
  This move adds no model quality, safety, cost, or latency evidence.
- Updated the README, prompt guide, evals, and project instructions. Added tests
  for invalid configuration, loading, and selection changes. Validation passed
  98 offline tests without real API calls.

### Changed — manual activation of input v4 and classification v7

| Stage | Replaced baseline | Active selection | Decision and rationale |
| --- | --- | --- | --- |
| Input | [v1 few-shot](prompts/input_moderation/few_shots/version_1_01_11.yaml) | [v4 brief few-shot](prompts/input_moderation/few_shots/version_4_06_11.yaml) | Active for the authorized manual trial, using condensed rules and two harmless examples to compare a compact alternative. |
| Classification | [v4 zero-shot](prompts/input_question/zero_shot/version_4_31_10.yaml) | [v7 brief few-shot](prompts/input_question/few_shots/version_7_06_11.yaml) | Active for the authorized manual trial, using summarized contracts/categories and two examples. Savings and quality remain pending evaluation. |
| Output | Preserved | [v1 zero-shot](prompts/output/zero_shot/version_1_01_11.yaml) | Remains active for its detailed privacy and review rules. |

- The goal is to test the recommended combination with the user's real workflow.
  All three stages retain their purpose and contracts. This selection edits no
  prompt file. Replaced baselines become historical references, and remaining
  variants retain candidate status and their earlier descriptions.
- Centralized selection in `ACTIVE_PROMPTS` in `src/clients/prompts.py`, shared
  by OpenAI, Gemini, and runner defaults. Updated documentation, inventory,
  and project instructions.
- Model comparison remains pending using the same `evals/data_set.jsonl` cases,
  provider/model, and settings. User-authorized activation establishes no
  measured quality, safety, token, cost, or latency improvement. Implementation
  made no real API calls. Validation passed 96 offline tests, including shared
  CLI/runner prompt selection.

### Changed — harmless examples throughout prompts

- Reviewed all 24 prompt files. At the user's request, replaced examples of
  harm, intrusion, secret extraction, and authentication requests with stories,
  cooking, general knowledge, or ordinary support. Output review examples cover
  wording, guidance, and unsupported claims. Harmless privacy examples retain
  fictional data.
- Active input v1 and derived candidates replace the veterinary example with
  an unrelated pirate story. The then-active selection remains input v1,
  classification v4, and output v1, with their safety, scope, and contract rules.
  Input v1 content changes, producing a new instruction hash in future metrics.
- Rejection illustrations were stronger than necessary to demonstrate scope.
  The intended difference is simpler, readable examples. Quality and safety
  improvements remain unproven. Earlier descriptions preserve the history of
  replaced examples and previous results.
- Updated inventory and lengths in `prompts/README.md`, the preference in
  `AGENTS.md`, and the README. Preserved `evals/data_set.jsonl`, whose evaluation
  coverage serves a different purpose from illustrative prompt examples.

**Files and decision**

The files below update examples within the same versions at the user's explicit
request. Input v1 remains active at this point, with the others retained as
candidates. Compare each stage's active prompt and candidates using matching
cases, provider/model, and conditions. Comparative model evaluation remains
pending. Quality, safety, token usage, cost, and latency differences were not
measured, and no real calls were made. Validation checked 24 YAML files,
63 valid illustrative outputs, and 95 passing offline tests.

- [prompts/output/chain_of_thought/version_7_06_11.yaml](prompts/output/chain_of_thought/version_7_06_11.yaml).
- [prompts/output/chain_of_thought/version_3_06_11.yaml](prompts/output/chain_of_thought/version_3_06_11.yaml).
- [prompts/output/chain_of_thought/version_6_06_11.yaml](prompts/output/chain_of_thought/version_6_06_11.yaml).
- [prompts/output/few_shots/version_5_06_11.yaml](prompts/output/few_shots/version_5_06_11.yaml).
- [prompts/output/few_shots/version_2_06_11.yaml](prompts/output/few_shots/version_2_06_11.yaml).
- [prompts/input_moderation/chain_of_thought/version_7_06_11.yaml](prompts/input_moderation/chain_of_thought/version_7_06_11.yaml).
- [prompts/input_moderation/chain_of_thought/version_3_06_11.yaml](prompts/input_moderation/chain_of_thought/version_3_06_11.yaml).
- [prompts/input_moderation/chain_of_thought/version_6_06_11.yaml](prompts/input_moderation/chain_of_thought/version_6_06_11.yaml).
- [prompts/input_moderation/few_shots/version_5_06_11.yaml](prompts/input_moderation/few_shots/version_5_06_11.yaml).
- [prompts/input_moderation/few_shots/version_1_01_11.yaml](prompts/input_moderation/few_shots/version_1_01_11.yaml).
- [prompts/input_moderation/few_shots/version_2_06_11.yaml](prompts/input_moderation/few_shots/version_2_06_11.yaml).
- [prompts/input_moderation/few_shots/version_4_06_11.yaml](prompts/input_moderation/few_shots/version_4_06_11.yaml).

### Added — separate variants and prompt length review

- Reviewed all 24 existing and new prompts in `prompts/README.md`, with a complete
  inventory, status, character counts, and word counts. Retained active versions,
  historical versions, earlier candidates, and their modification history.
- Added twelve files with brief variants (two examples) and extended variants
  (four examples and boundary guidance), by technique and stage. Examples differ
  between files. Filenames contain version/date and directories identify technique.

| Stage and comparison | Brief / extended few-shot | Brief / extended guided analysis | Differences and intended problem |
| --- | --- | --- | --- |
| Input with active v1 and previous v2/v3 | [v4](prompts/input_moderation/few_shots/version_4_06_11.yaml) / [v5](prompts/input_moderation/few_shots/version_5_06_11.yaml) | [v6](prompts/input_moderation/chain_of_thought/version_6_06_11.yaml) / [v7](prompts/input_moderation/chain_of_thought/version_7_06_11.yaml) | Condensed safety/scope core and distinct examples covering support, unrelated health questions, documentation, employment, secret extraction, fraud, defensive reports, and instruction changes. Extended variants clarify intent and mixed requests. |
| Classification with active v4 and previous v5/v6 | [v7](prompts/input_question/few_shots/version_7_06_11.yaml) / [v8](prompts/input_question/few_shots/version_8_06_11.yaml) | [v9](prompts/input_question/chain_of_thought/version_9_06_11.yaml) / [v10](prompts/input_question/chain_of_thought/version_10_06_11.yaml) | Consolidated categories, contract, and language rules, reducing rejection-rule repetition. Distinct examples cover refunds, hours, access, failures, invoices, guides, permissions, plans, and unrelated subjects. Extended variants clarify the main need and uncertain confidence. |
| Output with active v1 and previous v2/v3 | [v4](prompts/output/few_shots/version_4_06_11.yaml) / [v5](prompts/output/few_shots/version_5_06_11.yaml) | [v6](prompts/output/chain_of_thought/version_6_06_11.yaml) / [v7](prompts/output/chain_of_thought/version_7_06_11.yaml) | Grouped privacy, safety, and contract rules. Distinct examples cover contact information, identity, invented discounts, secrets, personal data, and unconfirmed deadlines. Extended variants check both fields and avoid new promises. |

**Function, input, output, and rules**

The contracts and purposes remain those in the previous inventory. Input maps a
ticket to `allowed`. Classification maps a ticket to its four fields. Output
maps a draft to revised `answer`/`actions`. Review receives neither category
nor confidence and requests only the final result. Guided variants include
examples and combine techniques. Brief variants reduce repetition, while extended
variants add criteria and expected coverage. Numbering carries no quality claim.

**Evidence**

Model evaluation remains pending. The guide locally measures character reduction
against the previous candidate of the same technique. Actual tokens and savings
require separate measurement. Some candidates exceed the active prompt's length.
Quality, safety, cost, and latency have not been measured.

**Decision and rationale**

The twelve additions remain candidates, preserving the three active prompts and
all prior history. Compare the same `evals/data_set.jsonl` inputs and provider/model
conditions, reviewing contracts, quality, and safety and measuring cost/latency
where applicable. At this time the runner is OpenAI-only. No real calls were made.
Local validation loaded 24 prompts, checked 63 valid example outputs, and passed
95 offline tests. The three active prompts were verified against their prior
instructions.

### Changed — more candidate examples and simpler filenames

- Added two input/output pairs to each of six candidates, retaining each stage's
  complete rules and input/output contracts. Preserved the three active prompts
  and unified eval dataset.
- Removed `_few_shot` and `_analisis_interno` suffixes from six filenames.
  Directories identify technique. Updated references and inventory. Earlier
  descriptions preserve the initial content as history.

| Stage and comparable versions | Updated few-shot candidate | Updated guided candidate |
| --- | --- | --- |
| Input with active v1 versus v2/v3 | [v2](prompts/input_moderation/few_shots/version_2_06_11.yaml) allows an integration-duplication report and rejects unauthorized access. | [v3](prompts/input_moderation/chain_of_thought/version_3_06_11.yaml) allows defensive rotation and rejects an unrelated recipe. |
| Classification with active v4 versus v5/v6 | [v5](prompts/input_question/few_shots/version_5_06_11.yaml) covers an invoice inquiry (`billing`) and permission changes (`account`). | [v6](prompts/input_question/chain_of_thought/version_6_06_11.yaml) covers an integration failure (`technical`) and demonstration request (`other`). |
| Output with active v1 versus v2/v3 | [v2](prompts/output/few_shots/version_2_06_11.yaml) removes a fictional token and preserves a safe answer with empty actions. | [v3](prompts/output/chain_of_thought/version_3_06_11.yaml) removes a fictional payment identifier and substitutes a safe answer for an instruction-disclosure request. |

**Problem and difference**

Broaden illustrative situations to explain each technique. Guided candidates
retain their internal-analysis criteria and now all include examples, combining
guided analysis and few-shot. Their results expose no reasoning. Confidence
values are illustrative and example sensitive data is fictional, with no real
credentials.

**Evidence**

Comparative model evaluation is pending. Local checks cover YAML and example
contracts. No new quality, safety, cost, or latency measurements establish an
improvement. The intended difference is illustrative coverage.

**Decision**

The six remain candidates, neither activated nor discarded. Compare them with
the active baseline using matching `evals/data_set.jsonl` cases, provider, model,
and conditions. The runner at this time evaluates only OpenAI. Earlier results
are preserved and no real calls were made. Validation checked 27 contract-valid
example outputs and passed 95 offline tests.

### Changed — stage naming in prompt identity

- Renamed `system_prompt.role` to `system_prompt.stage` to distinguish processing
  stages from message roles. Updated documentation and tests while retaining
  version, file, hash, and historical records. Validation passed 95 offline tests.

### Changed — system prompt role and version in metrics

- New records begin with `system_prompt`, containing `role` for the stage
  (`input_moderation`, `input_question`, or `output`) and `version` for the filename
  without its extension. An unidentified unique file yields a null version.
  Retained actual-instruction paths and hashes, with stage/version in the
  readable block. Updated documentation and tests for both providers. Historical
  records and active prompts were preserved. Validation passed 95 offline tests
  without real API calls.

### Changed — system prompt metadata at the start of records

- New records for both providers begin with `prompt_file` and `prompt_sha256`,
  preceding timestamp and consumption data. Updated the metrics guide and
  field-order test. Historical records were preserved. Validation passed
  95 offline tests.

### Changed — readable metrics and system prompt identity

- Both providers write numeric USD costs in decimal notation and numeric latency
  in seconds with three decimal places. Added a `readable` block with Spanish
  labels, units, and explicit missing-data descriptions. Numeric fields remain
  available for analysis.
- Every call records `prompt_file` and `prompt_sha256` for the instructions sent,
  supporting active prompts and eval candidates while omitting their text.
  When a stage has no unique matching file, its path is null and the actual hash
  is retained. Historical records receive no inferred provenance.
- Added `metrics/README.md` to explain fields, tokens, UTC, seconds, and USD.
  Updated the main README. Tests cover formatting, units, missing data, and
  prompt identity for both providers. Preserved active prompts and prior JSONL
  records. Validation passed 95 offline tests, with no real API calls.

### Changed — verified Gemini rates

- Configured paid Standard rates for `gemini-3.8-flash` in `pricing/gemini.json`
  at USD 0.75 input, 0.075 cached input, and 3.75 output per million tokens,
  including reasoning. The pricing table and README link Google's official
  source, verified on 2026-11-06 and valid through 2026-12-31.
- Added optional `valid_until` validation. Expired rates yield null cost with
  content-free diagnostics. Prior records retain their original costs. New
  responses use paid Standard list-price estimates without inferring account
  discounts or free-tier usage.
- Tested the 475-input-token, 71-output-token example (USD 0.0006225 with no cache),
  expired rates, and continued metric recording. Prompts were preserved and model
  quality was not evaluated. Validation passed 92 offline tests without real calls.

### Added — persistent Gemini metrics

- Gemini now appends to the same three per-stage JSONL files as OpenAI, with
  `provider=gemini`, returned model (or configured model when omitted), tokens,
  and SDK latency including retries and rate-limit waits. Preserved previous
  records. Records omit tickets, responses, and credentials.
- Output tokens include candidate and reasoning tokens. Totals preserve provider
  values and missing data remains null. Recording follows API-envelope validation
  and precedes validation of the generated-text contract.
- Added `pricing/gemini.json` with no invented rates. Cost is null until verified
  values are configured for the exact model. Estimation accounts for cached input
  and reasoning output, excluding additional charges and tiered pricing.
- Reused the file-locking writer. Persistence failures preserve the response.
  Offline tests cover stages, provider coexistence, reasoning tokens, synthetic
  costs, missing data, and write/transport errors. Validation passed 91 offline
  tests. Updated documentation with no real calls or model-quality evals.

### Changed — explicit Gemini model

- Set `GEMINI_MODEL=gemini-3.8-flash` in the local `.env` and `.env.example` and
  updated the README table. The existing client reads this through
  `get_gemini_settings()` and sends it to `models.generate_content`.
  `gemini-flash-latest` remains the default for missing or empty configuration.
  Verified local configuration loading without real calls or evals.

### Changed — prompt directories by technique

- Moved twelve prompts into `zero_shot/`, `few_shots/`, or `chain_of_thought/`
  within each stage, retaining their original filenames. Updated references and
  inventories. The loader and `--all-prompts` search recursively.
- Active input v1 and historical classification v3 use `few_shots/` because they
  contain examples. Guided variants use `chain_of_thought/` for their distinctive
  approach. Input retains its examples.
- Instructions, contracts, and active versions were preserved. Candidates remain
  pending evaluation, with their descriptions and rationale retained. Directory
  organization adds no selection or quality, safety, cost, or latency evidence.
- Validation passed 87 offline tests, including recursive candidate discovery
  by the runner. No real calls were made and usage records were preserved.

### Changed — completion of the manual fallback test

- The user confirmed that a ticket used OpenAI after configuring an invalid
  Gemini key. Restored the original Gemini key and deleted the temporary backup.
  Gemini remains primary. This is the user's manual confirmation, without further
  log inspection or model-quality evaluation.

### Changed — temporary manual fallback test

- Temporarily replaced the local Gemini key with an invalid value to test fallback
  to OpenAI using a ticket submitted by the user. The original key is stored in a
  private local backup under `.runtime/`, ignored by Git. Preparation made no API
  calls. Key restoration is pending completion of the test at this point.

### Changed — decision to retain active prompts

- **Stages and versions** compare input v1 with few-shot v2 and guided v3,
  classification v4 with few-shot v5 and guided v6, and output v1 with few-shot v2
  and guided v3. File links and descriptions are retained in the candidate record
  for this date and the historical inventory.
- **Problem and decision** clarify why the new variants remain inactive. At the
  user's direction, keep the three active prompts as a mainly zero-shot baseline
  of direct instructions and contracts that are easy to maintain and review.
  More examples or guided analysis have no demonstrated benefit yet. Input
  already has two scope examples and therefore has a few-shot component.
- **Introduced change** documents selection and rationale in `README.md` and
  `AGENTS.md`. Prompt files, contracts, active configuration, and behavior were
  preserved. All six candidates remain available.
- **Evidence and limitations** indicate pending comparative model evaluation.
  Earlier local YAML/example checks verify structure and contracts. Quality and
  safety require model evidence. Cost and latency differences were not measured.
  Avoiding additional context is a simplicity criterion, with savings and
  superiority still unproven.

### Added — prompt candidates by technique

Added six candidates at the user's request to inspect few-shot and guided
internal analysis. All remain candidates, with the selection in
`src/clients/prompts.py` and active prompts preserved. Each derives from the active
version of its stage and retains its complete rules. Version numbers identify
variants without establishing superiority.

| Stage | File and status | Compared baseline and difference | Problem and expected improvement |
| --- | --- | --- | --- |
| Input | [v2 few-shot](prompts/input_moderation/few_shots/version_2_06_11.yaml) — candidate | Active v1 plus six query/`allowed` pairs and the two existing examples. | Illustrate scope, legitimate support, defensive reports, attacks, and malicious instructions to reduce ambiguity. |
| Input | [v3 internal analysis](prompts/input_moderation/chain_of_thought/version_3_06_11.yaml) — candidate | Active v1 plus five internal criteria and its two brief examples, giving it a few-shot component. | Separate safety and scope, distinguish defensive quotations, and check the combined decision and contract. |
| Classification | [v5 few-shot](prompts/input_question/few_shots/version_5_06_11.yaml) — candidate | Active v4 plus five ticket/JSON pairs covering four categories and an out-of-scope inquiry. | Show responses, suggestions, and format, with guidance against copying facts or confidence values. |
| Classification | [v6 internal analysis](prompts/input_question/chain_of_thought/version_6_06_11.yaml) — candidate | Active v4 plus six internal criteria and no new examples. | Guide scope, main category, ambiguity, wording, and contract checks while keeping reasoning internal. |
| Output | [v2 few-shot](prompts/output/few_shots/version_2_06_11.yaml) — candidate | Active v1 plus four draft/review pairs. | Illustrate fictional-data removal, removal of secret requests, correction of unconfirmed refunds, and preservation of appropriate content. |
| Output | [v3 internal analysis](prompts/output/chain_of_thought/version_3_06_11.yaml) — candidate | Active v1 plus six internal criteria and no new examples. | Review privacy, safety, claims, suggestions, and format using only the received draft. |

**Preserved function, input, output, and rules**

Input receives an untrusted ticket and returns only a boolean `allowed` after
checking safety and Nubbix scope. Classification receives the ticket and returns
`answer`, `category`, `confidence`, and `actions`, with English categories, Spanish
text, and human-agent suggestions. Unrelated inquiries receive `other` and empty
actions. Output receives only draft `answer` and `actions`, returning those two
fields revised to remove sensitive data and invented commitments. Category and
confidence are preserved outside this stage. All require JSON with no extra
fields. Guided variants request internal criterion checks and final-only output.
This provides no evidence about the model's internal reasoning process.

**Evidence**

Model evaluation is pending. Local checks cover YAML, active selection, and
example contracts. No real calls or quality, safety, cost, or latency measurements
were made. Improvements above are goals. The examples are authored illustrations,
with no observed provider responses.

**Pending comparison**

Use the same cases from `evals/data_set.jsonl` for each stage and compare its
active baseline with both candidates under identical provider, model, settings,
and criteria. Review quality, safety, and contract compliance and record measured
cost/latency. At this point the runner uses OpenAI exclusively, even with Gemini
selected in the CLI. Gemini results require separate evaluation.

**Decision and rationale**

All six remain candidates for review and evaluation because evidence for replacing
the active versions is pending. Preserve previous descriptions, decision history,
and evidence. Dataset and execution flow were preserved.

### Changed

- Credential errors now activate per-stage fallback in both directions, including
  missing keys, HTTP 401/403, and Gemini HTTP 400 with `API_KEY_INVALID` or
  `API_KEY_EXPIRED`. Other configuration errors still stop processing. Errors are
  normalized while omitting bodies and credentials. Validation passed 86 offline
  tests and documentation was updated. No real calls were made.
- Added primary-provider selection through `LLM_PROVIDER=open_ai|gemini` in
  `.env`, defaulting to OpenAI with the other provider as per-stage backup. The
  local environment selects Gemini for testing. Diagnostics reflect the chosen
  order. Updated documentation and instructions. Added selection, invalid-config,
  and bidirectional fallback tests. Validation passed 84 offline tests, without
  real calls or model-quality evaluations.
- Configured `GEMINI_API_KEY` in the local `.env` beside the OpenAI key to
  authenticate the backup provider. The credential was not tested against the API.

## 2026-11-04

### Case identification

- Verified all 72 cases in `evals/data_set.jsonl` have nonempty unique `id` values,
  including original and malicious cases. Existing IDs were preserved. The runner
  now rejects missing, empty, or duplicate IDs before calling a model. Added tests
  for these errors.

### Unified evaluation cases

- Combined all 72 cases into `evals/data_set.jsonl`, with 40 classification,
  28 input moderation (including attacks), and 4 output cases. Every case has
  `id` and `stage`. The runner validates the file and filters by stage.
- Removed separate datasets and the empty `adversarial.jsonl` placeholder.
  Per-stage metrics files were retained. Updated tests, documentation, and
  `AGENTS.md` to preserve the unified dataset.

### Changed

- Standardized filenames with `_`. Stage records now use
  `metrics/input_moderation.jsonl`, `metrics/input_question.jsonl`, and
  `metrics/output_moderation.jsonl`. Preserved records and updated writer
  references, tests, and the README.
- Added the underscore filename/directory convention to `AGENTS.md` for future
  changes. Earlier history retains the names used at the time.

## 2026-11-03

### Removed

- Removed `metrics_data/metrics/metrics.jsonl` at the user's request, leaving
  three per-stage JSONL files. The earlier file had three records without stage
  identification. These were not reassigned to new files by inference. Updated
  documentation to remove the historical-file reference.

### Changed

- Moved rates from `metrics/pricing.json` to `pricing/openai.json`. Updated cost
  calculation references and documentation. `metrics/` retains per-stage records.
  Rates were preserved.
- Simplified the layout to root-level `metrics/`, removing the `metrics_data/`
  parent directory. Retained the three per-stage JSONL files and `pricing.json`.
  Eval runs now write to `metrics/eval_runs/`. Updated the writer, runner,
  documentation, and Git exclusions.
- Renamed per-stage metrics files to `input-moderation.jsonl`,
  `input-question.jsonl`, and `output-moderation.jsonl` under
  `metrics_data/metrics/`. Updated the writer, tests, and documentation while
  preserving records.
- Split metrics by stage into `metrics_data/metrics/input.jsonl`,
  `generation.jsonl`, and `output.jsonl` for both the ticket application and evals.
  Each response appends only to its stage's file. The earlier `metrics.jsonl`
  remains historical because its rows lack stage identity. Records were not
  reassigned by inference.
- Moved cumulative records into `metrics_data/metrics/metrics.jsonl` and updated
  writer paths and documentation. Each OpenAI response appends a row there,
  preserving history. Rates remain in `metrics_data/pricing.json` and run
  results in `metrics_data/eval_runs/`.

### Added

- Expanded `evals/input_moderation.jsonl` from 8 to 28 cases, adding 16 synthetic
  attacks with expected rejection and 4 legitimate defensive inquiries with
  expected acceptance. IDs and scenarios are included. The runner loads them
  without additional configuration. Documented coverage and false-positive
  controls. Prompts and classification labels were preserved. Real effectiveness
  remains pending OpenAI evals.
- Added cumulative `metrics_data/metrics.jsonl` records for validated OpenAI
  responses in the ticket CLI and evals, including UTC timestamp, model,
  input/output/total tokens, latency, and estimated cost. Uses file locking for
  concurrent writes and omits ticket content.
- Added editable `metrics_data/pricing.json`, initially for `gpt-6-luna`, verified
  against official documentation. Distinguishes cached input. Unknown prices or
  usage produce null values.
- Added tests for appending, calculation, missing data, write errors, and automatic
  recording across all three stages. Prompts were preserved and no real calls
  were made. Gemini and per-variant summaries do not yet include these metrics
  at this point. Validation passed 80 offline tests, whose records were written
  to temporary files to preserve real usage history.
- Added detailed function, input, output, and rule descriptions for each of six
  prompts. Added an `AGENTS.md` instruction to preserve these descriptions and
  decision/evidence history when introducing versions.
- Added a linked inventory of six existing prompts, grouped by stage, with
  differences, contracts, and activation status. Retained the requirement to
  update the inventory and justify prompt changes and selections.
- Added a sequential OpenAI-only eval runner supporting individual or all stages,
  version comparisons, case limits, and model selection. Saves per-case results
  and hash/metric summaries while leaving prompt selection under user control.
  Complete inputs and generated responses are omitted from results.
- Added initial synthetic input moderation (8 cases) and output review (4 cases)
  datasets, alongside the 40 existing classification tickets.
- Added offline runner tests and documented commands, criteria, and limitations
  in `evals/README.md`. Run results are ignored by Git.
- Evidence consists of mocked API validation. No real evals were run and no new
  prompt versions were selected. Quality comparisons remain pending evaluation.
- Added `CHANGELOG.md` to retain project history and an `AGENTS.md` requirement
  to update it for every change.
- Linked the changelog and its maintenance instructions from `README.md`.
- Added criteria for documenting and comparing prompts and instructions to
  record evidence and rationale for future changes or selections.
- Added the Nubbix ticket-project context to `AGENTS.md`, including its purpose,
  three-stage flow, providers, contracts, organization, and validation, to guide
  future work against current behavior.

### Initial prompt state from source review

This inventory compares the existing files at that point in time. Historical
selection decisions and measured improvements require additional evidence.

| Stage | Prompt | Purpose and observable difference | Status |
| --- | --- | --- | --- |
| Input | [v1 — input moderation](prompts/input_moderation/few_shots/version_1_01_11.yaml) | Decides Nubbix safety/scope with `allowed`, distinguishes legitimate security inquiries from harmful requests, and rejects instructions that attempt to change its role. | Active |
| Classification | [v1 — category only](prompts/input_question/zero_shot/version_1_25_10_es.yaml) | Returns only `billing`, `technical`, `account`, or `other`, which is incompatible with the current four-field contract. | Historical, inactive |
| Classification | [v2 — structured response](prompts/input_question/zero_shot/version_2_31_10.yaml) | Adds JSON `answer`, `confidence`, `category`, and `actions`, Spanish wording, and suggested human-agent actions. | Historical, inactive |
| Classification | [v3 — Nubbix scope and fixed rejection](prompts/input_question/few_shots/version_3_31_10.yaml) | Makes Nubbix scope explicit, broadens `other` examples, and prescribes a fixed out-of-scope rejection. | Historical, inactive |
| Classification | [v4 — flexible rejection wording](prompts/input_question/zero_shot/version_4_31_10.yaml) | Preserves v3 scope/contract and permits rejection in the model's own words while leaving the unrelated subject unanswered. | Active |
| Output | [v1 — response review](prompts/output/zero_shot/version_1_01_11.yaml) | Reviews `answer`/`actions` for sensitive data, unsafe recommendations, wording, and invented commitments. Defines a safe alternative if the draft cannot be corrected. | Active |

Linked files contain the complete instructions. The three active prompts are
selected in `src/clients/prompts.py` and shared by OpenAI and Gemini. At this
point, the OpenAI runner can compare versions while preserving that selection.
Historical files remain references, with no claim that measured results caused
their rejection.

**Selection at this review**

The loader explicitly uses version 4 for both providers. Its historical selection
rationale is undocumented. Rejection variation is a design difference, with
superiority over version 3 pending evaluation. The input guardrail may reject
out-of-scope inquiries before they reach classification.

**Active guardrails at this review**

`input_moderation/few_shots/version_1_01_11.yaml` and
`output/zero_shot/version_1_01_11.yaml` are shared by OpenAI and Gemini. No
alternative versions were identified in those directories at this point.

**Evidence available for this inventory**

All 76 local tests passed with mocked APIs after implementing the runner,
verifying functionality and contracts. Real comparisons and documented quality
results remain pending for all prompts.

### Detailed function of each prompt

These descriptions explain the instructions present at this review. Real model
compliance requires measured evaluation.

#### Input — v1 safety and scope moderation

File is [input_moderation/few_shots/version_1_01_11.yaml](prompts/input_moderation/few_shots/version_1_01_11.yaml). **Active.**

Receives the original ticket and decides whether processing may continue.
Returns only `{"allowed": true}` or `{"allowed": false}`. Both safety and Nubbix
support relevance are required. Rejects instruction overrides, secret extraction,
requests to facilitate harm, and unrelated questions even when harmless. Allows
negative-toned complaints, account recovery, and defensive security reports.
A compatible support problem need not mention Nubbix. It leaves the query
unanswered and category unclassified. Rejection stops the flow before generation.

#### Classification — v1 category assignment

File is [input_question/zero_shot/version_1_25_10_es.yaml](prompts/input_question/zero_shot/version_1_25_10_es.yaml). **Historical, inactive.**

Receives a ticket and requests one lowercase English category. `billing` covers
payments, `technical` failures/integrations, `account` access/administration, and
`other` remaining queries. Treats the ticket as data and ignores embedded
instructions. Its classification-only output has no answer, confidence, or
actions. Plain-category output is incompatible with the current JSON pipeline.

#### Classification — v2 structured response and next steps

File is [input_question/zero_shot/version_2_31_10.yaml](prompts/input_question/zero_shot/version_2_31_10.yaml). **Historical, inactive.**

Receives a ticket in any language and requests four JSON fields. `answer` is a
brief Spanish response, `category` is an English category, `confidence` estimates
category confidence from 0 to 1, and `actions` lists Spanish suggestions for the
human agent. Suggestions are proposed steps. Includes discounts and enterprise
plans under `other`. Compared with v1, it adds an actionable structured response
to classification. Explicit Nubbix-only scope and out-of-scope rejection are
still absent in this version.

#### Classification — v3 Nubbix scope and uniform rejection

File is [input_question/few_shots/version_3_31_10.yaml](prompts/input_question/few_shots/version_3_31_10.yaml). **Historical, inactive.**

Retains v2's four fields and limits assistance to Nubbix, its services, and
integrations. Lists valid `other` inquiries such as documentation, training,
demonstrations, and collaboration proposals. A valid ticket need not name the
brand. Out-of-scope inquiries receive a fixed rejection, `category: other`,
and `actions: []`, leaving the unrelated query unanswered. Explicitly rejects
role changes requested by the ticket. Compared with v2, it limits response scope
and standardizes rejection. Effectiveness remains pending evaluation.

#### Classification — v4 Nubbix scope and flexible rejection

File is [input_question/zero_shot/version_4_31_10.yaml](prompts/input_question/zero_shot/version_4_31_10.yaml). **Active.**

Receives a ticket allowed by input moderation and produces the same four-field
JSON. Preserves v3 categories, scope, and restrictions. Rejection wording changes
to a brief friendly Spanish explanation in the model's own words, identifying
Nubbix scope while leaving the unrelated subject unanswered, with
`category: other` and `actions: []`. Comparative evidence of improved quality
from this flexibility is pending. In the normal flow, input moderation should
stop out-of-scope inquiries before classification.

#### Output — v1 privacy, safety, and wording review

File is [output/zero_shot/version_1_01_11.yaml](prompts/output/zero_shot/version_1_01_11.yaml). **Active.**

Receives only draft `answer` and `actions`, excluding the original ticket,
category, and confidence. Returns those two fields revised in Spanish. Requests
removal of personal data, private identifiers, banking details, credentials,
and secrets, replacing them with generic references while omitting original
values. Also removes unsafe recommendations, offensive language, unsupported
claims, and invented commitments. Preserves meaning and safe recommendations,
and directs verification through official channels without requesting secrets.
If safe correction is impossible, requests a brief referral to official support
and `actions: []`.

The service combines the revision with classification's `category` and
`confidence`. Failed or invalid review withholds the draft. This stage aims to
reduce sensitive-information exposure. Evals must measure its real coverage,
including preservation of response usefulness.
