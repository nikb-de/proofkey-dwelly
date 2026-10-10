# Case-state analysis integration

## Intent and alternatives
Success means a teammate can open a separate local interface, choose either supplied branch and any step, inspect the exact evidence-only input, run a bounded baseline, inspect its immutable result next to the separately labelled author reference, and export development records. It does not mean a model reconstructed the author's state or a business action occurred.

Alternatives: (1) force snapshots into frozen case v1 (rejected: missing identities, dynamic participant registry and timestamp differences); (2) show the widget alone (insufficient: no input/reference boundary or analysis); (3) add a small separate analysis contract and service (selected). This leaves the existing private Case API and future BFF/worker integration independent.

## Data boundary
Vendor the original 14 widget files; JSON bytes stay unchanged. A manifest pins source repository/commit, exact source hashes, family IDs, split `development`, and qualification `author_labels_unvalidated`. Case002 and N4 belong to the same family. Minimal is a UI/control fixture, not an independent logistics outcome. Sixteen snapshots are not sixteen independent cases.

`project(document, step_index, case_id)` produces `proofkey-step-input-v1`: case ID, index, cutoff event ID (null at start), initial supplied goal, current minimal actors (ID/name/role), our actor ID, visible messages and canonical SHA-256 `input_hash`. Preserve array order and original `body`; report a translation-only fallback explicitly. Exclude state/decision/results, facts, requests, explanations, annotations, actor responsibilities, criteria and future events. The hash excludes its own field and changes only with projected evidence. Document hash belongs in run provenance, not inference input.

`reference` extracts evaluator-only author state and expected next action bound to the exact input hash. It is never an inference argument. All generated rows stay development/unreviewed. Preserve source bytes and include adapter version, raw hash, family, selected index and exclusions in exports. This is a new contract, not a silent extension of `proofkey-decision-input-v1`.

## Inference and comparison
`analyze(input)` is a pure, limited `deterministic_fixture_baseline` independent from references. It can recognize actual outgoing requests (wait), supplied missing detail (propose forwarding), ambiguous channel outcome (request readback, never resend), and explicit service confirmation (infer goal completion, not verified execution). Unknown/empty/unsupported evidence returns unknown/operator review. No case-ID-specific rules or reference-text matching. Candidates retain evidence IDs, uncertainty, `operational_effects: 0` and `live_calls: 0`.

Comparison reports literal state/wait-target agreement only, never an accuracy score or semantic certification. Reference and candidate are displayed separately. A candidate never changes the raw timeline or inserts sent messages.

## Service and UI contract
New `tools.dwelly_analysis` serves same-origin UI on `127.0.0.1`, default port 8093. Fixed catalog only; request paths cannot select arbitrary files. GET `/api/capabilities`, `/api/catalog`, `/api/cases/{id}`, `/api/cases/{id}/steps/{n}`, `/api/runs/{run_id}`. POST `/api/runs` requires exactly `{case_id, step_index, expected_input_hash, mode: "offline"}` plus `X-ProofKey-Request: analysis-v1`. Invalid/missing hashes fail; live mode fails. No permissive CORS. Validate Host against the actual loopback port; deny foreign Origin and `Sec-Fetch-Site: cross-site`. Managed-cloud markers fail startup. Never expose keys or backend tokens.

Run artifacts are private local JSON files, exclusively created with source/input/candidate/reference hashes and implementation version. A server-local lock and a 256-run cap bound creation. `--runs-dir` enables explicit persistence; otherwise use a temporary directory and say so. Reloaded artifacts must be validated and cannot escape that directory. POST response is the run record, including run_id, input, candidate, evaluation and reference, with provenance; no raw exception text. GET step returns input, reference and source binding. GET case returns the original document for the source-only timeline.

UI at `/` is `case-state-widget/analysis.html` with English shell and original source text. It contains catalog selection, source timeline, separate evidence-only input, baseline result, author reference and JSON download. Switching case/step invalidates older pending responses. All dynamic text is escaped/textContent. Source-viewer remains available at `/source-viewer`; original uploads are browser-local and not added to the trusted analysis catalog.

Harden the shared viewer before reuse: uniform UTF-8 size (5 MiB), depth (64) and node (100000) limits; typed actors/annotations; preserve last valid view on rejected input; reject inconsistent completed state and invalid message direction. UI labels make authored source state, inferred state, analysis completion and business execution distinct.

## Verification
TDD: malformed/deep inputs, future-label sentinels, input-hash stability when references change, all sixteen selections, source-file hash mismatch, deterministic repeatability, N4 no-resend, unknown abstention, same-origin/Host/CSRF checks, immutable/reloadable run records, stale browser responses, XSS and mobile/desktop rendering. Run old widget tests, new Node/Python tests and existing contract/service regression. No cloud or model network access is required.
