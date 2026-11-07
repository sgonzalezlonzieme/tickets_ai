# Tests

Run from the project root using the project's Python environment:

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s tests/unit -v
.venv/bin/python -B -m unittest discover -s tests/integration -v
```

Run the same test runner in Windows PowerShell after activating the environment.

```powershell
python -B -m unittest discover -s tests -v
```

File-lock tests cover OS selection, contention, release after errors, empty files,
and preservation of UTF-8 records. The suite also starts four local processes
writing to the same JSONL file. The Windows branch is mocked on macOS. Running
the suite on an actual Windows machine is still pending.

- `unit/`: entity contracts, prompt/configuration loading, dataset integrity,
  validation error privacy, and isolated service moderation branches.
- `integration/`: components working together, including the full CLI → service
  → client pipeline, actual YAML prompt loading, strict schemas, client cleanup,
  three-call ordering, revised output, rejection, and failures at each stage.
- `support.py`: shared synthetic response fixtures. These are not real customer data.

All tests run offline. The integration suite mocks the provider SDK boundaries and
configuration values, preserving the application's internal wiring. It does not
exercise the remote services or model quality. Dedicated transport tests run
the real SDK retry code against local mock HTTP transports, with a fake clock
for rate-limit waits.
In particular, a simulated redacted response verifies that the app uses the
reviewed output; it does not prove the model reliably detects sensitive data.
Live model accuracy belongs in separate evaluations and is not claimed here.

When changing a prompt contract, entity, client, service, or CLI behavior, update
the affected unit tests and pipeline integration cases and run the suite before
considering the change complete. Keep failures fail-closed: never show an
unreviewed draft when any stage fails.

Provider coverage also verifies OpenAI-first ordering, same-stage Gemini fallback,
no fallback on rejection or nontransient errors, both providers failing, resource
cleanup, Gemini schema configuration, blocked/partial responses, and lazy credentials.

Parsing retry tests verify three attempts per provider, early recovery, independent
budgets for each stage, OpenAI-to-Gemini fallback after exhaustion, and no parsing
retries for rejection, refusal, incomplete output, or configuration failures.

Rate limiter tests cover sliding-window boundaries, separate provider quotas,
persistent reservations, configuration, and wait-and-continue behavior. Client
tests distinguish normal primary requests from fallback handler execution.
