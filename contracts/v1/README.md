# Team contract v1

**Entry point for UI, backend, E2E and training/evals.** Source records use the existing `dwelly-local-case-v1` format. This contract pack is versioned independently; no endpoint is added merely by describing it here.

Read [architecture and ownership](../../docs/architecture/team-contract-v1.md), [API definitions](openapi.json), [state transitions](state-machines.json) and [schemas](schemas/). Run `python -m unittest discover -s contracts/v1 -p 'test_*.py' -v` using an environment with the test dependencies documented alongside the tests.

## Fixed rules

1. A case is created at **revision 0**, with no events. An append creates N+1, never edits N. IDs match `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`. Do not convert `001` to an integer or rename public benchmark IDs to fit local cases.
2. A decision binds `(case_id, revision, snapshot_hash)`. A case ID alone is insufficient. Hashes are SHA-256 of canonical UTF-8 JSON (sorted keys, no whitespace, no NaN; exclude `snapshot_hash` itself).
3. A stored file, readable content, model proposal, authorised operation and verified outcome are **five different facts**.
4. Raw participant messages, photos, transcripts and LLM labels never grant authority. Policy derived from examples remains a proposal until explicitly approved by the responsible human.
5. Exact append retries use the same body and idempotency key and receive the original snapshot, even if the head has advanced. A changed body requires a new key; concurrent different appends require revision conflict handling.
6. Training labels, reference decisions, future events and transition expectations stay outside model-visible decision input. Human review status is explicit. Do not turn assistant-authored labels into gold data.

## Availability

| Interface | Now | Consumer contract |
|---|---|---|
| Create case, append event, read exact/latest revision | Local authenticated service | `openapi.json` ordinary `paths` |
| Photo/audio metadata in events | Local service, declared hash only | `local-case.schema.json` |
| File selection, preview, bytes after reload | Separate browser-local workbench | `design/right-ontime/prototype/intake.html` |
| Shared file upload/object storage, case list API, browser BFF | **Target, not installed** | `x-target-interfaces` |
| New case revision automatically analysed | **Target, not installed** | `analysis.schema.json` and outbox design |
| Existing benchmark model jobs | Local service; fixed startup bundle | `docs/model-service.md`; not the new-case pipeline |
| Trusted runtime association | Optional read-only shadow bridge | `tools/dwelly_bridge/README.md`; zero effects |
| Real reschedule/refund/carrier integration | **Not connected** | Synthetic runtime is not a real integration |

## Change policy

Existing closed service schemas must not acquire fields from this pack. Add UI-only data in an outer local envelope; export the exact inner request. Additive contract corrections require tests and a changelog entry. Breaking field/state/meaning changes require v2 and a converter with explicit errors. Leave original source and previous snapshots immutable.

## Parallel work now

- **UI:** develop against local workbench and target BFF, never embed service tokens. Treat unavailable integration as unavailable, not a simulated success.
- **Backend:** implement target asset/BFF and revision-analysis adapters behind these interfaces, with atomic state changes and readback.
- **E2E:** run fixed fixtures in isolated storage; cover reload, duplicate delivery, stale revision, crash, late result and uncertain effect.
- **Training/evals:** prepare episode, decision-input, decision-label, transition and decision-run separately; use exact hashes and label provenance. Judge scores do not replace human validation or runtime permission.
