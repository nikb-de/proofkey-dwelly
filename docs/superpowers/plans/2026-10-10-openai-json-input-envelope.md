# OpenAI JSON input envelope fix

Scope: `tools/dwelly_model/providers.py` and provider tests; OpenSpec change `openai-json-input-envelope`.

- [x] RED: Fake HTTP boundary rejects input lacking JSON despite JSON instructions; preserve a neutral evidence prompt in the assertion.
- [x] GREEN: Prefix OpenAI input with `Return a JSON object.\n`; keep all other fields and providers unchanged.
- [x] VERIFY: Provider tests and offline model suite; no live calls, retries or ledger changes.
- [x] ARCHIVE: Record exact red/green results and archive the spec delta.

Diagnosis: the parent's real Responses diagnostic returned HTTP 400 when JSON appeared only in `instructions`; a diagnostic with JSON in `input` succeeded. The shared adapter used the supplied prompt directly; platform prompts differ from the evaluation runner's format-bearing prompts. The fixed envelope belongs at the shared adapter boundary.

Observed red: `test_openai_json_mode_requires_json_in_input_not_only_instructions` failed with `ProviderError: http_400` before production change. Green provider suite: 19 passed, 75 subtests. Full model suite: 75 passed, 173 subtests. Final model + analysis-model/service + platform-model contracts: 122 passed, 222 subtests in 3.61 seconds with real local PostgreSQL and injected provider boundaries.

Tests adapted narrowly: provider exact envelope; parallel test-only request decoders; runner persisted logical prompt versus fixed wire prefix; analysis model exact wire assertion. Persisted logical evidence is unchanged and remains the exact suffix of OpenAI input. No semantic ledger change, paid call, retry, credential change or operational action was performed. Root owns server restart and real OpenAI canary.
