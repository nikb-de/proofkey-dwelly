# Local case/event intake implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking. The user's answers and autonomous-work instruction authorize this local no-provider increment.

**Goal:** Accept and preserve new local case information with honest pending-analysis status.

**Architecture:** Extend the existing service, not a second server. A case-specific repository composes the existing JobStore owner/connection and produces immutable revisions. No job worker or runtime path consumes them yet.

**Tech Stack:** Python 3.11+, standard library HTTP/SQLite, existing unittest fixtures; no new dependencies.

**Spec:** `openspec/specs/local-case-event-intake/spec.md`; design archived at `openspec/changes/archive/2026-10-10-local-case-event-intake/design.md`.

**Delivery:** Implemented and independently reviewed; local intake scope archived on 2026-10-10. See `docs/verification/local-case-event-intake-2026-10-10.md`. Automatic analysis and rescheduling remain follow-on work.

## Global constraints

- All snapshots disclose local-fixture input, unverified authorization, no runtime binding and zero operational effects.
- Existing16KiB request limit; max256cases,128events/case,16participants,16recipients,4096characters/text.
- No providers, runtime, uploads, URL fetching, policy activation or implicit job enqueue.
- Canonical finite JSON, closed shapes, durable atomic writes and immutable history.

## Review focus

1. An old idempotent retry after newer events must return its original snapshot, not current state (Task1).
2. Two simultaneous appends against one revision must not both commit (Task1).
3. Hash-valid but cross-case or malformed persisted data must fail closed (Task1).
4. Duplicate/unknown query parameters and encoded path variants must not select unintended records (Task2).
5. Accepted input must not be reported as analysed or invoke the existing worker (Task2).

## Task 1 — Contracts and durable snapshots

Own `tools/dwelly_service/cases.py` and `tools/dwelly_service/tests/test_cases.py`. `CaseStore(job_store)` uses the existing owner's `_connect()` context, creates its own tables with `CREATE TABLE IF NOT EXISTS`, and never instantiates/closes JobStore. Public methods: `create(key, body) -> (snapshot, created)`, `append(case_id, key, body) -> (snapshot, created)`, `get(case_id, revision=None) -> snapshot`.

Follow exact design contracts. `CaseError(ValueError).code` carries only `invalid_case_request`, `case_not_found`, `revision_not_found`, `idempotency_conflict`, `revision_conflict`, `event_conflict`, `case_capacity`, `case_storage_error`. Use transactions, canonical finite bounded JSON, revalidated readback, no raw error text. Test persistence/restart, stale concurrent appends, idempotency across later revisions, corrupt records, bounds and consistent participant links. No other production-file edits or provider calls.

- [ ] Write failing tests for create/restart and immutable append using the exact documented request bodies; extend with all review-focus cases.
- [ ] Run `python3.12 -B -m unittest discover -s tools/dwelly_service/tests -p test_cases.py -v`; confirm failure is a missing API or expected behavior.
- [ ] Implement the above contracts using `with owner._connect() as db: db.execute("BEGIN IMMEDIATE")` around each modifying transaction; snapshots and request identities commit together.
- [ ] Run the same suite cleanly; report red/green evidence before the controller commits only the two owned paths.

Minimal acceptance assertion after using the documented bodies:

```python
first, created = cases.create("create-1", creation)
assert created and first["revision"] == 0
next_snapshot, created = cases.append("demo-1", "append-1", append_body)
assert created and next_snapshot["revision"] == 1
assert cases.get("demo-1", 0) == first
assert cases.append("demo-1", "append-1", append_body) == (next_snapshot, False)
```

## Task 2 — HTTP integration (parallel, disjoint files)

Own `tools/dwelly_service/server.py` and new `tools/dwelly_service/tests/test_case_http.py`. Instantiate `server.cases = CaseStore(store)` before startup succeeds. Reuse existing guard and16KiB body limit. Endpoints follow design. GET accepts only one optional nonnegative canonical integer revision; reject unknown/duplicate query fields. POST both require one valid existing-format Idempotency-Key. Return201 on create/append,200 on exact retry. Map not-found404; conflicts409; capacity429; input400; storage503. Preserve current jobs/cancel/capabilities behavior; add `case_intake` capability with explicit pending-no-analysis/no-effects disclosure. Do not widen live execution, change Worker or authentication. Test real HTTP with existing fixtures; do not run the full runtime suite.

Task2 may develop against Task1's fixed interface, but final tests must consume actual CaseStore. Write RED tests before implementation. If partial parallel RED overlaps implementation, report it honestly.

- [ ] Write a real loopback HTTP test asserting POST `/v1/cases` returns201 with the documented body and bearer token; run before adding routes.
- [ ] Add routes calling `server.cases.create/append/get`, never `worker.wakeup` or `store.submit`.
- [ ] Test all guards, conflicts and malformed query parameters through `http.client.HTTPConnection`; verify creation cannot bypass bearer authentication.
- [ ] Run `python3.12 -B -m unittest discover -s tools/dwelly_service/tests -p test_case_http.py -v`, then the existing service tests; report before controller commit.

## Task 3 — Controller integration and documentation

Create `.env.example` and ignored private `.env`, neither with real secrets; document explicit shell loading (no new dotenv behavior), reserved cloud values, local endpoints and remaining boundaries in service docs. Add an offline demo using synthetic identifiers and no providers. Run all case tests + existing service tests + bridge regressions. Independent review exact diff; no pushes or deployment. Archive only if accepted.

- [ ] Verify `.env` is ignored and mode0600; `zsh -n .env .env.example` succeeds without reading secrets to output.
- [ ] Run `python3.12 -B -W error::ResourceWarning -m unittest discover -s tools/dwelly_service/tests -q` and the82-test bridge suite in the documented runtime environment.
- [ ] Review the diff independently; fix findings and rerun affected tests.
- [ ] Run `openspec validate local-case-event-intake --strict`, then archive only after implementation and review evidence are complete.

## Follow-on, not completion claims

New snapshots are pending, not automatically analysed. Rescheduling is the next sandbox action and requires typed planning, deterministic gate and original-effect readback. Training data may suggest policies but activation needs the single designated owner's approval. Real media extraction and cloud storage remain separate work.
