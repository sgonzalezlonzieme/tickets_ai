# Reading usage metrics

Each JSON line represents an API response. The filename identifies its stage.
`input_moderation.jsonl` records input moderation, `input_question.jsonl` records
classification, and `output_moderation.jsonl` records output review. Both providers
append to these files. New records begin with `system_prompt`, which identifies
the stage and version.

```json
{"system_prompt": {"stage": "input_moderation", "version": "version_1_01_11"}}
```

`stage` is `input_moderation`, `input_question`, or `output`. `version` is the
complete filename without `.yaml`. It is null when a unique matching file cannot
be identified. The following fields retain `prompt_file` and `prompt_sha256`.

| Field | Meaning | Example |
| --- | --- | --- |
| `system_prompt` | Prompt stage and version at the start of the record. | `{"stage": "input_moderation", "version": "version_1_01_11"}` |
| `timestamp` | UTC recording time in ISO 8601. `+00:00` indicates UTC. | `2026-11-06T12:10:57.211466+00:00` corresponds to 09:10:57 in Argentina on that date. |
| `provider` | Provider that handled the call. | `openai` or `gemini` |
| `model` | Model reported by the API. Gemini falls back to the configured name when omitted. | `gemini-3.8-flash` |
| `prompt_file` | File whose instructions exactly match those sent. | `prompts/input_question/zero_shot/version_4_31_10.yaml` |
| `prompt_sha256` | Hash of the instructions actually sent, used to detect content changes. It excludes the ticket and YAML wrapper. | A 64-character hexadecimal string. |
| `prompt_tokens` | Input text/context units processed by the model. A token can represent part of a word, a word, or punctuation. | `507` tokens |
| `completion_tokens` | Generated tokens, including reasoning where applicable. | `39` tokens |
| `total_tokens` | Total reported by the API, retained even when individual counts are missing. | `546` tokens |
| `latency_s` | SDK call duration in seconds with three decimal places, including rate-limit waits and transport retries. | `3.578` seconds equals `3578` milliseconds. |
| `cost_usd` | Estimated cost in US dollars, written in decimal notation. The estimate excludes some provider charges. | `0.0000702` USD is equivalent to `7.02e-05`. |
| `readable` | Human-readable values with Spanish keys and explicit units, as emitted by the application. | `duracion: "3.578 segundos"`, `costo_estimado: "USD 0.0000702"` |

The original fields remain JSON numbers for summing costs and calculating
averages. JSON uses a decimal point. Values inside `readable` are text.
`null` and the application's Spanish text `No disponible` indicate unavailable
data or pricing. A numeric zero is required to represent a zero estimate.

Prompt identity is calculated from the actual instructions of each call,
including eval variants and fallback calls. If they do not match a unique file
in that stage, `prompt_file` is null and the hash is retained. Records omit prompt
text, tickets, responses, and credentials. Recovering a modified prompt requires
preserving the file and its history alongside the hash.

New fields and decimal formatting apply to new records. Historical records retain
their original values and prompt metadata. A blocked response or text that later
fails validation can still consume tokens. The main README describes recording
behavior and pricing in more detail.

The writer coordinates processes through an exclusive lock selected by
`os.name`. It uses `fcntl.flock` on macOS/Linux and `msvcrt.locking` on Windows.
Windows writers lock the first byte of the file, including when it is empty,
wait for competing writers, and release the lock after flushing. Append mode
preserves earlier records. Exceptions release the lock, and persistence errors
are logged to stderr.
