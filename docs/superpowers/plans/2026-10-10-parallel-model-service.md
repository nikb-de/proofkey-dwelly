# Parallel Model Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Execute independent file owners in parallel, as expressly requested by the user; only root commits after review.

**Goal:** Deliver an authenticated persistent local model-job service with bounded parallel inference and honest Google Cloud preparation.

**Architecture:** One coordinator owns ordered reservations and artifacts; provider transports overlap. One durable SQLite job queue controls the shared local budget. Cloud preparation stays offline until external durable admission exists.

**Tech Stack:** Python 3.12 standard library, SQLite, HTTP, Docker, Cloud Run Job YAML.

**Spec:** `openspec/changes/archive/2026-10-10-parallel-model-service/design.md` and `openspec/specs/parallel-model-service/spec.md`.

## Global Constraints

- Zero business effects; no provider calls, cloud deployments or paid resources during development tests.
- Keep existing direct callers serial by default; optional bounds global 1..16, per provider 1..8.
- Preserve pre-dispatch durable reservations, retained spend and proposal/reference barrier.
- One operator, one active service job, persistent POSIX storage; no cloud durability claims.
- Keep edits in assigned files; no worker commits, no worker subagents. Root commits the integrated change.

## Review Focus

- Out-of-order replies must not corrupt case identity or exceed concurrency bounds.
- Near-cap budgets across jobs must not reset or race.
- Cancellation and restart must not duplicate paid calls or erase partial results.
- HTTP paths, origins, authentication and idempotency must fail closed.
- Cloud templates must not accidentally enable live calls or ephemeral queue deployment.

### Task 1: Parallel model coordinator

**Files:** Modify `tools/dwelly_model/runner.py`, `tools/dwelly_model/__main__.py`; create focused helper/test modules under `tools/dwelly_model/` as needed. Do not edit service or cloud files.

**Interfaces:** Extend `run_experiment` with keyword parameters `max_parallel_requests=1`, `per_provider_limit=1`, `proposals_only=False`, `cancel_requested=None`, `shared_budget_path=None`. `cancel_requested` is a zero-argument Boolean callable. Shared-ledger keys include a stable unique experiment namespace. Existing output-local keys stay unchanged. Terminal state uses `completed` or `cancelled`. Keep original callers and config schemas compatible.

- [x] Write failing tests: controlled transports overlap within limit, finish out of order, and observe `proposals-frozen.json` before every judge; proposal-only succeeds even with missing evaluation directory; cancelled run drains one blocked call and sends no next call; two distinct outputs share budget and cannot reset cap; invalid bool/zero/large concurrency fails before output. Test behavioral invariants, not literal implementation source.
- [x] Run `python3 -B -m unittest tools.dwelly_model.tests.test_parallel -v` and record missing-feature failures.
- [x] Implement one-writer coordinator and bounded provider worker pool; canonical-order admission independent of response ordering; never reserve speculative work beyond in-flight capacity. Cooperative cancel stops admission; all results settle before summary. Shared ledger uses namespace on reservation/outcome only. Add CLI `--max-parallel-requests`, `--per-provider-limit`, `--proposals-only`; validate bounds before writing.

```python
run_experiment(bundle, output, config, live=False, limit=1,
               max_parallel_requests=4, per_provider_limit=2,
               proposals_only=True, cancel_requested=lambda: False,
               shared_budget_path=state_dir / 'budget.jsonl')
```

- [x] Run focused new tests and all model tests. Report red/green evidence and files; do not commit.

### Task 2: Persistent local API

**Files:** Create `tools/dwelly_service/{__init__,__main__,store,server,worker}.py` and tests. No edits to runner/cloud files.

**Interfaces:** Call Task 1 signature above. `python -m tools.dwelly_service --bundle PATH --config PATH --state-dir PATH` starts local API with token from `PROOFKEY_SERVICE_TOKEN`, loopback default, port 8080. `--allow-live` explicitly enables live requests; without it reject live. Service defaults 4 global/2 per-provider calls and proposal-only. Refuse `K_SERVICE` or `CLOUD_RUN_JOB` environments.

- [x] Write failing API/store tests: real SQLite commit/reopen; duplicate key and differing-body conflict; unauthorized/Origin/oversized/malformed requests; queued cancellation; recovery of running job without dispatch; lock exclusion; actual HTTP post/poll to offline proposal result. No live providers.
- [x] Run new service suite for expected red evidence.
- [x] Implement endpoints `GET /healthz`, authenticated `GET /v1/capabilities`, `POST /v1/jobs`, `GET /v1/jobs/{id}`, `GET /v1/jobs/{id}/summary`, `GET /v1/jobs/{id}/proposals`, `POST /v1/jobs/{id}/cancel`. Proposal readback returns bounded validated unsent drafts in stable case order, never raw provider replies or incomplete files. Require `Idempotency-Key` on submissions. Exact allowed JSON fields are `mode` (`dry_run` default or `live`), `limit` (1..50 default 1), `evaluate` (Boolean default false), `max_parallel_requests` (1..16 default 4), `per_provider_limit` (1..8 default 2). All inputs and provider config fixed by operator CLI, never client paths/credentials. Bound body 16 KiB; content-free errors, no request logs or CORS. Limit pending jobs to 256; full queue preserves idempotent readback; dead worker reports unhealthy and refuses new work.
- [x] Use SQLite transactions and exclusive process ownership; states `queued`, `running`, `completed`, `cancelled`, `failed`, `interrupted`. One worker job at a time, shared ledger `state_dir/budget.jsonl`, unique output under `state_dir/jobs/{id}`. Preserve queued jobs on restart; running jobs reconcile valid terminal summary or become interrupted. Never replay interrupted calls. Persist cancellation; runner polls DB callback. GET progress reports counts of completed artifacts, not raw responses; summary only when present and valid. Reject state/input path overlap and symlinks that could escape server roots.
- [x] Add restart-policy regression: without current startup live enablement, prior live jobs remain queued and offline jobs can run; later enabled startup can claim the live work. Pass the live policy through the worker and claim filter; historical admission must not bypass current execution permission.

```python
# Consumer-visible integration expectation; use temp real fixture bundle.
body = {'mode': 'dry_run', 'limit': 1, 'evaluate': False}
# POST twice with one key -> identical job_id; poll -> completed,
# summary.live_calls == 0 and summary.operational_effects == 0.
```

- [x] Run service tests and model tests; report red/green evidence and files, no commit.

### Task 3: Cloud preparation and documentation

**Files:** Create `deploy/cloud-run/README.md`, `deploy/cloud-run/job.template.yaml`, `Dockerfile.service`, `tools/dwelly_model/cloud_guard.py`, `tools/dwelly_model/tests/test_cloud_guard.py`, `docs/model-service.md`. May update root README links only after other agents finish. Do not modify runner/CLI or service package owned by siblings; coordinate guard hook to root.

**Interfaces:** `cloud_guard.reject_live_cloud(live: bool)` raises `ValueError('live_cloud_unavailable')` on live plus `K_SERVICE` or `CLOUD_RUN_JOB`. Root/Task 1 calls it before output. Local service independently refuses those environments. Job template invokes offline CLI only. Build local service Docker using existing stdlib tools plus new service package, non-root user, mounted writable state, read-only inputs.

- [x] Write guard tests first for live-cloud rejection and ordinary/offline allowance; run red.
- [x] Implement guard; provide valid Cloud Run Job YAML with `taskCount: 1`, `parallelism: 1`, `maxRetries: 0`, explicit timeout and resources, placeholder pinned image/service account/input mount. No secrets needed in offline template; document version-pinned Secret Manager for future live adapter only. State clearly that outputs are ephemeral in this smoke template and live cloud execution remains disabled.
- [x] Document local service run/poll/cancel and two diagrams using short text boxes: current deterministic/model boundary and target Cloud Run API → external queue/store → worker. Distinguish implemented, local-only and planned; no claim of real integrations, calibrated correctness or deployment. Explain offline cloud smoke preparation and not using SQLite/flock on FUSE, final-only upload insufficiency, required durable pre-dispatch claims, authentication and duplicate execution protection. Link official GCP sources.
- [x] Run guard tests, Dockerfile syntax/build if available without network dependency, and document residual cloud acceptance gates. No deploy, paid call, token inspection or commit.

### Task 4: Integration, independent review and archive

**Files:** Update this plan checkboxes, OpenSpec tasks, and `docs/verification/2026-10-10-parallel-model-service.md`.

- [x] Root reviews interface consistency; run `python3 -B -m unittest discover -s tools/dwelly_model/tests -v`, equivalent service and case suites, `git diff --check`, `openspec validate parallel-model-service --strict`.
- [x] Independent reviewer reads scoped diff and checks all requirements, concurrency/cancel/restart attacks and claim honesty; route fixes to file owners.
- [x] Run offline Docker service and batch smoke with networking disabled for providers; record exact results and omissions.
- [x] Commit reviewed files only, archive `parallel-model-service` using OpenSpec, preserve unrelated changes/evidence. Do not publish or deploy as part of this change.
