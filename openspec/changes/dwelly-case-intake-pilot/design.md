## Context and approved intent

The user approved the in-chat pipeline and asked to implement it without further continuation questions. This architectural slice is limited to offline intake and assessment, not a new live agent. Existing `CanonicalRequest` and registered replay profiles remain untouched because arbitrary natural-language cases cannot safely be coerced into executable requests.

## Decisions

1. Use standalone standard-library tooling rather than changing the runtime's frozen package inventory or importing data into executable fixtures.
2. Parse `history.md` as the authoritative source of available messages. Ignore all index prose for agent input: even titles, context and summaries can contain hindsight. A snapshot includes only Context/Escalation events before the unique Agent action. That action and later events belong exclusively to evaluator reference files.
3. Preserve exact bytes of index/history/attachments under `raw/`. Agent files contain only visible event messages and attachments first linked in visible events. Future file names and whole-history hashes stay in the evaluator manifest, not in agent payloads. Relative paths are validated; remote links are never fetched. Reject symlinks, traversal, malformed stages, event gaps and unordered timestamps.
4. A deterministic baseline emits a proposed next communication, source event IDs and zero-effect metadata. It never imports evaluator references or accesses source paths. Its policy uses visible messages, not case numbers. Unknown scenarios request operator review. This is an inspectable starting point, not an LLM or general resolution engine.
5. Reference comparison checks exact normalized recipient/channel only. A mismatch is not a wrong answer and agreement is not semantic correctness. All semantic quality labels remain `unassessed`. References are examples, not unique ground truth.
6. All 50 public cases are development material already inspected by the team/assistant. They are not a held-out benchmark. Determinism, routing proxy and guardrail controls are measured; provider quality and real-world applicability are not certified.

## CLI and artifacts

`python3 -m tools.dwelly_cases import --source REPO --output NEW_DIR --expected-cases 50`

Creates `raw/`, `agent/<case>.json`, `evaluation/<case>.json`, `manifest.json` and `ledger.jsonl`. The output directory must not exist; failed imports leave no published bundle. A case ID is `delivery-logistics-NNN`; inputs preserve event source spans and channel text.

`python3 -m tools.dwelly_cases run --bundle DIR --output NEW_DIR`

Loads only explicit agent files, produces per-case proposals and a summary. Comparison happens in a separate evaluation function, after proposals have been frozen. Outputs distinguish unsupported decisions and malformed/missing data from routing mismatches. Repeat runs must produce identical proposal bytes. No command modifies the original dataset or existing output.

## Verification

- Unit and integration tests cover future-answer mutation invariance, attachment temporal filtering, exact raw bytes, invalid metadata, source escapes, fail-closed output, no operational effects, unknown-case abstention and proxy limits.
- Known-good, wrong-route, unsupported-completion and empty-output controls establish sensitivity of each claimed check; repeated/reordered evaluation must agree.
- Full 50-case import validates the observed 228 events and six future-only attachments without hardcoding these totals into import logic.
- Run the standalone suite and existing runtime regression; preserve all failures if any. Archive only after commands and scope statements agree.

## Non-goals

No live connectors, external LLM invocation, payment decisions, automatic fixture activation, semantic accuracy certification, untouched holdout claim, other-track schema support, or hackathon submission.
