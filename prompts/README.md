# Prompt review and variants

The active manual-trial selection is brief few-shot input v4, brief few-shot
classification v7, and zero-shot output v1. Both providers and the runner defaults
share the selection file. The loader validates unique YAML filenames within each
stage. Restart the CLI after editing the cached selection. Previous input v1
and classification v4 are historical baselines. Other variants remain candidates.
The file history preserves their descriptions and decisions.
[Active prompt selection](active_prompts.yaml).

The review covers every prompt file. Historical classifier v1 and v2 are brief,
but v1 requests a plain category and v2 omits explicit Nubbix scope restrictions.
Historical v3 prescribes a fixed rejection message. Previous v4 and active v7
allow flexible wording. The six earlier candidates repeat the full baseline
rules and add criteria and examples, serving as longer comparison references.

New variants condense repeated rules into a stage-specific core and use compact
JSON examples. Brief variants have two examples. Extended variants have four
examples and extra boundary-case guidance. `chain_of_thought` variants combine
internal review instructions with few-shot examples. They request only the final
JSON output. Variants differ in both length and examples, so attributing a result
to one factor requires an additional controlled comparison.

## Contracts and rules

- Input moderation receives an untrusted ticket and returns only an `allowed`
  boolean. It checks safety and Nubbix relevance together, covering defensive
  support, commercial and employment inquiries, and the distinction between
  reporting harm and requesting help to cause it.
- Classification receives a ticket and returns `answer`, `confidence`, `category`,
  and `actions`. Text is in Spanish, categories in English, and confidence ranges
  from 0 to 1. Out-of-scope questions receive `other`, a brief scope explanation,
  and empty actions. Actions are suggestions for a human agent. Facts and
  commitments must be supported by the available information.
- Output review receives the draft's `answer` and `actions` and returns those two
  revised fields. It removes personal data, private identifiers, secrets,
  offensive language, unsafe recommendations, and unsupported claims. It directs
  users to secure official channels, preserves appropriate content, and defines
  a safe alternative response with empty actions when necessary.

## Separate variants

Each candidate is compared with its stage's active prompt and the previous
candidate listed below. Character counts measure the loaded `instructions`
string. Token counts require model-specific measurement. Examples use fictional,
harmless inputs such as stories, cooking, and general knowledge to illustrate
scope rejection. These authored examples provide no measured evidence of the
model's safety performance.

| Stage / technique | Candidate file | Variant | Examples | Characters | Previous candidate | Character reduction |
| --- | --- | --- | --- | --- | --- | --- |
| input_moderation / few_shots | [version_4_06_11](input_moderation/few_shots/version_4_06_11.yaml) | brief | 2 | 1354 | [version_2_06_11](input_moderation/few_shots/version_2_06_11.yaml) | 55.0% |
| input_moderation / few_shots | [version_5_06_11](input_moderation/few_shots/version_5_06_11.yaml) | extended | 4 | 1977 | [version_2_06_11](input_moderation/few_shots/version_2_06_11.yaml) | 34.4% |
| input_moderation / chain_of_thought | [version_6_06_11](input_moderation/chain_of_thought/version_6_06_11.yaml) | brief | 2 | 1538 | [version_3_06_11](input_moderation/chain_of_thought/version_3_06_11.yaml) | 53.5% |
| input_moderation / chain_of_thought | [version_7_06_11](input_moderation/chain_of_thought/version_7_06_11.yaml) | extended | 4 | 2251 | [version_3_06_11](input_moderation/chain_of_thought/version_3_06_11.yaml) | 32.0% |
| input_question / few_shots | [version_7_06_11](input_question/few_shots/version_7_06_11.yaml) | brief | 2 | 1711 | [version_5_06_11](input_question/few_shots/version_5_06_11.yaml) | 65.2% |
| input_question / few_shots | [version_8_06_11](input_question/few_shots/version_8_06_11.yaml) | extended | 4 | 2705 | [version_5_06_11](input_question/few_shots/version_5_06_11.yaml) | 45.0% |
| input_question / chain_of_thought | [version_9_06_11](input_question/chain_of_thought/version_9_06_11.yaml) | brief | 2 | 1926 | [version_6_06_11](input_question/chain_of_thought/version_6_06_11.yaml) | 57.7% |
| input_question / chain_of_thought | [version_10_06_11](input_question/chain_of_thought/version_10_06_11.yaml) | extended | 4 | 2971 | [version_6_06_11](input_question/chain_of_thought/version_6_06_11.yaml) | 34.8% |
| output / few_shots | [version_4_06_11](output/few_shots/version_4_06_11.yaml) | brief | 2 | 1718 | [version_2_06_11](output/few_shots/version_2_06_11.yaml) | 51.8% |
| output / few_shots | [version_5_06_11](output/few_shots/version_5_06_11.yaml) | extended | 4 | 2631 | [version_2_06_11](output/few_shots/version_2_06_11.yaml) | 26.3% |
| output / chain_of_thought | [version_6_06_11](output/chain_of_thought/version_6_06_11.yaml) | brief | 2 | 1831 | [version_3_06_11](output/chain_of_thought/version_3_06_11.yaml) | 48.2% |
| output / chain_of_thought | [version_7_06_11](output/chain_of_thought/version_7_06_11.yaml) | extended | 4 | 3023 | [version_3_06_11](output/chain_of_thought/version_3_06_11.yaml) | 14.5% |

## Reviewed inventory

| File | Status | Characters | Space-separated words |
| --- | --- | --- | --- |
| [input_moderation/chain_of_thought/version_3_06_11.yaml](input_moderation/chain_of_thought/version_3_06_11.yaml) | Previous candidate | 3310 | 494 |
| [input_moderation/chain_of_thought/version_6_06_11.yaml](input_moderation/chain_of_thought/version_6_06_11.yaml) | Compact candidate | 1538 | 203 |
| [input_moderation/chain_of_thought/version_7_06_11.yaml](input_moderation/chain_of_thought/version_7_06_11.yaml) | Compact candidate | 2251 | 304 |
| [input_moderation/few_shots/version_1_01_11.yaml](input_moderation/few_shots/version_1_01_11.yaml) | Historical, previous baseline | 2178 | 319 |
| [input_moderation/few_shots/version_2_06_11.yaml](input_moderation/few_shots/version_2_06_11.yaml) | Previous candidate | 3012 | 431 |
| [input_moderation/few_shots/version_4_06_11.yaml](input_moderation/few_shots/version_4_06_11.yaml) | Active for manual trial | 1354 | 180 |
| [input_moderation/few_shots/version_5_06_11.yaml](input_moderation/few_shots/version_5_06_11.yaml) | Compact candidate | 1977 | 270 |
| [input_question/chain_of_thought/version_10_06_11.yaml](input_question/chain_of_thought/version_10_06_11.yaml) | Compact candidate | 2971 | 388 |
| [input_question/chain_of_thought/version_6_06_11.yaml](input_question/chain_of_thought/version_6_06_11.yaml) | Previous candidate | 4554 | 692 |
| [input_question/chain_of_thought/version_9_06_11.yaml](input_question/chain_of_thought/version_9_06_11.yaml) | Compact candidate | 1926 | 254 |
| [input_question/few_shots/version_3_31_10.yaml](input_question/few_shots/version_3_31_10.yaml) | Historical | 2534 | 399 |
| [input_question/few_shots/version_5_06_11.yaml](input_question/few_shots/version_5_06_11.yaml) | Previous candidate | 4921 | 718 |
| [input_question/few_shots/version_7_06_11.yaml](input_question/few_shots/version_7_06_11.yaml) | Active for manual trial | 1711 | 227 |
| [input_question/few_shots/version_8_06_11.yaml](input_question/few_shots/version_8_06_11.yaml) | Compact candidate | 2705 | 354 |
| [input_question/zero_shot/version_1_25_10_es.yaml](input_question/zero_shot/version_1_25_10_es.yaml) | Historical | 632 | 93 |
| [input_question/zero_shot/version_2_31_10.yaml](input_question/zero_shot/version_2_31_10.yaml) | Historical | 1294 | 201 |
| [input_question/zero_shot/version_4_31_10.yaml](input_question/zero_shot/version_4_31_10.yaml) | Historical, previous baseline | 2653 | 420 |
| [output/chain_of_thought/version_3_06_11.yaml](output/chain_of_thought/version_3_06_11.yaml) | Previous candidate | 3536 | 482 |
| [output/chain_of_thought/version_6_06_11.yaml](output/chain_of_thought/version_6_06_11.yaml) | Compact candidate | 1831 | 230 |
| [output/chain_of_thought/version_7_06_11.yaml](output/chain_of_thought/version_7_06_11.yaml) | Compact candidate | 3023 | 378 |
| [output/few_shots/version_2_06_11.yaml](output/few_shots/version_2_06_11.yaml) | Previous candidate | 3568 | 467 |
| [output/few_shots/version_4_06_11.yaml](output/few_shots/version_4_06_11.yaml) | Compact candidate | 1718 | 222 |
| [output/few_shots/version_5_06_11.yaml](output/few_shots/version_5_06_11.yaml) | Compact candidate | 2631 | 331 |
| [output/zero_shot/version_1_01_11.yaml](output/zero_shot/version_1_01_11.yaml) | Active | 1805 | 261 |

## Evidence and decision

Comparative model evaluation is pending. Local checks validate YAML, illustrative
outputs, and runner loading. Real-ticket behavior requires model evaluations.
All new candidates have fewer characters than the previous candidate of the
same technique. Some are longer than the active zero-shot prompt. Token savings,
cost, latency, quality, and safety differences have yet to be measured.

The user selected input v4 and classification v7 for a manual trial while keeping
output v1. Comparison with the previous baselines is pending. Use the same cases
from `evals/data_set.jsonl`, settings, provider/model, and scoring criteria.
The runner selects OpenAI or Gemini through `evals/config.yaml`, independently
of the CLI provider, and evaluates directly with the selected provider.

Compare the previous input baseline, the active brief few-shot variant, and the
extended candidate with this command.

```bash
.venv/bin/python evals/runner.py --stage input_moderation \
  --prompt version_1_01_11.yaml --prompt version_4_06_11.yaml \
  --prompt version_5_06_11.yaml
```

On Windows, activate the environment and use `python` in place of
`.venv/bin/python`. This command makes real API calls and consumes tokens.
It was not executed during this review. Assess quality and safety alongside
contract compliance, and record cost and latency when measured, including
regressions.
