# Same-owner observed stop v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow authenticated stop of an admission-observed case in the same live v2 registered owner while preserving all original identities, business deadlines and accounting.

**Architecture:** A closed new factory key selects a larger exact first-party implementation inventory using the existing registered-release schema. Only a successfully completed observation in the current owner mints a private stop receipt. A tagged execution scope permits the existing engine stop path; fresh proof resolution and existing current-source authorization remain required.

**Tech Stack:** Python >=3.11, stdlib unittest/dataclasses/SQLite, current pinned Pydantic 2.13.5. No dependencies added.

**Spec:** `openspec/changes/archive/2026-10-10-observed-route-stop-v2/specs/observed-route-stop-v2/spec.md` and `openspec/changes/archive/2026-10-10-observed-route-stop-v2/specs/trusted-replay-case-provisioning/spec.md`; architecture in `openspec/changes/archive/2026-10-10-observed-route-stop-v2/design.md`. Independent architecture preflight corrected wait/fence preservation, inner JSON decoding and exact attempt joins before implementation. Completed bounded source leaf; see `docs/verification/2026-10-10-observed-stop-v2.md` for exact evidence and limits.

## Global Constraints

- Source-test interpreter is the existing qualified `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python`. Use the exact commands below, no installation.

- Exact new factory key: `fixed-synthetic-observed-stop-v2`. Existing default/key `fixed-synthetic-v1` remains run-only.
- Keep `HostExecutableBindingV1`, `LocalAdmissionCompositionV1`, `RegisteredReleaseV1`, claim/route/marker and journal/control schema versions unchanged.
- Profile remains exact supported v1.3, process v1, policy v1, SyntheticReplayClock exact type. No arbitrary profile, clock, factory, import, callback or code activation.
- Fresh private roots only for v2 preparation. Do not repin or modify historical roots, grants, markers, receipts or releases. Old mismatched executable pins continue to deny.
- Only a successfully observed case in this exact live owner/clock may stop. Registered recover/reply/restart/transfer stay denied. Stop-first host dispatch must not construct a runtime.
- Request/IDs: existing exact model validation; host IDs 1–256 nonblank characters; SHA-256 lowercase hex digests exactly 64 characters. Request fixture <=1,048,576 bytes; preserve the stricter existing request and fixture parser bounds.
- Release: 1–512 sorted normalized-unique implementation names, each implementation/blob <=1,048,576 bytes; aggregate encoded release <=8,388,608 bytes. Dependency names/hashes must equal both factory pins and embedded implementation blobs. Keep `completeness='unestablished'`.
- Claims/routes: <=4096 rows, <=262,144 bytes per row, <=8,388,608 aggregate route/claim bytes; route-store retained release bytes <=33,554,432. Public retained journal: <=4096 total rows, <=262,144 bytes per row, <=4,194,304 payload bytes.
- One stop I/O context clipped to <=5.0 seconds, with both UTC and monotonic bounds; no per-stage renewal. Existing SQLite VM limits remain <=1,000,000. Original business deadlines never extend. No post-deadline stop guarantee is introduced.
- Existing budgets remain max active 120 seconds, max tool calls 24, effects 6, planning 4, clarifications 2, per-intent reconciliation reads 3/retries 1, max tool seconds 10, reserved handoff effects >=1. Control reads use existing accounting; no reset or new admission.
- Compare immutable records exactly and debt semantically. Never assert blanket source/journal byte equality after an authorized/accounted read. Shared-pressure concurrency may settle; do not require it to increase monotonically.
- No providers, network, new dependencies, live operations, merges, pushes or publication. Evidence claims require executed tests and independent review. Implementation stays in the existing isolated worktree.

## Review Focus

- A stop requested as the first command must deny without opening/creating world/journal/control stores (Task 2 host test).
- A route observed before a failed final claim write must never mint stop authority (Task 2 injected failure test).
- Current source authorization may be revoked after admission even when the supplied proof digest matches (Task 2 accounted-revocation test).
- A timeout after the durable stop transaction must preserve the fence and clear the in-memory active capability (Task 2 post-commit interruption test).
- New source modules must not silently escape v2 inventory, and v1 must not inherit v2 control behavior (Task 1 inventory test and Task 2 v1 test).

## File map

| File | Responsibility |
|---|---|
| `runtime/src/proofkey/host_admission.py` | Closed per-key inventory, exact binding validation, private observed receipt/view/active stop token, semantic debt guard, stop entry |
| `runtime/src/proofkey/synthetic_provisioning.py` | Trusted `factory_key` selection and detached propagation through preparation |
| `runtime/src/proofkey/host.py` | `RuntimeResources.stop_registered`, registered dispatch routing without stop-first construction |
| `runtime/src/proofkey/gateway.py` | Forward explicit entry-kind to owner guard |
| `runtime/src/proofkey/engine.py` | Stop-only entry-kind plumbing |
| `runtime/tests/support_observed_stop_v2.py` | Test-only prepared fixture/context/snapshot and semantic assertion helpers |
| `runtime/tests/test_observed_stop_v2.py` | Inventory, owner, auth, timing, interrupted-state and host tests |
| `runtime/examples/observed_stop_v2.py` | Explicit trusted-library same-owner positive demonstration |
| `runtime/tests/test_observed_stop_v2_acceptance.py` | Real-clock trusted-library acceptance and receipt assertions |
| `docs/verification/2026-10-10-observed-stop-v2.md` | Actual commands/results, scope and unresolved work |

No edits planned to registered-release, route, journal, source, clock or persisted schema modules. If implementation requires those changes, return the concrete delta to the controller before expanding this leaf. Bootstrap already reconstructs binding with its fields and compares factory commitments; no change should be required.

---

### Task 1: Closed v2 inventory and trusted provisioning

**Files:** Modify `host_admission.py:106-133`, `synthetic_provisioning.py:94-104,217-274,618-659`; create test support and test module listed above.

**Interfaces:**

- Consume `SyntheticCaseReleaseSpecV1(host_release_id, registered_release_id, resource_id, request, fixture_bytes)` and existing `ReleaseBlobV1`, `KnownFactoryV1`, `ReleaseArtifactV1`, `ReleaseRegistryV1`.
- Produce `OBSERVED_STOP_V2_FACTORY_KEY: str`, `OBSERVED_STOP_V2_IMPLEMENTATION_PATHS: tuple[str, ...]`, private `_implementation_paths(factory_key: str) -> tuple[str, ...]`.
- Extend `prepare_synthetic_release(spec, *, parent, clock, execution, factory_key='fixed-synthetic-v1') -> PreparedSyntheticReleaseV1` and `_validate_input(spec, clock, execution, *, factory_key='fixed-synthetic-v1') -> _ValidatedInput`. Add detached `factory_key: str` to `_ValidatedInput`; preserve current positional callers by making only the function parameter keyword-only/defaulted.
- Test helper `prepared_case(factory_key='fixed-synthetic-observed-stop-v2', *, missing=False)` is a context manager yielding a SimpleNamespace with `parent, clock, state, prepared, request, auth, composition`. It prepares files but does not construct RuntimeResources.

- [x] **Step 1: Add actual red tests and the preparation helper.** Use existing test-only `paced_clock`, `case_data`, `cj`, `context`; `missing=True` changes `source['facts']['case.completeness']['value']='missing'` before hashing/preparation, never after runtime creation.

```python
# support_observed_stop_v2.py
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
from proofkey.contracts import AuthContext
from proofkey.host_admission import (
    LocalAdmissionCompositionV1, ProvisionedReviewResolverV1, SyntheticReviewGrantV1)
from proofkey.synthetic_provisioning import SyntheticCaseReleaseSpecV1, prepare_synthetic_release
from support_synthetic_provisioning import case_data, cj, context
from test_host_admission import paced_clock

@contextmanager
def prepared_case(factory_key='fixed-synthetic-observed-stop-v2', *, missing=False):
    with TemporaryDirectory() as folder, paced_clock() as (clock, state):
        parent = Path(folder).resolve()
        parent.chmod(0o700)
        request, source = case_data()
        # Task 2 fixture correction: the generic preparation fixture lacks
        # two typed packet facts required for actual flat-v1.3 execution.
        example = Path(__file__).resolve().parents[1] / 'examples/registered-cases/window-fixture.json'
        packet_facts = json.loads(example.read_text())['facts']
        for name in ('operator.packet_access', 'operator.packet_catalog'):
            source['facts'][name] = packet_facts[name]
        if missing:
            source['facts']['case.completeness']['value'] = 'missing'
        spec = SyntheticCaseReleaseSpecV1('J07-H', 'J07-L', 'J07-R', request, cj(source))
        prepared = prepare_synthetic_release(spec, parent=parent, clock=clock,
            execution=context(clock), factory_key=factory_key)
        grant = SyntheticReviewGrantV1('j07-review', prepared.binding.artifact_hash,
            'j07-synthetic-reviewer', 'admit_fixed_local_replay', 'synthetic_rehearsal',
            clock.now(), clock.now() + timedelta(minutes=10))
        composition = LocalAdmissionCompositionV1(prepared.registry, prepared.binding,
            ProvisionedReviewResolverV1((grant,)), grant.review_id, prepared.control_parent)
        yield SimpleNamespace(parent=parent, clock=clock, state=state, prepared=prepared,
            request=request, auth=AuthContext(caller_id=request.principal_id,
            proof_reference='j06-synthetic-proof'), composition=composition)
```

```python
def test_new_factory_uses_exact_existing_schema(self):
    import base64, json
    from hashlib import sha256
    with prepared_case() as fx:
        value = json.loads(fx.prepared.registry.resolve('J07-L').wire_bytes)
        dependency = json.loads(base64.b64decode(value['blobs']['dependency']['base64']))
        self.assertEqual(value['version'], 1)
        self.assertEqual(value['factory']['factory_id'], 'fixed-synthetic-observed-stop-v2')
        self.assertEqual(dependency['completeness'], 'unestablished')
        observed = tuple(item['name'] for item in dependency['entries'])
        self.assertEqual(observed, OBSERVED_STOP_V2_IMPLEMENTATION_PATHS)
        self.assertIn('clock.py', observed)
        self.assertIn('waits.py', observed)
        self.assertIn('execution_trace.py', observed)
        self.assertEqual([(e['name'], e['sha256']) for e in dependency['entries']],
            [(e['name'], e['sha256']) for e in value['implementations']])
        for item in value['implementations']:
            self.assertEqual(sha256(base64.b64decode(item['base64'])).hexdigest(), item['sha256'])
```

Add this parameterized binding test. Also test default preparation by directly calling `prepare_synthetic_release` without `factory_key` and assert both binding keys remain v1; test unknown key with a fresh TemporaryDirectory and assert no child allocated.

```python
def test_factory_and_inventory_cannot_be_mixed(self):
    from dataclasses import replace
    with prepared_case() as fx:
        binding = fx.prepared.binding
        pins = binding.implementation_pins
        old_pins = tuple(pair for pair in pins if pair[0] in FIXED_IMPLEMENTATION_PATHS)
        for update in (
            {'implementation_pins': old_pins},
            {'implementation_pins': tuple(reversed(pins))},
            {'implementation_pins': pins[:-1]},
            {'implementation_pins': pins + (pins[-1],)},
            {'factory_id': 'unknown', 'host_factory_key': 'unknown'},
            {'host_factory_key': 'fixed-synthetic-v1'},
        ):
            with self.subTest(update=update), self.assertRaises(ValueError):
                replace(binding, **update)
```

- [x] **Step 2: Run only the new tests red.** From repository root: `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_observed_stop_v2 -v`. Expected initial failure is missing v2 constants/unsupported factory_key; after API declaration, retain the behavioral red showing v2 is rejected or inventory is incomplete. Use the already qualified environment; do not install dependencies if this command selects an unqualified interpreter.

- [x] **Step 3: Implement the closed key map and explicit inventory.** Use the complete literal appendix in the public design, including `execution_trace.py` after `execution_consumer.py` and `trace.py` after `synthetic_provisioning.py`. This is an explicit reviewed tuple, not runtime filesystem discovery. Define lookup exactly:

```python
OBSERVED_STOP_V2_FACTORY_KEY = 'fixed-synthetic-observed-stop-v2'

def _implementation_paths(factory_key):
    if factory_key == 'fixed-synthetic-v1':
        return FIXED_IMPLEMENTATION_PATHS
    if factory_key == OBSERVED_STOP_V2_FACTORY_KEY:
        return OBSERVED_STOP_V2_IMPLEMENTATION_PATHS
    raise AdmissionCompositionFailure('unsupported_release')
```

Replace the old binding equality/list checks with `self.host_factory_key == self.factory_id`, then exact tuple length/names from `_implementation_paths`; retain all original ID/digest/type checks. Keep default host_factory_key v1. Add a test-only inventory coverage assertion comparing the literal v2 set with `*.py`/`schema.sql` paths under the source package; filesystem enumeration is allowed in this regression test only. If the concurrently completed trace work adds another first-party module, that test fails until its exact name is reviewed into the tuple.

- [x] **Step 4: Propagate detached factory_key through preparation.** In `_validate_input`, call `_implementation_paths` before any allocation; use selected names in the existing `_installed_bytes` loop. Use `role='data' if item.name == 'schema.sql' else 'code'` for dependency entries. Construct both validation-time and allocation-time `ReleaseArtifactV1`/`KnownFactoryV1` with the snapshotted key. Construct the executable binding with `host_factory_key=snapshot.factory_key`. Retain all _boundary calls, source fixture bytes, aggregate preflight and failure/cleanup semantics. Do not add a factory field to business input.

- [x] **Step 5: Run green and compatibility checks.** Run `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_observed_stop_v2 test_synthetic_provisioning test_synthetic_provisioning_cli test_release_route_foundation test_host_admission -v`. Review only this task's files. Controller may commit these exact files after its review; do not commit another agent's trace edits. Deliverable: v2 can be prepared and opened under its own exact pins, but no controls enabled yet.

### Task 2: Same-owner stop capability and registered host routing

**Files:** Modify `host_admission.py:508-785`, `host.py:249-254,623-677`, `gateway.py:65-87`, `engine.py:171-176,386-410`; expand `support_observed_stop_v2.py`, `test_observed_stop_v2.py`.

**Interfaces:**

- New public `RuntimeResources.stop_registered(case_id: str, generation: str, auth: AuthContext, *, execution: ExecutionContext) -> CaseResult | SavedResult` delegates to `RegisteredAdmissionOwner.stop` with identical parameters/return.
- Add keyword-only `entry_kind: str | None = None` to `WorkflowEngine._execution_scope`, `ActionGateway.execution_scope`, `RegisteredAdmissionOwner.guard_execution`.
- New private frozen dataclasses in host_admission: `_StopViewV2(binding: RequestBinding, request: CanonicalRequest, checkpoint: PhaseCheckpoint, request_row: bytes, admission_rows: bytes, intent_rows: bytes, wait_rows: bytes, wait_states: tuple[tuple[str,str,str | None], ...], request_stopped: bool)`; `_ObservedReceiptV2(claim: AdmissionClaimV1, route: RouteRecordV1, view: _StopViewV2)`; `_ObservedStopV2(execution: ExecutionContext, window: bytes, auth: AuthContext, receipt: _ObservedReceiptV2)`. Set `__reduce_ex__` on each capability/receipt to raise TypeError. `_StopViewV2` is data, not authority.
- Owner fields: `_created_clock`, `_stop_receipts: dict[tuple[str,str], _ObservedReceiptV2]`, `_stop_high_water: tuple[datetime,float]`; existing `active` holds either its existing admission tuple or exact `_ObservedStopV2`.
- Private `_inner_json(raw: str) -> dict`; `_stop_view(snapshot, case_id, generation, execution, clock, *, claim: AdmissionClaimV1, route: RouteRecordV1) -> _StopViewV2`; `_check_stop_continuity(before: _StopViewV2, after: _StopViewV2) -> None`.
- Test helper `opened_case(factory_key='fixed-synthetic-observed-stop-v2', *, missing=False)` wraps prepared_case, assigns `fx.runtime`, yields it and closes runtime in finally. `snapshot_rows(runtime, clock)` returns a dict of table name -> list of row dicts from the public retained snapshot.

- [x] **Step 1: Write the positive and semantic-accounting red test.** Add these support functions; no replacement engine/result.

```python
from proofkey.host import RuntimeFactory
import json

@contextmanager
def opened_case(factory_key='fixed-synthetic-observed-stop-v2', *, missing=False):
    with prepared_case(factory_key, missing=missing) as fx:
        fx.runtime = RuntimeFactory().create_registered(fx.prepared.host_release,
            fx.clock, composition=fx.composition, execution=context(fx.clock))
        try:
            yield fx
        finally:
            fx.runtime.close()

def snapshot_rows(runtime, clock):
    image = runtime.store.capture_retained_state(execution=context(clock), clock=clock)
    return {table['name']: [dict(zip(table['columns'], row)) for row in table['rows']]
        for table in json.loads(image.payload)['tables']}
```

```python
def test_same_owner_stop_preserves_original_and_charges_existing_case(self):
    with opened_case() as fx:
        r = fx.runtime
        first = r.run_registered(fx.request, fx.auth, execution=context(fx.clock, 120))
        key = (fx.request.case_id, first.binding.generation)
        before = r.store.checkpoint(key[0])
        original = r.store.original_request(*key)
        saved = r.store.saved_result(*key)
        claim = r.admission.claim_for_case(key[0], execution=context(fx.clock))
        route = r.admission.route_for_case(key[0], execution=context(fx.clock))
        attempts = snapshot_rows(r, fx.clock)['admission_attempts']
        effect_count = r.world.effect_count('reschedule')
        calls = len(r.world.calls)
        result = r.stop_registered(*key, fx.auth, execution=context(fx.clock))
        after = r.store.checkpoint(key[0])
        self.assertTrue(result.stop.requested)
        self.assertEqual(after.binding, before.binding)
        self.assertEqual(r.store.original_request(*key), original)
        self.assertEqual(r.store.saved_result(*key), saved)
        self.assertEqual(r.admission.claim_for_case(key[0], execution=context(fx.clock)), claim)
        self.assertEqual(r.admission.route_for_case(key[0], execution=context(fx.clock)), route)
        self.assertEqual(snapshot_rows(r, fx.clock)['admission_attempts'], attempts)
        self.assertEqual(r.world.effect_count('reschedule'), effect_count)
        self.assertEqual([c.operation for c in r.world.calls[calls:]], ['read_case'])
        self.assertLessEqual(after.deadline, before.deadline)
        self.assertGreater(after.budget.tool_calls, before.budget.tool_calls)
        assert_budget_continuity(self, before.budget, after.budget)
```

Implement `assert_budget_continuity(test, before, after)` in test support independently: assert case_id equal, deadline <=, all `max_*` and reserved_handoff_effects equal, scalar consumed active_seconds/tool_calls/planner_calls/effects/clarifications >=, each old reconciliation_reads/retries key retained with >= count, role keys/limits equal and invocations/cost/each prior usage >=. Do not compare `shared_account_pressure.concurrent_calls` monotonically or require equality of all checkpoint/source rows.

- [x] **Step 2: Write negative/failure red cases before implementing stop.** Each case below is a real test body to parameterize over fresh opened_case contexts:

The Task 1 generic preparation fixture can open a resource without being sufficient to execute it. Before testing stop, use the corrected helper above to copy the two exact typed packet envelopes from the already executed J06 window fixture before hashing/preparation. Preserve the failed setup attempts, then require actual complete and pending-wait admissions to reach the missing stop API. Do not relax retention, authorization or typed-envelope validators to obtain a RED.

```python
def test_v1_and_direct_engine_controls_stay_denied(self):
    for factory in ('fixed-synthetic-v1', 'fixed-synthetic-observed-stop-v2'):
        with opened_case(factory) as fx:
            r = fx.runtime
            first = r.run_registered(fx.request, fx.auth, execution=context(fx.clock, 120))
            calls = len(r.world.calls)
            self.assertEqual(r.engine.stop(fx.request.case_id, first.binding.generation,
                fx.auth, execution=context(fx.clock)).status, 'denied')
            self.assertEqual(r.engine.recover(fx.request.case_id, fx.auth,
                execution=context(fx.clock)).status, 'denied')
            if factory == 'fixed-synthetic-v1':
                with self.assertRaises(AdmissionCompositionFailure):
                    r.stop_registered(fx.request.case_id, first.binding.generation,
                        fx.auth, execution=context(fx.clock))
            self.assertEqual(len(r.world.calls), calls)

def test_post_commit_interruption_keeps_stop_and_wait_fence(self):
    class Interrupted(BaseException):
        pass
    with opened_case(missing=True) as fx:
        r = fx.runtime
        first = r.run_registered(fx.request, fx.auth, execution=context(fx.clock, 120))
        cp = r.store.checkpoint(fx.request.case_id)
        self.assertIsNotNone(cp.question_id)
        question = cp.question_id
        before_wait = r.store.load_wait_record(question)
        actual = CaseStore.stop_waits_atomic
        def interrupt(store, binding, expected):
            actual(store, binding, expected)
            raise Interrupted()
        with patch.object(CaseStore, 'stop_waits_atomic', interrupt):
            with self.assertRaises(Interrupted):
                r.stop_registered(fx.request.case_id, first.binding.generation,
                    fx.auth, execution=context(fx.clock))
        self.assertTrue(r.store.checkpoint(fx.request.case_id).stop.requested)
        self.assertEqual(r.store.load_wait_record(question).lifecycle, 'stopped')
        after_wait = r.store.load_wait_record(question)
        self.assertEqual(after_wait.model_dump(exclude={'lifecycle', 'successor_hash'}),
            before_wait.model_dump(exclude={'lifecycle', 'successor_hash'}))
        self.assertEqual(after_wait.wait.expires_at, before_wait.wait.expires_at)
        self.assertEqual(after_wait.wait.budget.deadline, before_wait.wait.budget.deadline)
        self.assertEqual(after_wait.origin_checkpoint, before_wait.origin_checkpoint)
        self.assertIsNone(r.admission.active)
        self.assertEqual(r.world.effect_count('reschedule'), 0)
        repeated = r.stop_registered(fx.request.case_id, first.binding.generation,
            fx.auth, execution=context(fx.clock))
        self.assertTrue(repeated.stop.requested)
        self.assertEqual(r.store.load_wait_record(question), after_wait)
```

Add concrete parameter tables for `(case_id,generation,auth)` wrong-target tests: `('foreign','G1',fx.auth)`, `(fx.request.case_id,'foreign',fx.auth)`, `(fx.request.case_id,'G1',fx.auth.model_copy(update={'caller_id':'foreign'}))`, `(fx.request.case_id,'G1',fx.auth.model_copy(update={'proof_reference':'wrong'}))`. Require AdmissionCompositionFailure and no source calls/admission changes. For current source revocation, after valid run use test-only `r.world.mutate('case.authorization', 'revoked')`; matching auth reaches existing source check, returns denied, preserves stop=False, and charges an existing case read. Do not compare whole snapshots for that accounted failure.

Add final-write injection by wrapping `_ClaimStore.write`: if `value['state']=='admission_observed'`, raise AdmissionCompositionFailure('storage'); otherwise call the original. The genuine run must leave route observed/claim sealed and no stop receipt. Add reopen test: successful run, `r.close()`, reconstruct RuntimeFactory with same release/composition/clock, call stop, require denial and no source call. Do not change existing pending-claim startup tests.

- [x] **Step 3: Run Task 2 tests red.** Use the Task 1 unittest command. Confirm initial absence of stop method, then retain behavioral red for missing live receipt/invalid operation tag after public API declaration.

- [x] **Step 4: Implement immutable projections and semantic continuity.** `_stop_view` reconstructs the public `RetainedStateSnapshotV1` envelope, then explicitly calls `_parse(snapshot.payload, 4194304)` for its canonical outer image. Convert each table row to a dict using its recorded columns; check time while iterating. Select exactly one `cases` row, one `requests` row and one `original_requests` row for the case/generation. Decode inner checkpoint/request/binding/attempt/account/wait JSON strings with the noncanonical decoder below, then `_model(decoded, ExactModel)`; decode versions_json with that decoder and compare its exact three expected keys/values. Keep existing claim `_parse` canonical behavior unchanged. `request_row` canonicalizes the request row without `stop_requested`, and `request_stopped` records that exact boolean separately. `admission_rows` canonicalizes all four admission tables' rows whose `claimed_case_id` equals case_id. Select the single admission attempt by `claim.attempt_id`, require its row/model state transferred and explicit identity map below; never access nonexistent attempt.claim_id or attempt.binding. Require one imported account for the same claimed case and zero pending_tool_calls/pending_active_seconds. `intent_rows` canonicalizes sorted pairs `(action_id,intent_json)` for that generation. Their immutable data do not change during stop.

`wait_rows` canonicalizes sorted `(question_id, case_id, generation, immutable_envelope)` entries for every exact case/generation wait. Decode as WaitRecordV1, deny legacy/unknown envelopes in this v2 capability, and remove only lifecycle and successor_hash from immutable_envelope. Preserve wait.expires_at, wait.budget, origin_checkpoint, graph, owner/communication context and accepted-reply fields exactly. `wait_states` records sorted `(question_id,lifecycle,successor_hash)` tuples. Require exact same wait IDs: lifecycle/successor is unchanged, or pending→stopped with nonnull successor_hash; stopped→pending is forbidden. Require a previously true checkpoint.stop.requested or request_stopped never becomes false. `_check_stop_continuity` compares immutable projections and full original/binding/version identity exactly, checkpoint deadline <=, and the budget helper below.

```python
def _inner_json(raw):
    _require(type(raw) is str, 'invalid')
    _require(0 < len(raw.encode('utf-8')) <= 262144, 'limit')
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, 'invalid')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(AdmissionCompositionFailure('invalid')))
    _require(type(value) is dict, 'invalid')
    _canonical(value)  # Reject overflow-to-infinity too; do not compare raw key order/spacing.
    return value

# claim and route are the validated exact original objects passed to _stop_view.
route_data = _parse(route.wire_bytes)
binding = claim.binding
expected = dict(attempt_id=claim.attempt_id, claimed_case_id=binding.case_id,
    claimed_object_id=binding.object_id, claimed_principal_id=binding.principal_id,
    request_id=binding.request_id, request_revision=binding.request_revision,
    consent_revision=binding.consent_revision,
    claimed_caller_id=route_data['auth_claim']['caller_id'],
    proof_digest=route_data['auth_claim']['proof_digest'],
    business_fingerprint=route_data['business_fingerprint'],
    request_hash=route_data['request_hash'], dedup_hash=route_data['dedup_hash'])
_require(attempt_row['attempt_id'] == claim.attempt_id
    and attempt_row['claimed_case_id'] == binding.case_id
    and attempt_row['dedup_hash'] == expected['dedup_hash']
    and attempt_row['state'] == attempt.state == 'transferred'
    and attempt.deadline > attempt.created_at, 'scope')
_require(all(getattr(attempt, key) == value for key, value in expected.items()), 'scope')
```

The bounded captured model strings are not rewritten before decoding. Host claim_id is checked only as part of the exact host claim; current immutable attempt row/model (including created_at/deadline) must match the observation receipt.

Add these concrete parser/join/projection regressions to `test_observed_stop_v2.py`. The two helper functions below are test-only and must not be imported by production. They preserve the real captured inner encodings unless a negative test explicitly mutates one field:

```python
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from proofkey.host_admission import _inner_json, _stop_view, _check_stop_continuity

def captured_view(fx, snapshot=None):
    r, clock = fx.runtime, fx.clock
    if snapshot is None:
        snapshot = r.store.capture_retained_state(execution=context(clock), clock=clock)
    claim = r.admission.claim_for_case(fx.request.case_id, execution=context(clock))
    route = r.admission.route_for_case(fx.request.case_id, execution=context(clock))
    return snapshot, _stop_view(snapshot, fx.request.case_id, claim.binding.generation,
        context(clock), clock, claim=claim, route=route)

def changed_inner(snapshot, table_name, column, update):
    image = json.loads(snapshot.payload)
    table = next(item for item in image['tables'] if item['name'] == table_name)
    index = table['columns'].index(column)
    assert len(table['rows']) == 1
    value = json.loads(table['rows'][0][index])
    update(value)
    table['rows'][0][index] = json.dumps(value)
    payload = cj(image)
    return replace(snapshot, payload=payload, content_hash=sha256(payload).hexdigest())

def test_real_noncanonical_inner_strings_parse_and_exact_attempt_joins(self):
    with opened_case(missing=True) as fx:
        fx.runtime.run_registered(fx.request, fx.auth, execution=context(fx.clock, 120))
        snapshot, view = captured_view(fx)
        image = json.loads(snapshot.payload)
        strings = [row[i] for table in image['tables']
            for i, column in enumerate(table['columns']) if column.endswith('_json')
            for row in table['rows'] if isinstance(row[i], str)]
        self.assertTrue(any(raw.encode() != cj(json.loads(raw)) for raw in strings))
        claim = fx.runtime.admission.claim_for_case(fx.request.case_id, execution=context(fx.clock))
        self.assertNotEqual(claim.claim_id, claim.attempt_id)
        self.assertEqual(view.binding, claim.binding)
        for field, bad in (('claimed_principal_id', 'foreign'), ('proof_digest', '0' * 64),
                           ('request_hash', '0' * 64), ('attempt_id', claim.claim_id)):
            altered = changed_inner(snapshot, 'admission_attempts', 'attempt_json',
                lambda value, field=field, bad=bad: value.__setitem__(field, bad))
            with self.subTest(field=field), self.assertRaises(AdmissionCompositionFailure):
                captured_view(fx, altered)

def test_inner_json_rejects_duplicates_nonfinite_and_oversized_strings(self):
    for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}',
                '{"a":"' + 'x' * 262144 + '"}'):
        with self.subTest(prefix=raw[:30]), self.assertRaises(ValueError):
            _inner_json(raw)

def test_wait_expiry_context_and_observed_stop_fences_cannot_regress(self):
    with opened_case(missing=True) as fx:
        r = fx.runtime
        first = r.run_registered(fx.request, fx.auth, execution=context(fx.clock, 120))
        snapshot, before = captured_view(fx)
        question = r.store.checkpoint(fx.request.case_id).question_id
        record = r.store.load_wait_record(question)
        def shorten(value):
            reduced = record.wait.model_copy(update={
                'expires_at': record.wait.expires_at - timedelta(seconds=1)})
            value['wait']['expires_at'] = reduced.model_dump(mode='json')['expires_at']
        altered = changed_inner(snapshot, 'waits', 'wait_json', shorten)
        _, changed = captured_view(fx, altered)
        with self.assertRaises(AdmissionCompositionFailure):
            _check_stop_continuity(before, changed)
        r.stop_registered(fx.request.case_id, first.binding.generation,
            fx.auth, execution=context(fx.clock))
        _, stopped = captured_view(fx)
        _check_stop_continuity(before, stopped)
        for regressed in (
            replace(stopped, request_stopped=False),
            replace(stopped, checkpoint=stopped.checkpoint.model_copy(update={
                'stop': stopped.checkpoint.stop.model_copy(update={'requested': False})})),
            replace(stopped, wait_states=((question, 'pending', None),)),
        ):
            with self.assertRaises(AdmissionCompositionFailure):
                _check_stop_continuity(stopped, regressed)
```

Continue with the budget helper; lifecycle comparisons are separate from budget comparisons so legitimate accounted reads remain permitted:

```python
def _check_budget_continuity(before, after):
    from .budget import preserve_budget, validate_budget
    validate_budget(after)
    preserve_budget(after, before)  # checks frozen limits; returned ledger is not used
    _require(after.case_id == before.case_id and after.deadline <= before.deadline, 'scope')
    for key in ('active_seconds', 'tool_calls', 'planner_calls', 'effects', 'clarifications'):
        _require(getattr(after, key) >= getattr(before, key), 'scope')
    for key in ('reconciliation_reads', 'retries'):
        old, new = getattr(before, key), getattr(after, key)
        _require(all(new.get(name, -1) >= count for name, count in old.items()), 'scope')
    for name, old in before.role_allowances.items():
        new = after.role_allowances[name]
        _require(new.invocations >= old.invocations and new.cost >= old.cost
            and all(new.usage.get(key, -1) >= count for key, count in old.usage.items()), 'scope')
```

Mint the receipt using the already captured successful run journal snapshot and final observed claim/route after all final checks, passing `claim=observed_claim, route=observed_route` to `_stop_view`. Save exact original admission attempt and wait projections; store current observed budget as its immutable floor. Do not mint on exceptions, final time failure, v1, prepared or sealed claims. Keep the receipt map <=4096 cases. Reset it on close. For each stop validate exact claim/route equality to receipt, both observed, look up same route by generation, deny any pending claims and compute current journal view with one fresh bounded capture. Compare to receipt and to the last successfully retained stop view. Retain each successfully validated preflight view as the observed floor before engine dispatch, so an already observed stopped fence cannot regress even if later work fails. After an attempted engine stop capture/update the nondecreasing floor only if bounded time remains. Never perform a second capture merely to make an already expired operation appear successful, and never roll back committed accounting/fences if postflight cannot complete.

- [x] **Step 5: Implement stop token/guard and operation routing.** The token window is canonical `_window(control)` bytes; compare on every owner guard. Copy typed auth before storing it. Save `_created_clock=clock`; reject clock alias changes, nonfinite/reversed clock observations, uncertain/closed/reentrant/cross-thread operations. Require original principal and proof digest before case material lookup. Use the same `control=control_context(execution,self.clock)` object for all preflight and engine work. Owner stop core:

```python
# After the exact owner/clock/auth/claim/route/current-view checks above:
self.active = _ObservedStopV2(control, _canonical(_window(control)), auth, receipt)
try:
    result = self.engine.stop(case_id, generation, auth, execution=control)
    self.guard_execution(control, self.gateway, entry_kind='stop')
    return result
finally:
    self.active = None
```

In guard, exact `_ObservedStopV2` requires `entry_kind=='stop'`, matching owner/gateway/execution, unchanged window, unchanged current control clock, remaining time >0; admission tuple retains its old guard and additionally requires entry_kind None. `require_entry` rejects non-tuple active tokens before unpacking. In engine stop only, use `with self._execution_scope(execution, entry_kind='stop')`; all other entrypoints keep default None. Gateway forwards the tag to owner before opening store.execution_scope. Do not alter authenticate_control, stop_waits_atomic, graph transition, effect reconciliation or result construction.

In host `_execute`, replace registered non-run blanket denial with closed allowed routing: run unchanged; stop allowed only when binding factory key v2 and `_resources is not None`; all other tags deny. Skip runtime creation for denied stop-first. Actual registered stop dispatch is `self._resources.stop_registered(command.case_id, command.generation, auth, execution=state.execution)`, ordinary unregistered engine.stop unchanged. RuntimeResources method uses exact owner type and delegates, matching run_registered error style.

- [x] **Step 6: Add timing, alias and host tests with exact seams.** Wrap `_ClaimStore.find` and `AdmissionRouteStoreV1.get` to advance `fx.state['tick']` by 3.0 each after calling the real method; stop must fail before any new source call because the same five-second context is exhausted. Use `ThreadPoolExecutor(max_workers=1).submit(r.stop_registered, case, generation, auth, execution=context(clock)).result()` and require denial. Patch `r.engine`/`r.store`/`r.world` individually to object(), restore in finally, require denial; call owner with the old original fields restored and ensure clean close. Change marker bytes in a test-owned root, require denial, restore them only for cleanup.

Host test uses `AuthResolver({'user':fx.auth})`, `HostDispatcher(RuntimeFactory(),resolver,ProfileRegistry((release,)),clock,prepared.inventory_parent/'host',HostLimitsV1(),release_id='J07-H',admission_composition=composition)`. Submit `RunCommandV1(release_id='J07-H',request=fx.request)` and `StopCommandV1(release_id='J07-H',case_id=case,generation='G1')` with `resolver.handle('user')`. Require stop result and clean owner_closed shutdown. In a new dispatcher patch RuntimeFactory.create_registered with `side_effect=AssertionError('stop opened runtime')`; stop-first must return denied without that exception. Active registered RecoverCommandV1 and a valid-shaped ReplyCommandV1 remain denied. Build the latter from the real pending wait's binding/question/recipient and `ScopedReply` fields, using `received_at=clock.now(),simulated=True`; never accept it in this leaf.

- [x] **Step 7: Green and review.** Run `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_observed_stop_v2 test_host_admission test_host_contracts test_gateway_control test_stop test_waits test_operator_wait_gateway -v`. Review task files only and verify no admission/schema/recover/reply behavior changed. Controller may commit the exact reviewed files; preserve concurrently owned trace work. Deliverable: local same-owner v2 stop with bounded preflight, current source authorization, durable fence and negative compatibility evidence.

### Task 3: Explicit trusted-library acceptance and scoped documentation

**Files:** Create `runtime/examples/observed_stop_v2.py`, `runtime/tests/test_observed_stop_v2_acceptance.py`, `docs/verification/2026-10-10-observed-stop-v2.md`. Controller owns the separate OpenSpec proposal/tasks/spec and archival.

**Interfaces:** `run_demo(parent: Path) -> dict` in the new example; it reads only the existing `runtime/examples/registered-cases/window-request.json` and `window-fixture.json`, creates a fresh v2 release, explicitly grants synthetic review for its hash, uses a real SyntheticReplayClock and one RuntimeFactory resource, runs then stops and returns a public-safe summary. Its output has exact keys `scope,factory_id,artifact_hash,run_status,stop_requested,original_generation,original_request_preserved,claim_preserved,route_preserved,deadline_not_extended,tool_calls_before,tool_calls_after,business_effects_before,business_effects_after,owner_closed`. No credentials, raw source, private paths or review identities in output.

Add `run_pending_demo(parent: Path) -> dict` for the separate real-clock pending-wait acceptance required by the binding spec. It uses the same one-read input pattern, then changes only `facts.case.completeness.value` to `missing` in the in-memory fixture before preparation/hashing. It must not alter a prepared/opened source. Share the preparation/run/stop/close implementation through one private helper, not duplicated business logic. Its output has the base keys above plus exactly `wait_observed,wait_stopped,wait_context_preserved,wait_expiry_preserved`, all four true only after an actual pending WaitRecordV1 is observed and becomes stopped. Base `business_effects_*` means persisted reschedule count (zero for the pending case); a clarification is not a business reschedule. The complete-case interface/output remains unchanged.

- [x] **Step 1: Add an actual failing acceptance test.** Load the example with `runpy.run_path(str(Path(__file__).resolve().parents[1]/'examples/observed_stop_v2.py'))` and invoke returned `run_demo`. The initial missing-file failure establishes the red; after file creation preserve the behavioral assertions:

```python
def test_real_clock_trusted_library_same_owner_acceptance(self):
    from pathlib import Path
    from tempfile import TemporaryDirectory
    import runpy
    with TemporaryDirectory() as folder:
        parent = Path(folder).resolve()
        parent.chmod(0o700)
        demo = runpy.run_path(str(Path(__file__).resolve().parents[1] /
            'examples/observed_stop_v2.py'))['run_demo']
        receipt = demo(parent)
        self.assertEqual(receipt['scope'], 'trusted-library-same-owner-no-restart')
        self.assertEqual(receipt['factory_id'], 'fixed-synthetic-observed-stop-v2')
        self.assertEqual(receipt['run_status'], 'authorized')
        for key in ('stop_requested', 'original_request_preserved', 'claim_preserved',
                    'route_preserved', 'deadline_not_extended', 'owner_closed'):
            self.assertIs(receipt[key], True, key)
        self.assertEqual(receipt['business_effects_before'], receipt['business_effects_after'])
        self.assertGreater(receipt['tool_calls_after'], receipt['tool_calls_before'])
```

Add a second RED test `test_real_clock_pending_wait_is_stopped_without_changing_context` that calls `run_pending_demo` from the same runpy-loaded example in a separate TemporaryDirectory. Assert scope/factory/run_status as above, all original preservation/stop/closure booleans true, all four wait booleans true, reschedule counts both zero and accounted tool calls increased. Before/after comparison excludes only WaitRecordV1.lifecycle/successor_hash; original wait expiry, budget deadline and origin checkpoint must be exactly equal. Do not monkeypatch the clock, engine or wait creation. Missing example/function is the initial RED; real pending source behavior is the GREEN.

- [x] **Step 2: Implement the example with real APIs and guaranteed close.** Read request/fixture bytes once; create `SyntheticCaseReleaseSpecV1('J07-DEMO-H','J07-DEMO-L','J07-DEMO-R',request,fixture_bytes)`; call prepare_synthetic_release with new key and a five-second execution; create `SyntheticReviewGrantV1('j07-demo-review',prepared.binding.artifact_hash,'j07-demo-reviewer','admit_fixed_local_replay','synthetic_rehearsal',clock.now(),clock.now()+timedelta(minutes=10))`; use AuthContext(request.principal_id,'j06-synthetic-proof') via keyword fields. Build LocalAdmissionCompositionV1 from prepared objects. Call RuntimeFactory.create_registered, then inside try call run_registered with a 120-second context, capture original request/checkpoint/claim/route/effect_count, call stop_registered with a five-second context, derive the named summary booleans/counters using the same checks as Task 2. For the pending variant also capture the actual pending wait before stop and compare its immutable envelope/expiry afterward; absence of the expected pending wait is a failure, not a false/omitted passing field. In finally call resources.close(); set owner_closed only from `resources.closed is True` after successful close. A close or command exception must propagate; never return a passing receipt on exception. Keep prepared roots for inspection rather than deleting evidence in the example.

Add this exact CLI wrapper to the example:

```python
if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description='Explicit synthetic same-owner v2 stop demo')
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--pending-wait', action='store_true')
    args = parser.parse_args()
    demo = run_pending_demo if args.pending_wait else run_demo
    print(json.dumps(demo(args.parent), sort_keys=True))
```

This is trusted-library acceptance from the checkout, not an installed-wheel or CLI restart claim. It uses the real source adapters locally, no providers/network and no monkeypatched clock. Reuse of J06 input bytes does not replace J06 historical receipts; this is a new v2 artifact/root/receipt.

- [x] **Step 3: Run acceptance and final gates once.** Run `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_observed_stop_v2_acceptance -v`. Retain the completed Task 2 focused group for its exact unchanged executable/test hashes instead of redundantly rerunning that group after example/document-only changes; rerun any actually changed relevant code/test path. The controller then runs `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest discover -s runtime/tests -v` on the final committed source archive, including the new acceptance test. The implementer does not start a competing full suite. Save actual commands, exit codes, durations, test counts/failures and candidate hashes. Repeat only to address a diagnosed new failure/change, preserving failed attempt evidence.

- [x] **Step 4: Write factual verification document and archive only the approved stop leaf.** Document exact candidate commit/source hashes, v2 artifact/dependency hashes and literal inventory, fresh-root identity, real-clock local acceptance, stopped generation, preserved originals/claim/route/deadlines, increased accounted tool calls, unchanged business effects and confirmed close. State unimplemented recover/reply/restart, unsupported post-deadline stop, source/constructor hostile-state limits and no external human-review/provider proof. Include actual red/green failures instead of invented expected results. Link the independent review outcome when it exists; do not invent approval. Controller validates its separate OpenSpec change and archives that leaf after checks, keeping J07 broader integration and unrelated trace work separately classified. No old root/grant/marker is changed.

## Self-review

Coverage: Task 1 owns factory/inventory/provisioning/schema compatibility; Task 2 owns live receipt, identity/debt/time/authority/fence/host behavior; Task 3 owns real-clock trusted-library acceptance and factual docs. The five Review Focus items each have named executable tests. All new APIs/types/helpers are declared above; all source-only helper algorithms have their row/field inputs and failure rules specified. Exact first-party inventory comes from the public OpenSpec design's literal appendix plus the currently present execution_trace.py; the regression coverage test catches future drift. This plan makes no execution claim. Independent preflight findings and their scoped clearance are retained in the preceding trace leaf's evidence; implementation and final verification remain required.
