# Case-state analysis contract v1

This is a separate development contract. It does not extend or replace `contracts/v1`, the live case store, or the legacy `dwelly-bundle-v1` model runner. All current annotations are **unreviewed author references**, not trusted policy or gold labels.

## Records

| Record | Meaning |
| --- | --- |
| `case-step-viewer/1.0` | Original source document: complete authored snapshots for display. Never send the whole document to inference. |
| `proofkey-step-input-v1` | Evidence-only selected-step projection; `case_id`, `step_index`, `cutoff_event_id`, supplied initial `goal`, minimal `actors`, `our_actor_id`, `messages`, and `input_hash`. |
| `proofkey-step-reference-v1` | Evaluator-only author state, wait targets and next action, bound to `input_hash`. |
| `proofkey-step-candidate-v1` | Offline or model state inference, uncertainty and cited visible events; inspect `mode`, never execution authority. |
| `proofkey-step-comparison-v1` | Literal state/wait-target comparison with the author reference. `accuracy_score` is null. |
| `proofkey-analysis-run-v1` | Immutable local artifact containing input, candidate, separate reference/comparison, source binding and record checksum. |
| `proofkey-model-job-v1` | Separate opt-in PostgreSQL lifecycle with frozen input, nullable candidate/receipt, retained reservation and single-dispatch recovery. |

Index 0 is the initial state; index N is the state **after** the Nth recorded event. Array order is authoritative. `input_hash` is SHA-256 of canonical UTF-8 JSON (sorted keys, compact separators, no NaN), excluding `input_hash` itself. It is not the raw document hash. Raw document/source commit are provenance, kept outside inference. These hashes provide identity/integrity, not authentication.

Messages prefer original `body` and explicitly label translation-only fallback as `body_source: body_ru`. No timestamps, messages, participant ownership, delivery outcomes or media are fabricated. Authored state, explanations, facts, requests, decisions, outcomes, criteria, annotations and actor responsibilities are excluded from inference. Role strings are source labels, not verified authority.

## Local HTTP

| Method / path | Result |
| --- | --- |
| `GET /api/capabilities` | Offline/provider/cloud/persistence limits. |
| `GET /api/catalog` | `{cases: [...]}`; each item has ID, title, maximum step index, family, qualification and source hashes. |
| `GET /api/cases/{id}` | `{case_id, document}`: full authored source for display only. |
| `GET /api/cases/{id}/steps/{index}` | `{input, reference, source}`: separated objects. |
| `POST /api/runs` | `201` with an immutable local run. Body exactly `{case_id, step_index, expected_input_hash, mode: "offline"}`; header `X-ProofKey-Request: analysis-v1`. |
| `GET /api/runs/{run_id}` | Previously persisted run, verified against its record checksum. |

The service binds to `127.0.0.1`. Exact loopback Host and same-origin checks apply; cross-site requests and missing custom write headers are denied. There is no CORS grant, arbitrary path/URL input, browser credential field or cloud outbox consumer. A stale input hash returns `409`; invalid request `400`; unknown selection `404`; run capacity `429`; unavailable/corrupt stored data `503`. Separate model routes (`/api/model-profiles`, `/api/model-runs`, `/api/model-runs/{id}`) and their exact envelope are documented in [model analysis operations](../../docs/model-analysis-operations.md); `/api/runs` remains offline-only and unchanged.

The local artifact cap is 256 runs per directory. With no `--runs-dir`, storage is a temporary session directory. An explicit directory supports readback after a service restart; it is not a multi-user/cloud store. Creation uses private exclusive files. The service is a developer tool, not an authenticated internet-facing API.

## Dataset export

`python3 -m tools.dwelly_analysis export --output NEW_DIRECTORY` writes `inputs/`, `references/`, `manifest.jsonl` and `summary.json`. The manifest records input hash, file-byte hashes, family, source commit/hash, split, qualification and exclusions. Every row has `eligible_for_training: false` until a separate review/promotion workflow exists. Initial states are marked `context_only`; the minimal example is a `ui_fixture`. Related 002/N4 branches share one family.

This export is usable for inspecting/authoring state-analysis datasets. It is **not directly accepted** by the old next-contact model runner or the canonical case-intake importer. Those adapters require explicit output semantics and handling of dynamic actors, timestamps and channels; do not forge missing fields to pass validation.
