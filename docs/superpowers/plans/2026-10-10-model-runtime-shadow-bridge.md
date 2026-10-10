# Model Runtime Shadow Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import completed local model-service results into a durable, non-executable shadow association with an optional trusted runtime binding.

**Architecture:** An optional standard-library bridge reads existing service state without opening its mutable JobStore. A separately installed runtime resolver reads an already-open CaseStore under a consistent read transaction. A companion CLI has no configured resolver and therefore reports unmapped; only trusted in-process composition can supply one. No service callback or effect path is added.

**Tech Stack:** Python 3.12, unittest, pathlib/os/fcntl, SQLite, existing canonical JSON/snapshot validators; Pydantic only in the optional runtime resolver.

**Spec:** `openspec/changes/model-runtime-shadow-bridge/specs/model-runtime-shadow-bridge/spec.md`; design in the parent change directory.

## Global Constraints

- No live API, cloud deploy, external messaging, runtime execution, mutation of source service state, or runtime checkpoint/budget/ownership updates.
- Existing model service API, draft schemas and Docker images remain unchanged.
- Shadow records carry identifiers, hashes, status and bounded reasons, not raw prompts, responses, transcripts, media or credentials.
- All input files are finite regular files beneath configured canonical roots; reject symlinks, path traversal, duplicate JSON keys, nonfinite values and unsafe IDs.
- A supported source is a completed service-owned job with a matching terminal experiment, complete frozen proposal set and exact source-attempt linkage. An offline baseline is independently recomputed against its snapshot and records the verifier implementation hash, never a fabricated provider receipt or original-version claim.
- Target bindings are host-registered in process; caller-provided mappings or role labels do not establish authority. Without a resolver, report unmapped. Successful binding is only point-in-time association, never approval.
- Tests are written and observed failing before production behavior is implemented. Each task owns only its listed files. No worker commits; controller commits explicit paths after review.

## Review Focus

- Individually valid receipt/proposal from different attempts: reject the splice.
- Completed service job but changed frozen artifact set: reject the result.
- Concurrent or interrupted repeated imports: one complete durable record, no partial visible output.
- Host mapping stale or caller not scoped: no shadow_recorded result and no runtime mutation.
- Untrusted strings/path names and raw provider responses: bounded sanitized errors, no data leakage.

### Task 1: Source validation and immutable source snapshot

**Files:** Create `tools/dwelly_bridge/__init__.py`, `source.py`, `tests/__init__.py`, `tests/test_source.py`.

**Interfaces:** `ShadowError(ValueError)` exposes a bounded `code`. `load_source(service_root, job_id, case_id)` returns a frozen `SourceRecord` with `job_id`, `case_id`, `snapshot_hash`, `proposal_hash`, `receipt_hash`, `source_hash`, `provenance`, `source_mode`, `verifier_version`, and a `summary()` returning these values only. Define errors and source record in `source.py` so later tasks can import them. No external calls.

- [ ] Write source tests using a real temporary JobStore and real offline run_experiment output, then close the store before reading. Assert no source file hash changes and the baseline verifier version is present. For live fixtures, manually build a coherent saved request/response/proposal attempt using existing prompt/parse functions without sending it; label it a test fixture.

```python
def test_source_does_not_accept_a_different_attempt(self):
    root, job_id, case_id = self.live_fixture()
    self.replace_receipt_with_other_case(root, job_id, case_id)
    with self.assertRaises(ShadowError) as raised:
        load_source(root, job_id, case_id)
    self.assertEqual(raised.exception.code, "source_linkage_invalid")
```

- [ ] Run `/Users/nbk/.local/bin/python3.12 -B -m unittest tools.dwelly_bridge.tests.test_source -v`; record RED. Implement exact source linkage: read queue.sqlite3 through SQLite URI mode=ro/query_only, job complete, valid finite spec, start/terminal mode and case count agree; enumerate at most 50 exact snapshot/proposal IDs; verify frozen input/proposal sets and summary hash. For live output compare saved request key/provider/model/system/prompt with config and snapshot, parse receipt text, validate it and require the exact resulting envelope. For baseline compare the exact existing deterministic proposal and compute a current verifier source hash; source_mode records the experiment's mode, provenance records baseline or historical_live_api. Hash bounded canonical source evidence into source_hash. Reject unsupported source versions.
- [ ] Use no-follow regular-file reads and finite limits (4 MiB JSON, 50 cases); verify service database/root ownership and no group/world writable roots. Preserve input as immutable canonical bytes or scalar fields; do not expose mutable raw source dictionaries in SourceRecord. Test malformed JSON, unknown fields where contracts are closed, incomplete jobs, foreign case, wrong prompt/model, altered set, traversal/symlink/oversize and successful baseline/live fixture.
- [ ] Run source tests GREEN and existing model/service tests once. Write report including exact RED/GREEN commands and results. Do not commit or touch other files.

### Task 2: Optional host-owned runtime binding resolver

**Files:** Create `runtime/src/proofkey/shadow.py`, `runtime/tests/test_shadow_binding.py`. No dependency on Task 1.

**Interfaces:** `RuntimeShadowTarget` is a frozen registration containing `source_case_id`, `source_snapshot_hash`, expected `RequestBinding`, expected checkpoint hash, profile/process/policy versions, and allowed caller IDs. `RuntimeShadowResolver(store, registrations, *, authorize, clock)` is callable as `resolver(source_case_id, snapshot_hash)` and returns a JSON-compatible mapping with `status` (`bound`, `unmapped`, `rejected`), `reason`, and for bound results `target` (the complete binding, versions, checkpoint_hash, checked_at). `authorize(target, auth)` is an explicitly trusted host callback; auth is fixed at resolver construction, never supplied by the model. Include `auth` in the constructor. Bound target payload is finite and validated.

- [ ] Write a real CaseStore fixture test before implementation: create admitted synthetic state through existing harness helpers, capture the exact checkpoint, construct trusted registration, and assert returned case/object/principal/revisions/version/hash agree. Mutate generation or checkpoint through supported fixture APIs and assert rejected. Denied authorization and absent mapping must not disclose target data.

```python
def test_denied_scope_does_not_disclose_binding(self):
    resolver = self.make_resolver(authorized=False)
    result = resolver(self.source_case_id, self.snapshot_hash)
    self.assertEqual(result, {"status": "rejected", "reason": "scope_denied"})
```

- [ ] Run with `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest discover -s runtime/tests -p test_shadow_binding.py -v` and `PYTHONPATH=runtime/src`; record RED. Implement resolver as a thread-owned read transaction over the already-open CaseStore; refuse existing transactions/active execution contexts. Call existing checkpoint and original_request validation inside the same read snapshot; do not construct a new CaseStore, invoke a gateway, consume budgets or execute a workflow. Roll back read transaction on errors; restore connection state. Compare all registered fields plus source snapshot identity and check timezone-aware clock. If safe snapshot access cannot be implemented without changing journal.py, report before widening scope.
- [ ] Test copied/invalid registrations, no mutation of runtime table content, no dangling transaction, stopped case, expired checkpoint, callback exception, wrong auth, stale version and valid point-in-time association. Gate actual binding on trusted callback literal True. Hash using runtime identity.fingerprint over canonical model dumps.
- [ ] Run focused runtime tests and relevant journal/contract tests without launching the multi-hour complete runtime suite. Report the omitted full-suite limitation. Do not commit or touch other files.

### Task 3: Durable shadow record store

**Files:** Create `tools/dwelly_bridge/store.py`, `tools/dwelly_bridge/tests/test_store.py`. Other agents own package initialization and source.py; do not edit them.

**Interfaces:** `ShadowStore(root)` owns only its private SQLite database. `record(identity: dict, content: dict) -> dict` atomically stores or retrieves one record. Identity contains service namespace, job ID, source case ID and target identity (unmapped or case/object/principal/request identity); content contains validated shadow record fields. Store computes `import_id` from canonical identity, compares a canonical content fingerprint excluding only target.checked_at, and returns the original complete record on an identical repeat. Changed content under the same identity raises ValueError with code `idempotency_conflict`. Store errors are bounded ValueError codes. No imports of source.py required.

- [ ] Write failing tests for identical repeat, changed-content conflict, reopening, and concurrent independent processes recording the same identity; assert one row and identical complete return values.

```python
def test_repeat_preserves_first_observation(self):
    store = ShadowStore(self.root)
    first = store.record(self.identity, self.content)
    changed_time = copy.deepcopy(self.content)
    changed_time["target"]["checked_at"] = "2026-10-10T12:01:00+00:00"
    self.assertEqual(store.record(self.identity, changed_time), first)
```

- [ ] Run `/Users/nbk/.local/bin/python3.12 -B -m unittest tools.dwelly_bridge.tests.test_store -v`; record RED. Implement finite canonical JSON validation, maximum 64 KiB identity/content, private owned non-symlink directory, regular owned single-link database, SQLite FULL synchronous transactions, atomic unique identity insertion and conflict detection. Reject symlink database/journal/WAL/SHM, world/group accessible existing output directories instead of chmodding foreign inputs, special files, NaN and invalid JSON object shapes. Close connections promptly; expose no secret/body data in errors.
- [ ] Test bounds, aliases/hard links, unsafe directories and malformed values. Allow in-process independent instances/concurrent processes safely. Run GREEN. No source/runtime state access and no commits.

### Task 4: Idempotent bridge API, CLI and acceptance smoke

**Files:** Create `tools/dwelly_bridge/bridge.py`, `__main__.py`, `tests/test_bridge.py`, `tests/test_cli.py`, `README.md`; update `docs/model-service.md` with one optional companion link. Consume Tasks 1–3, do not change their interfaces without coordination.

**Interfaces:** `import_shadow(service_root, job_id, case_id, shadow_root, *, resolver=None)` returns a JSON-compatible record. Resolver follows Task 2's callable shape. CLI flags: `--service-state`, `--job-id`, `--case-id`, `--shadow-state`. CLI installs no runtime resolver and offers no arbitrary module import or caller-supplied binding flag.

- [ ] Write failing tests for default unmapped, bound result via a controlled host resolver, sanitized rejected errors, repeated identical import and changed content conflict. A record contains `schema_version=dwelly-shadow-record-v1`, `status`, `reason`, `source` from summary(), `target` or null, `effects=[]`, `authorization=False`, `import_id`. It does not copy the draft text. Stable logical import identity derives from service namespace, job/case and registered target identity (or unmapped); content fingerprint also includes the complete source/target except checked_at so rechecking an identical binding is idempotent. Retain first observation time; a changed checkpoint is a conflict, not silently another success.

```python
def test_default_import_is_unmapped_and_repeatable(self):
    first = import_shadow(self.source, self.job, self.case, self.output)
    second = import_shadow(self.source, self.job, self.case, self.output)
    self.assertEqual(first, second)
    self.assertEqual(first["status"], "unmapped")
    self.assertFalse(first["authorization"])
    self.assertEqual(first["effects"], [])
```

- [ ] Use ShadowStore for persistence. Output storage must not overlap source or optional runtime state. Validate exact resolver shape/finite fields and reject unknown status, invented fields or invalid target hashes/timestamps. Invalid source imports return rejected sanitized status at CLI without persisting untrusted payload. No raw exception strings in output.
- [ ] Test concurrent imports with independent processes, restart persistence, source/target changes, denied resolver, symlinked output and no source mutations. Prove no network/provider/effect path is reached with a real offline service job and forbidden-call hooks; pair hooks with source/runtime before/after hashes. Run CLI in a subprocess against real artifacts. Keep errors machine-readable and nonzero for rejected; unmapped is a successful shadow observation.
- [ ] Document exact local commands, approved scope, how trusted in-process host composition differs from CLI unmapped mode, and why this is not operational planning. Run all tools test modules, new runtime resolver tests, and an offline no-network smoke. Add verification receipt, independently review, then archive this scoped change only after fixes. Do not push or deploy.
