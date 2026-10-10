# Window Readiness Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the exact opt-in J05 synthetic window readiness delta and collect independently bound current-source evidence without claiming historical pending preservation.

**Architecture:** Extend existing profile, factory, world, scheduling, gateway, engine and host modules. Four separately leased readiness reads feed a finite engine branch; source-owned raw scheduling bytes pass a bounded decoder; exact semantic and source commitments authorize only the declared v3 composition.

**Tech Stack:** Existing Python >=3.11, standard-library unittest/SQLite/JSON and installed Pydantic 2.13.5; the existing source-test interpreter only. No dependency, network, installation or DDL work.

**Spec:** `openspec/changes/window-readiness-adaptation/{proposal,design,tasks}.md` and its four `specs/*/spec.md` files. Read those seven files in full before execution. The formal artifacts and corrected draft have C0/I0/M0 reviews. This promoted plan still requires its final independent review before Task 1.

## Global Constraints

The following requirements are copied verbatim from the approved design/specs; all five tasks inherit them.

- The design depends on completed and archived `observed-route-stop-v2` and its source freeze.
- A separate reviewed Superpowers plan must follow this change's tasks before implementation.
- No new package modules or dynamic graph interpreter are introduced, preserving stop-v2's all-package path assertion.
- Keep public `SchedulingPort` signatures unchanged.
- All candidate scheduling reads use raw envelopes because `ReadRequest` has no process version. Candidate window dispatch uses raw; candidate exact-slot dispatch remains typed. Legacy profiles remain typed.
- Full positive execution must fit 24 calls, 120 active seconds and 10 seconds per tool; fit is unmeasured. Raising limits or concealing reads is not an acceptable remedy.
- Bounds are inclusive and conjunctive: complete UTF-8 bytes at most 262,144; container depth at most 16 starting with root object depth 1; at most 128 observations; identifiers/revisions/reason at most 1024 Unicode code points; at most 128 **evidence occurrences** across all body references, each observation reference and non-null nonexecution reference, counting repeats.
- There is no typed fallback, limit relaxation, truncation or observation/effect deletion.
- Over-bound pre-write data causes no new business dispatch; over-bound post-write readback preserves the possibly committed effect, original key, intent and debt with unknown status and zero resend/undo.
- All permission, authority, idempotency, conditional coverage, terminal basis, timeout, evidence mode, account/quota/rate settings remain equal to baseline.
- Mappings, authorities, policy hash, capability/process key sets and every other process are unchanged. There is no handoff supplement edit.
- The complete semantic top-level diff is exactly `capabilities` and `processes`.
- Keep the stop-v2 tuple and its equality test unchanged.
- Final J05 source hashes are frozen after implementation and the prior leaf freeze; old historical hashes are not repinned.
- Candidate controls remain denied by key-specific guards even after v2 adds same-owner stop.
- Completion of current-source tasks SHALL NOT close that historical gate or parent J05.
- No installation or external release step is included.

**Handoff context (operational, not a specification quotation):** Each worker receives only its own task plus this Global Constraints section; reading other tasks or the whole plan is not required. Existing producer outputs are consumed through the signatures repeated in that worker's task. Worktree root is `/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project`; run all commands there. The existing interpreter is `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests`; no installation fallback. The prerequisite stop leaf is archived with runtime candidate `4c8fd5a8d515aec6fe9cbd8453f5663027f84ecd`; final independent plan review is required before execution. The controller supplies the applicable approved OpenSpec artifacts with each extracted task.

## Review Focus

1. An equal-epoch owner response carries an empty, boolean or different owner: reject before successful lease settlement, with no dispatch (Task 3, `test_owner_validation_precedes_settlement`).
2. Individually plausible raw fields jointly exceed the evidence bound, or repeat the same evidence 129 times: reject the complete envelope rather than deduplicate or return a prefix (Task 2, `test_conjunctive_limits_and_repeated_evidence`).
3. An effect commits but the original read is malformed or out of domain: retain the exact intent/key/effect/debt and perform zero resend/undo (Task 2 direct source test and Task 3 `test_committed_effect_survives_unreadable_original`).
4. A stop or source/checkpoint revision changes during the fourth read or before save: retain the latest budget/stop and do not advance (Task 3, `test_readiness_races_preserve_latest_checkpoint`).
5. Candidate raw reads accept 1024-character references but reject legacy-valid 1025-character references, including unchanged exact-slot consumers: report a domain denial, not universal parity (Task 2 direct adapter, Task 3 workflow, Task 5 reporting; `test_legacy_reference_domain_contrast`).

---

## Prerequisite freeze and execution gate

Stop-v2 is complete and archived at `openspec/changes/archive/2026-10-10-observed-route-stop-v2/`. Its exact runtime candidate is `4c8fd5a8d515aec6fe9cbd8453f5663027f84ecd`: 1,829 tests passed, zero skips, all 281 runtime files unchanged during execution. Receipt: `outputs/proofkey-observed-stop-full-4c8fd5a/receipt.json` (SHA-256 `cf6fb440bc202951896832197bdd29f497f7325b05e5069da04bd2d09e6ae34c`). This qualifies only that source candidate, not this unimplemented J05 change.

The shared provisioning deltas were reconciled against the archived v1/v2 living contract. The source anchors below were rechecked against unchanged package code. Runtime README and specification closure edits do not change those package bytes. Historical roots and pins remain untouched.

The controller must finish independent review of this promoted plan before dispatching Task 1. Each task is separately implemented with TDD and independently reviewed. Final J05 source pins are frozen once after the package and qualification-lane changes, never copied from the historical stop candidate. Parent J05 remains open for its unmet historical-pending and wider qualification gates.

Working directory for all future commands: `/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project`.

Existing test interpreter (must still exist and match its recorded environment at promotion): `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python`. No install fallback. Run commands below with `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests`. Expected red means a named new behavior fails, not an import/environment failure. If the initial failure is an absent API, define its signature and retain a behavioral red before implementing it.

## File and interface map

| Owner | Exact files | Responsibility |
| --- | --- | --- |
| Task 1 | `runtime/src/proofkey/profiles.py`; `runtime/src/proofkey/factory/proposal.py`; `runtime/src/proofkey/factory/release.py`; `runtime/src/proofkey/factory/__init__.py` | Exact profile delta/compatibility helper, independent literal inventory, frozen registration, proposal/review/staging bindings |
| Task 1 | `runtime/profiles/flat-window-readiness-v1.json`; `runtime/src/proofkey/resources/profiles/flat-window-readiness-v1.json`; `runtime/pyproject.toml`; `runtime/MANIFEST.in` | New byte-identical resource/mirror and explicit package entries |
| Task 1 | `runtime/tests/test_window_readiness_registration.py`; `runtime/tests/support_window_readiness.py`; `runtime/tests/test_installed_resources.py` | Independent candidate oracle, registration mutation tests, resource assertions; test support is outside the package |
| Task 2 | `runtime/src/proofkey/adapters/world.py`; `runtime/src/proofkey/adapters/scheduling.py`; `runtime/src/proofkey/source_retained_state.py`; `runtime/tests/test_window_readiness_envelopes.py` | Shared source data, raw decoder, provider compatibility/S0 CAS, original joins, full-ID retained capture and direct source tests |
| Task 3 | `runtime/src/proofkey/gateway.py`; `runtime/src/proofkey/engine.py`; `runtime/src/proofkey/policy.py`; `runtime/tests/test_window_readiness_engine.py` | Four-call helper, guarded save, fresh policy S0 and real-engine preservation/domain/budget/race tests |
| Task 4 | `runtime/src/proofkey/host_admission.py`; `runtime/src/proofkey/synthetic_provisioning.py`; `runtime/src/proofkey/host.py`; `runtime/src/proofkey/profiles.py`; `runtime/tests/test_window_readiness_composition.py`; `runtime/tests/support_window_readiness.py` | Closed selection, corrected typed-packet source fixture, library/CLI paths, finalized evidence and control denials |
| Task 5 | `runtime/tests/support_factory_lanes.py`; `runtime/tests/test_factory_current_v1.py`; `runtime/tests/test_adaptation_factory.py`; `runtime/tests/test_factory_registration.py`; `runtime/tests/test_factory_qualification.py`; `runtime/scripts/qualify_factory.py` | Explicit current-source v1 comparison context, preserved historical denial/vectors, refactored existing behavioral and outer tests, closed qualifier selector |
| Task 5 | `runtime/scripts/qualify_window_readiness.py`; `runtime/tests/test_window_readiness_evidence.py`; `runtime/tests/fixtures/window-readiness-current-registration-v1.json` | Nonrecursive J05 runner, outer tests and final expected 86-source pins outside the package closure |
| Task 5 | `outputs/window-readiness-adaptation-<unique-run-id>/`; OpenSpec child tasks/review and archive | Exact-run evidence, limits and finite child closure, with parent J05 still open |

No file under `runtime/src/proofkey` is added. No schema or public contract/port changes are planned. Existing tests and fixed historical fixtures are retained; new current-source tests must not repin `factory-current-registration-v1.json` or rewrite `factory-legacy-vectors-v1.json` to make old evidence appear current.

Inspected existing interfaces: `load_profile(path) -> EnvironmentProfile`, `validate_profile(profile) -> EnvironmentProfile`; `_material_proposal(material, implementation_registration=None)` returns `(proposal, candidate, baseline, body)`; `AdaptationFactory._resolve(proposal)` returns `(material, expected, candidate, baseline, body)`; `stage_release(factory, review_packet, human_approval, pending_intents) -> StagedRelease`; `SchedulingAdapter(world)` has `list_permitted_slots(request)`, `read_schedule(request)` and `reschedule(intent, *, deadline=None)`; `SimulatedWorld._dispatch(operation, intent, *, deadline=None, auth=None)` and `_read(operation, request)` are the current typed seams. `ActionGateway._facts(scope, fields, *, attempt_id=None, deadline=None, purpose=None, validators=None)` returns an observation tuple; validators run inside `_leased_read` before `_settle`. `_source_validators(binding, checkpoint, *, recipient_key=None, packet=False)` maps authority names, including `ownership`, to validators. `WorkflowEngine._save(checkpoint, **changes)` constructs/saves/reloads a checkpoint; it does not itself refresh stale caller data. `build_test_runtime(folder, before_commit=None, *, request=None, profile_name='flat-v1.2')` returns an existing `RuntimeFixture` with engine/store/world/clock/profile/auth/request.

### Task 1: Exact profile, detached registration and resources

**Files:**

- Modify: `runtime/src/proofkey/profiles.py`, `runtime/src/proofkey/factory/proposal.py`, `runtime/src/proofkey/factory/release.py`, `runtime/src/proofkey/factory/__init__.py`.
- Create: `runtime/profiles/flat-window-readiness-v1.json`, `runtime/src/proofkey/resources/profiles/flat-window-readiness-v1.json`, `runtime/tests/test_window_readiness_registration.py`, `runtime/tests/support_window_readiness.py`.
- Modify: `runtime/pyproject.toml`, `runtime/MANIFEST.in`, `runtime/tests/test_installed_resources.py`.
- Read-only existing test dependencies: `runtime/tests/support.py`, `runtime/tests/support_synthetic_provisioning.py`, `runtime/tests/test_factory_registration.py` (literal-vector case only).

Anchors: `profiles.py:67` loader, `:85` validation; `factory/proposal.py:70` semantic matcher, `:110` material reconstruction, `:272` context and `:285` constructor; `factory/release.py:32` staging. Re-resolve line numbers after prerequisite freeze.

**Interfaces consumed:** Existing `EnvironmentProfile`, `fingerprint(value)`, `canonical(value) -> bytes`, `wire(model) -> bytes`, `ProposalMaterial`, and all existing regression/review contracts. `ProposalMaterial` already owns baseline/candidate/supplement bytes and a tuple of source byte pairs.

**New interfaces produced:**

- `profiles.WINDOW_READINESS_FACTORY_KEY: str = 'fixed-synthetic-window-readiness-v3'`, `WINDOW_READINESS_PROFILE_ID: str = 'flat-window-readiness-v1'`, `WINDOW_READINESS_PROCESS_VERSION: str = 'v2-window-readiness'`, `WINDOW_READINESS_IMPLEMENTATION_PATHS: tuple[str, ...]`.
- `profiles._window_readiness_profile_data(baseline: EnvironmentProfile) -> dict` builds only the enumerated delta and all derived hashes, rejecting any baseline hash except `5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4`.
- `profiles.is_window_readiness_profile(profile: EnvironmentProfile) -> bool` compares the entire validated candidate wire data to `_window_readiness_profile_data(load_profile('flat-v1.3'))`; it returns false for a forged ID or invalid hashes.
- `profiles.supports_process_operation(profile: EnvironmentProfile, process_version: str, operation: str, consent_mode: object) -> bool` retains legacy `process_version == 'v1'`; for the exact candidate, v2 requires source mode `window` and operation membership in `reschedule_window.operations`; candidate v1 reschedule requires source mode `exact_slot`, and other v1 operations must belong to an unchanged v1 process. No blanket v2 goods/service admission.
- `profiles._window_original_request_id(*, account_id: str, provider_key: str, case_id: str, object_id: str, operation: str, generation: str, action_id: str, fingerprint: str, identity_hash: str) -> str` is a pure helper over these exact stored-field names. It validates exact nonempty identifier strings, operation='reschedule', and exact lowercase 64-hex fingerprint/identity_hash; it hashes the explicit dictionary plus fixed domain `synthetic-window-original-v1` and prepends fixed `provider:window-envelope-v1:`. It has no namespace, callback, profile or caller-selected domain argument and imports no adapter or retained-state module. Callers separately validate exact candidate/source authority.
- Frozen/slotted `WindowReadinessRegistrationV1(registration_id: str, provenance: str, host_factory_key: str, baseline_hash: str, candidate_hash: str, process_hash: str, policy_hash: str, implementations: tuple[tuple[str, str], ...])` exported through existing `factory/__init__.py`.
- `FactoryContext.process_delta_registration: WindowReadinessRegistrationV1 | None = None` appended with the existing legacy default preserved.
- `_normalize_window_registration(registration) -> WindowReadinessRegistrationV1 | None`; `_window_registration_commitment(registration) -> dict`; `_material_proposal(material, implementation_registration=None, process_delta_registration=None)` with the same return tuple.
- Test support `expected_candidate() -> EnvironmentProfile` constructs the candidate independently from baseline JSON; `window_material(candidate: EnvironmentProfile, sources: tuple[tuple[str, bytes], ...]) -> ProposalMaterial`; `window_context(material, registration, *, regressions=(), reviews=(), pending=()) -> FactoryContext`. Test builders explicitly set baseline/supplement to flat-v1.3, the complete diff to capabilities/processes, the two expected old affected IDs, and do not call the production candidate builder.
- Test support `candidate_case_data() -> tuple[CanonicalRequest, dict]` creates the complete typed packet fixture before hashing. Implement the complete body below in this task so downstream direct capture and registered composition tests consume the same fixture without depending on later task text.

Create this fixture implementation in `runtime/tests/support_window_readiness.py`; it consumes existing `support_synthetic_provisioning.case_data() -> tuple[CanonicalRequest, dict]` and `cj(value) -> bytes`. These functions return fresh synthetic data and canonical JSON bytes respectively. All packet facts and S0 are set before the returned source is hashed or prepared.

```python
from hashlib import sha256
from proofkey.packet_contracts import PacketCatalogV1, PacketAccessSnapshotV1
from support_synthetic_provisioning import case_data, cj

def candidate_case_data():
    request, source = case_data()
    catalog = dict(version='packet-catalog-v1', case_id=request.case_id,
        object_id=request.object_id, complete=True, revision='v1',
        relevant_set_id='j05-empty-artifacts', originals=[], extracts=[], restrictions=[])
    catalog = PacketCatalogV1.model_validate(catalog).model_dump(mode='json')
    access = dict(version='packet-access-v1', decision_id='j05-operator-access', revision='v1',
        case_id=request.case_id, object_id=request.object_id, sender=request.principal_id,
        recipient='J06-OPERATOR', role='operator', purpose='operator_packet',
        catalog_hash=sha256(cj(catalog)).hexdigest(), permitted_originals=[], permitted_extracts=[],
        issued_at='2026-10-08T10:00:00Z', expires_at='2026-10-08T12:00:00Z', metadata_restrictions=[])
    access = PacketAccessSnapshotV1.model_validate(access).model_dump(mode='json')
    for key, value in (('operator.packet_catalog', catalog), ('operator.packet_access', access)):
        source['facts'][key] = dict(value=value, revision='v1', case_id=request.case_id,
            object_id=request.object_id, evidence_ref='synthetic-j05:' + key)
    source['facts']['scheduling.slot']['value'] = 'S0'
    if len(cj(source)) > 1048576:
        raise ValueError('candidate_fixture_limit')
    return request, source
```

- [x] **Step 1: Write the exact profile/resource red.** Put `expected_candidate()` below in `runtime/tests/support_window_readiness.py` and import it into `test_window_readiness_registration.py`, which owns ProfileDeltaTests. The function already recomputes each process hash, bundle hash and profile hash; no additional rehash helper is required. This test helper is not imported by production.

```python
def expected_candidate():
    data = load_profile('flat-v1.3').model_dump(mode='json')
    data['profile_id'] = 'flat-window-readiness-v1'
    cap = data['capabilities']['reschedule']
    cap['version'] = 'synthetic-scheduling-dual-v1'
    cap['acknowledgement']['basis'] = 'synthetic-scheduling-dual-v1: window v2 envelope ack only; exact v1 typed ack'
    cap['readback']['basis'] = 'synthetic-scheduling-dual-v1: bounded original scheduling receipt; out-of-domain unavailable'
    for name in ('acknowledgement', 'readback'):
        cap[name]['evidence_ref'] = 'synthetic-scheduling-envelope-v1'
    process = data['processes']['reschedule_window']
    process['process_id'] = 'reschedule-window-readiness-v2'
    process['version'] = 'v2-window-readiness'
    process['phases'].insert(process['phases'].index('window_gate'), 'window_readiness')
    edge = next(e for e in process['edges'] if e['origin'] == 'read_authority' and e['operation'] == 'check_window')
    edge['target'] = 'window_readiness'
    process['edges'].extend([
        {'origin': 'window_readiness', 'operation': 'read_authority', 'target': 'window_gate', 'condition': None},
        {'origin': 'window_readiness', 'operation': 'request_stop', 'target': 'stop', 'condition': None},
        {'origin': 'window_readiness', 'operation': 'ask_operator', 'target': 'wait_operator', 'condition': None},
    ])
    process['prerequisites'].append({'phase': 'window_gate', 'authority': 'scheduling', 'fact': 'slot', 'expected': 'S0'})
    process['acknowledgements']['reschedule'] = dict(cap['acknowledgement'])
    process['readbacks']['reschedule'] = dict(cap['readback'])
    for item in data['processes'].values():
        item['release_hash'] = fingerprint({k: v for k, v in item.items() if k != 'release_hash'})
    data['process_hash'] = fingerprint(data['processes'])
    data['release_hash'] = fingerprint({k: v for k, v in data.items() if k != 'release_hash'})
    return EnvironmentProfile.model_validate(data)

class ProfileDeltaTests(unittest.TestCase):
    def test_exact_candidate_and_only_two_affected_contracts(self):
        baseline = load_profile('flat-v1.3')
        candidate = load_profile('flat-window-readiness-v1')
        self.assertEqual(candidate, expected_candidate())
        self.assertEqual(_affected(baseline, candidate),
            ['capability:reschedule:v1.1', 'process:reschedule_window:v1'])
        self.assertEqual(candidate.processes['reschedule_exact'], baseline.processes['reschedule_exact'])
```

`ProcessEdge` has origin, target, optional operation and optional condition; the snippet explicitly preserves the null condition in canonical edge bytes. No new edge model is required.

- [x] **Step 2: Run red.** `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_registration.ProfileDeltaTests -v`. Expect absent candidate, then exact-delta mismatch until the resource and matcher exist.
- [x] **Step 3: Implement profile, resource and literal inventory.** Production builder performs the explicit operations above, requiring the exact baseline first; the independent test oracle remains separate. Serialize both new JSON files identically with a final newline. Add only `resources/profiles/flat-window-readiness-v1.json` to each explicit package list. Record file SHA-256 separately from semantic profile release_hash; these are different values. Add the candidate to the trusted loader names. Extend resource tests to eleven profiles and retain the ten literal historical hashes, two fixture hashes and schema hash.

Implement the pure full-ID helper in this task and test it against an independently spelled explicit dictionary; the world and capture integration belongs to Task 2. Use a local alias `from .identity import fingerprint as hash_fields` so the stored-field argument named fingerprint does not shadow the hash function. Require `type(value) is str`, value nonempty with at least one non-whitespace character, and `re.fullmatch('[0-9a-f]{64}', value)` for both digests before hashing. No source hashes belong in this helper or anywhere inside the 86-file closure.

Write the independent J05 tuple literally in `profiles.py`, with exactly these names in this order (do not reference stop-v2's constant or evaluate a glob in production):

```python
WINDOW_READINESS_IMPLEMENTATION_PATHS = (
    '__init__.py', 'adapters/__init__.py', 'adapters/case.py', 'adapters/delivery.py',
    'adapters/messaging.py', 'adapters/operator.py', 'adapters/ownership.py', 'adapters/returns.py',
    'adapters/scheduling.py', 'adapters/world.py', 'admission.py', 'admission_routes.py', 'api.py',
    'assessment/__init__.py', 'assessment/audit.py', 'assessment/cache.py', 'assessment/contracts.py',
    'assessment/coverage.py', 'assessment/drills.py', 'assessment/driver_contracts.py', 'assessment/drivers.py',
    'assessment/isolation.py', 'assessment/labels.py', 'assessment/ledger.py', 'assessment/readiness.py',
    'batch.py', 'batch_files.py', 'bootstrap.py', 'budget.py', 'cli.py', 'clock.py', 'contracts.py', 'engine.py',
    'evidence/__init__.py', 'evidence/catalog.py', 'evidence/intake.py', 'evidence/processing_contracts.py',
    'evidence/redaction.py', 'execution.py', 'execution_consumer.py', 'execution_trace.py', 'exporter.py',
    'factory/__init__.py', 'factory/proposal.py', 'factory/release.py', 'factory/views.py', 'gateway.py',
    'host.py', 'host_admission.py', 'host_contracts.py', 'host_files.py', 'host_writer.py', 'identity.py',
    'journal.py', 'ownership.py', 'ownership_contracts.py', 'ownership_gateway.py', 'ownership_store.py',
    'packet_contracts.py', 'packets.py', 'planner.py', 'policy.py', 'ports.py', 'process.py', 'processing.py',
    'processing_orchestration.py', 'processing_summary.py', 'profiles.py', 'providers/__init__.py',
    'providers/anthropic.py', 'providers/elevenlabs.py', 'providers/invocations.py', 'providers/protocols.py',
    'providers/replay.py', 'providers/unavailable.py', 'registered_releases.py', 'release.py', 'replay.py',
    'retained_state.py', 'schema.sql', 'source_retained_state.py', 'synthetic_provisioning.py', 'trace.py',
    'verifier.py', 'wait_contracts.py', 'waits.py',
)
```

- [x] **Step 4: Write registration/reconstruction red tests.** Build structurally valid unit material with 86 explicit path/nonempty-byte pairs; label it non-executing unit material. Such bytes must never produce a behavioral qualification receipt. Construct registration hashes independently from those bytes for matcher unit tests only. Test exact type/subclass rejection, every field's type/hash, unsorted/duplicate/list/alias/missing/extra paths, empty bytes, per-file 1048576/1048577 and aggregate 8388608/8388609 limits, simultaneous legacy/new registration rejection before malformed JSON is decoded, unrelated material rejection, and caller mutation after construction. For final executed qualification Task 5 uses independently fixed hashes, never hashes chosen by submitted bytes.

```python
def test_all_reconstruction_paths_use_the_retained_registration(self):
    factory = AdaptationFactory(window_context(self.mat, self.registration))
    retained = factory.context.process_delta_registration
    self.assertIsNot(retained, self.registration)
    proposal = factory.prepare_proposal(self.mat.source, load_profile('flat-v1.3'), self.mat.agent)
    self.assertEqual(factory._resolve(proposal)[1], proposal)
    self.assertEqual(factory._proposal_hash(proposal.proposal_hash), proposal)
    body = factory._resolve(proposal)[4]
    commitment = body['process_delta_registration']
    self.assertEqual(set(commitment), {'registration_id', 'provenance', 'host_factory_key',
        'baseline_hash', 'candidate_hash', 'process_hash', 'policy_hash',
        'inventory_sha256', 'registration_sha256'})
    self.assertNotIn('implementation_registration', body)
    without_self = {k: v for k, v in commitment.items() if k != 'registration_sha256'}
    self.assertEqual(commitment['registration_sha256'], sha256(canonical(without_self)).hexdigest())
```

Use a fully passing bound regression/review fixture to compare the staged manifest's exact object with `commitment`, then mutate each binding/receipt field and require denial. Do not equate fabricated unit receipts with execution. Preserve and rerun the literal legacy serialization-vector tests. Include a rejected alternate registration ID: the J05 ID is fixed; the broader existing legacy ID-binding test remains the positive demonstration that different allowed IDs produce different proposal hashes.

- [x] **Step 5: Implement exact detachment and binding.** Reject coexistence at the start of `AdaptationFactory.__init__`, before normalizing any material. Rebuild the registration object and tuple pairs with exact type tests; reject unsorted input instead of sorting it into acceptance. Enforce source limits before decoding/copying and retain immutable bytes. `_material_proposal` selects one matcher/mode and rejects mixed material. Pass the retained new registration explicitly in constructor validation, `_resolve`, `_proposal_hash`, and `prepare_proposal`.

```python
def _window_registration_commitment(registration):
    inventory = [{'path': path, 'sha256': digest} for path, digest in registration.implementations]
    body = {name: getattr(registration, name) for name in (
        'registration_id', 'provenance', 'host_factory_key', 'baseline_hash',
        'candidate_hash', 'process_hash', 'policy_hash')}
    body['inventory_sha256'] = sha256(canonical(inventory)).hexdigest()
    body['registration_sha256'] = sha256(canonical(body)).hexdigest()
    return body
```

Retain independent sorted `adapter_sources` in the proposal body. Exact semantic validation compares all candidate data to the expected candidate, so one altered sibling/hash cannot pass. In `check_proposal`, allow the sole v2 process only for the exact retained registration and exact candidate after all existing receipt coverage/provenance/binding checks pass; leave other non-v1 denial intact. Stage only the reconstructed commitment. Remove `changed_process_adapter_dispatch_unavailable` from the new exact qualified mode only; preserve the remaining unmet requirements and every legacy mode's bytes/status.

- [x] **Step 6: Green and independent task review.** Run `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_registration test_installed_resources test_factory_registration.FactoryRegistrationTests.test_legacy_serialization_matches_prechange_literal_vectors -v`. Do not run the complete old factory modules as an intermediate green requirement. Their certain current-byte/old-pin mismatch is resolved explicitly in Task 5, with no per-task repin. Review resource bytes, all registration call sites and semantic mutants. Deliverable is an independently reviewable exact profile/registration contract, not a runnable v3 workflow or final source freeze. Controller commits only the approved Task 1 files during later authorized execution.

### Task 2: Actual raw source bytes, strict decoder and original proofs

**Files:**

- Modify: `runtime/src/proofkey/adapters/world.py`, `runtime/src/proofkey/adapters/scheduling.py`, `runtime/src/proofkey/source_retained_state.py`.
- Create: `runtime/tests/test_window_readiness_envelopes.py`.
- Modify only to add owned shared test helpers: `runtime/tests/support_window_readiness.py`.
- Read-only dependencies: `runtime/src/proofkey/profiles.py`, `runtime/tests/support.py`, `runtime/tests/support_synthetic_provisioning.py`.

Anchors: `world.py:358` dispatch, `:474` operation application, `:597` observations and `:612` reads; `source_retained_state.py:257-266` validates stored provider IDs for both outcome tables; the complete current `scheduling.py` is 18 lines.

**Interfaces consumed:** From `proofkey.profiles`: `is_window_readiness_profile(profile: EnvironmentProfile) -> bool`; `supports_process_operation(profile: EnvironmentProfile, process_version: str, operation: str, consent_mode: object) -> bool`; `_window_original_request_id(*, account_id: str, provider_key: str, case_id: str, object_id: str, operation: str, generation: str, action_id: str, fingerprint: str, identity_hash: str) -> str`. The latter validates exact identifiers, reschedule operation and lowercase 64-hex hashes and produces the fixed full-digest window namespace. From `support_window_readiness`: `candidate_case_data() -> tuple[CanonicalRequest, dict]` returns complete typed packet source plus S0 before hashing. Existing `ReadRequest`, `ReadTarget`, `EffectIntent`, `AuthorityReadback`, `AuthorityObservation`, `NonexecutionProof`, `DispatchResult` are unchanged. `SchedulingAdapter(world)` exposes `list_permitted_slots(request: ReadRequest) -> AuthorityReadback`, `read_schedule(request: ReadRequest) -> AuthorityReadback`, and `reschedule(intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult`. `SimulatedWorld(path, fixture, *, profile=None, clock=None, fixture_bytes=None)` remains the source constructor.

**New private interfaces produced:**

- `world._dispatch_data(operation: str, intent: EffectIntent, *, deadline: datetime | None = None, auth: AuthContext | None = None, window_envelope: bool = False) -> dict` and `_read_data(operation: str, request: ReadRequest, *, window_envelope: bool = False) -> dict` return source dictionaries before any public output-model construction.
- `world._dispatch_scheduling_raw(intent: EffectIntent, *, deadline: datetime | None = None) -> bytes` and `_read_scheduling_raw(operation: str, request: ReadRequest) -> bytes` wrap those private data dictionaries in the exact raw outer schema. Only the candidate adapter calls them. No external callback argument is added.
- `world._effect_observation_data(connection, intent: EffectIntent, values: dict) -> list[dict]` supplies source dictionaries; keep `_effect_observations(...) -> list[AuthorityObservation]` as its typed wrapper where existing callers need it.
- World intent/row adapters call Task 1's pure `profiles._window_original_request_id` with all nine exact fields. `source_retained_state` imports that same pure helper only from profiles; the new ID path must introduce no world import or import cycle. Preserve the existing function-local world import used by material-key/revision validation; moving it is outside this change. No second request-ID formula is introduced.
- `scheduling._SchedulingEnvelopeError(ValueError)` with fixed message `synthetic_envelope_unavailable`; `_decode_scheduling_read(raw: bytes, operation: str) -> AuthorityReadback`; `_decode_scheduling_dispatch(raw: bytes) -> DispatchResult`; `_decode_envelope(raw: bytes, operation: str) -> dict` is the shared complete-envelope validator.

- [x] **Step 1: Write raw/normalized/source-row red tests.** Test support uses `build_test_runtime(folder, profile_name='flat-window-readiness-v1')`, existing `make_intent` with profile_version `v1.3`, process_version `v2-window-readiness`, `expected_revisions=world.material_revisions()`, owner revision `v1`, epoch `0`, slot `S1` and postcondition `{'slot': 'S1'}`. `original_request(intent, purpose='reconcile') -> ReadRequest` uses C1/O1/U1/synthetic-proof and all five target fields from that intent, with `deadline=intent.deadline`. Each case owns a fresh SQLite root.

```python
def original_request(intent, purpose='reconcile'):
    return ReadRequest(case_id=intent.binding.case_id, object_id=intent.binding.object_id,
        caller_id='U1', proof_reference='synthetic-proof', purpose=purpose, deadline=intent.deadline,
        target=ReadTarget(kind='original_effect', operation=intent.operation,
            generation=intent.binding.generation, action_id=intent.action_id,
            provider_key=intent.provider_key, fingerprint=intent.argument_fingerprint))

def fresh_intent(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    fx = build_test_runtime(temporary.name, profile_name='flat-window-readiness-v1')
    self.addCleanup(fx.store.close)
    intent = make_intent(profile_version='v1.3', process_version='v2-window-readiness',
        expected_revisions=fx.world.material_revisions(), ownership_state_revision='v1',
        ownership_epoch=0, arguments={'slot': 'S1'}, postcondition={'slot': 'S1'})
    return fx, intent

def test_http200_business_failure_is_not_terminal(self):
    fx, intent = self.fresh_intent()
    fx.world.set_fault('reschedule', 'http200_business_failed')
    raw = fx.world._dispatch_scheduling_raw(intent)
    decoded = json.loads(raw)
    self.assertEqual((decoded['http_status'], decoded['body']['status']), (200, 'business_failed'))
    normalized = _decode_scheduling_dispatch(raw)
    self.assertEqual((normalized.status, normalized.provider_request_id,
                      list(normalized.evidence_refs), normalized.reason),
                     ('outcome_unknown', None, [], 'synthetic_envelope_unresolved'))
    self.assertEqual(fx.world.effect_count('reschedule'), 0)
    with fx.world._connect() as connection:
        self.assertEqual(connection.execute('SELECT count(*) FROM final_rejections').fetchone()[0], 0)
    reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
    self.assertEqual(verify(intent, reply, profile=fx.profile).status, 'outcome_unknown')
```

Repeat for success, timeout-before/after, business_rejection and final_rejection_unknown. Verify raw bytes are not produced by a call to `_dispatch` or `_read`: patch those typed methods to raise during raw calls. Patch `_dispatch_scheduling_raw`/`_read_scheduling_raw` to record route selection: all candidate reads and candidate window writes use raw; candidate exact writes and all legacy scheduling calls use typed.

- [x] **Step 2: Write complete decoder boundary red tests.** Use this source-independent valid read envelope builder in the test module:

```python
def read_envelope(value='S0', *, reference='e', body_refs=None):
    stamp = '2026-10-08T10:00:00+00:00'
    return {'contract': 'synthetic-scheduling-envelope-v1', 'http_status': 200,
        'operation': 'list_permitted_slots', 'body': {
            'operation': 'list_permitted_slots', 'object_id': 'O1',
            'observations': [{'authority': 'scheduling', 'fact': 'slot', 'object_id': 'O1',
                'value': value, 'revision': 'v1', 'provider_at': stamp,
                'observed_at': stamp, 'evidence_ref': reference}],
            'provider_request_id': None, 'action_id': None, 'fingerprint': None,
            'stage': 'observed', 'nonexecution': {'status': 'unknown', 'basis': None, 'evidence_ref': None},
            'as_of': stamp, 'evidence_refs': ['body-e'] if body_refs is None else body_refs}}

def raw(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')

def test_conjunctive_limits_and_repeated_evidence(self):
    good = read_envelope(body_refs=['same'] * 127)  # one observation + 127 body occurrences
    self.assertEqual(len(_decode_scheduling_read(raw(good), 'list_permitted_slots').evidence_refs), 127)
    good['body']['evidence_refs'].append('same')
    with self.assertRaises(_SchedulingEnvelopeError):
        _decode_scheduling_read(raw(good), 'list_permitted_slots')
    encoded = raw(read_envelope())
    _decode_scheduling_read(encoded + b' ' * (262144 - len(encoded)), 'list_permitted_slots')
    with self.assertRaises(_SchedulingEnvelopeError):
        _decode_scheduling_read(encoded + b' ' * (262145 - len(encoded)), 'list_permitted_slots')
```

Add depth-16/17 values by wrapping the observation value in 12/13 nested lists: envelope root=1, body=2, observations=3, observation=4, first value list=5. Add observations=128 with body_refs=[] to isolate acceptance at the decoder layer (not gateway qualification); 129 necessarily also violates evidence occurrences and the test/report must say so. Test 1024/1025 Unicode code points and multibyte UTF-8 independently of the byte limit. For duplicate tests splice a duplicate key into raw bytes at outer/body/observation/nonexecution levels; dict builders cannot represent duplicates. Mutate every required key to missing, add unknown keys at every schema level, and test invalid UTF-8, trailing JSON, NaN/Infinity, boolean/string HTTP status, arrays/objects in scalar fields, numeric timestamps, naive ISO timestamps, unknown contract and wrong outer operation. Test source-owned body operation `reschedule` under outer `read_schedule`. One bound passing never exempts another bound.

- [x] **Step 3: Run decoder/source reds.** `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_envelopes -v`.
- [x] **Step 4: Factor source data, provider compatibility/S0 and strict decoding.** Move the existing dispatch/read transaction bodies into `_dispatch_data`/`_read_data`. Mechanically replace each output constructor with an explicit dictionary containing every field, including nulls, preserving `_call`, reservation, BEGIN mode, all returns/finally-release and final deadline checks. Typed wrappers construct the original public model once; raw wrappers serialize dictionaries directly with ISO timestamps and `allow_nan=False`. Convert stored/effect observations through source dictionaries; do not normalize them into public models before raw serialization. Replace `_apply_declared_operation`'s blanket `intent.process_version != 'v1'` test with the complete Task 1 compatibility helper. In this same task, before any new candidate window effect or terminal insertion, require strict source scheduling.slot='S0' beside the existing material CAS. Same-key original reuse precedes new-write S0 enforcement. Validate candidate process/operation/current source consent before minting its namespace. There must be no intermediate accepted v2 provider without this S0 gate. Test direct valid-v2 success, exact-slot/window consent swaps, unsupported goods/service v2, stale revisions and fresh-revision non-S0 denial here. The raw fault is accepted by `set_fault` only as a trusted driver scenario; on the raw window path it returns HTTP200/business_failed before any insertion. Legacy paths keep their existing behavior.

Decoder algorithm, in this order: require exact nonempty bytes and length <=262144; strict UTF-8 decode; scan characters with quoted-string/escape state to reject container depth >16 before recursive JSON decode; `json.loads` with duplicate-key hook and rejecting `parse_constant`; require exact top-level keys and exact int status in {200,429,503}; check contract and outer operation; require exact body/nested key sets, exact list/dict types and all scalar bounds; count evidence occurrences without deduplication; validate complete body with strict existing public models only after the raw checks. `Identifier` means nonempty with at least one non-whitespace character, `Hash` lowercase 64 hex, `Revision` the same strict string domain; use the existing `Timestamp` semantics for aware ISO strings, never numeric coercion. Arbitrary observation `value` remains finite JSON within byte/depth limits; do not apply identifier length to arbitrary JSON strings. Rejecting unknown keys applies to schema objects, not arbitrary keys inside JsonValue.

```python
def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise _SchedulingEnvelopeError('synthetic_envelope_unavailable')
        result[key] = value
    return result

def _evidence_count(body):
    return (len(body['evidence_refs']) + len(body.get('observations', []))
            + int(body.get('nonexecution', {}).get('evidence_ref') is not None))

def _unresolved_dispatch():
    return DispatchResult(status='outcome_unknown', provider_request_id=None,
                          evidence_refs=[], reason='synthetic_envelope_unresolved')
```

`_decode_scheduling_dispatch` catches parsing/validation failure and returns `_unresolved_dispatch`; successful normalization additionally requires HTTP200, acknowledged, nonempty provider ID and nonempty evidence. The adapter catches raw-method exceptions with the same dispatch result. Reads reject all non-200 or invalid bodies with the single bounded error; adapter exceptions are mapped to that error without raw payload in its public message. Raw test evidence retains bytes separately. Do not silently replace bad fields with expected request identities.

- [x] **Step 5: Write original identity/idempotency red tests.** Use each row's eight-field full join independently. For every `account_id`, `case_id`, `object_id`, `operation`, `generation`, `action_id`, `provider_key`, `fingerprint`, alter only the source row in a fresh test and require no proof. Separately corrupt request namespace, digest tail, 64-hex identity_hash, created_at type/naivety/future; add an effect plus terminal row and duplicate full-join rows using only legal existing schema shapes. If the schema prevents a physical duplicate, demonstrate the existing constraint and test the classifier with a test-only query-result seam; do not change schema. Revoke reader ACL and inject early read faults; purpose changes must not change the result. Same-key same-intent reuses stored ID/count; same key different complete intent is conflict. Patch the private ID hash seam to force a collision across each table and verify insertion denial.

```python
def test_window_terminal_is_joined_without_legacy_knob(self):
    fx, intent = self.fresh_intent()
    fx.world.set_fault('reschedule', 'final_rejection_unknown')
    dispatch = fx.world.bundle().scheduling.reschedule(intent)
    self.assertEqual(dispatch.status, 'outcome_unknown')
    reply = fx.world.bundle().scheduling.read_schedule(original_request(intent))
    self.assertEqual(reply.nonexecution.status, 'proven')
    self.assertTrue(reply.provider_request_id.startswith('provider:window-envelope-v1:'))
    self.assertEqual(verify(intent, reply, profile=fx.profile).status, 'rejected')
```

For baseline and candidate exact-slot final_rejection_unknown, no knob stays unknown; terminal_not_executed exposes proof. Candidate window never requires that knob. Test raw bounds on the proof too.

- [x] **Step 6: Implement source-owned original proofs.** After existing identity checks, validate exact candidate process/operation/source consent through Task 1 helper. Preserve same-key handling before new insertion; also validate an existing window row's full namespace/digest before reusing it. For terminal same-key rows retain the stored ID in private data while public candidate dispatch remains unknown. Derive a new window ID from this exact source data:

```python
payload = dict(domain='synthetic-window-original-v1', account_id=account,
    provider_key=intent.provider_key, case_id=intent.binding.case_id,
    object_id=intent.binding.object_id, operation=intent.operation,
    generation=intent.binding.generation, action_id=intent.action_id,
    fingerprint=intent.argument_fingerprint, identity_hash=identity_hash)
request_id = _window_original_request_id(**{key: value for key, value in payload.items() if key != 'domain'})
```

Inside the same immediate transaction, query both tables by exact request_id and reject any conflicting join fields or identity hash before either insertion. Keep legacy/exact IDs `provider:` plus the first 24 digest characters over account/provider_key. Original read preserves reservation/deadline/ACL and early faults, then queries **both** tables using `account_id=? AND case_id=? AND object_id=? AND operation=? AND generation=? AND action_id=? AND provider_key=? AND fingerprint=?`. Build params from provider account, request case/object and original target. For automatic window rejection require zero effects, exactly one terminal, supported terminal contract, strict stored fields and exact recomputation through the shared pure helper, aware created_at <= read time, and final deadline still live. Inconsistent rows yield unknown. Non-window rows retain terminal_not_executed behavior. Never inspect current consent/slot to classify a saved original.

- [x] **Step 7: Implement retained-source full-ID validation and direct capture reds.** In source_retained_state's existing outcomes loop, after strict stored identifier/hash/timestamp validation, choose the full-ID formula only when `is_window_readiness_profile(profile)`, row operation is reschedule and the stored ID starts with the exact `provider:window-envelope-v1:` discriminator. Recompute using the nine exact row fields and require complete equality. Every other row must match the old 24-hex rule. A malformed/partial namespace, altered digest, cross-original field or unexpected operation therefore fails both accepted rules. Keep all existing schema, row uniqueness, material completeness, observation and capture-deadline checks. Do not use current slot/consent, a latest row or the namespace alone as proof.

```python
fields = ('account_id', 'provider_key', 'case_id', 'object_id', 'operation',
          'generation', 'action_id', 'fingerprint', 'identity_hash')
if (is_window_readiness_profile(profile) and row['operation'] == 'reschedule'
        and row['request_id'].startswith('provider:window-envelope-v1:')):
    expected_request_id = _window_original_request_id(**{key: row[key] for key in fields})
else:
    expected_request_id = 'provider:' + fingerprint({
        'account': row['account_id'], 'provider_key': row['provider_key']})[:24]
if row['request_id'] != expected_request_id:
    raise ValueError('invalid')
```

For direct capture tests import `support_window_readiness.candidate_case_data() -> tuple[CanonicalRequest, dict]`, which already returns S0 and the typed matching packet catalog/access envelopes before hashing, and `support_synthetic_provisioning.cj(value) -> bytes` and `context(clock, seconds=5) -> ExecutionContext`. Build SimulatedWorld with a SyntheticReplayClock and those fixture bytes, derive a direct intent matching its request/source, dispatch once, then call the existing `world.capture_retained_state(execution=context(clock), clock=clock)`. Verify new window effect and terminal capture, exact-slot and legacy capture. Corrupt each join field, digest, identity_hash and namespace in fresh source databases and assert `SourceRetainedStateFailure` while before/after rows stay identical to the corrupted input; capture must not repair or remove an already committed effect. Source capture is local evidence validation, not authentication or a substitute for the original-read join.

- [x] **Step 8: Direct-adapter preservation/domain green and review.** `test_direct_committed_effect_survives_unreadable_original` calls the real adapter to commit one effect, substitutes malformed/1025-character original raw readback, and asserts unchanged full stored row/key/identity plus no second adapter dispatch. It does not claim journal-debt preservation, which belongs to Task 3. `test_direct_legacy_reference_domain_contrast` reads the trusted scheduling.slot fact through baseline/candidate adapters after setting evidence_ref to 1024/1025; baseline accepts both and candidate denies only 1025. Candidate exact-slot dispatch stays typed. No new Task 2 test invokes the candidate engine; the readiness branch does not exist yet. Run `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_envelopes test_engine_profile_contracts test_gateway test_workflows test_factory_registration.FactoryRegistrationTests.test_legacy_serialization_matches_prechange_literal_vectors -v`. Independently review source-row/normalization separation, retained capture and legacy timing/idempotency before a controller-owned scoped commit.

### Task 3: Four-read engine branch and fresh core fences

**Files:**

- Modify: `runtime/src/proofkey/gateway.py`, `runtime/src/proofkey/engine.py`, `runtime/src/proofkey/policy.py`.
- Create: `runtime/tests/test_window_readiness_engine.py`.
- Read-only dependencies: `runtime/src/proofkey/profiles.py`, `runtime/src/proofkey/adapters/world.py`, `runtime/src/proofkey/adapters/scheduling.py`, `runtime/tests/support.py`, `runtime/tests/support_window_readiness.py`.

Anchors: `gateway.py:258`, `:470`, `:490`, `:578`; `engine.py:412`, `:615`; `policy.py:183`. The provider compatibility and S0 CAS are complete inputs, not writes by this task.

**Interfaces consumed:** `proofkey.profiles.is_window_readiness_profile(profile: EnvironmentProfile) -> bool` selects only the exact candidate. Existing scheduling methods are `list_permitted_slots(request: ReadRequest) -> AuthorityReadback`, `read_schedule(request: ReadRequest) -> AuthorityReadback`, `reschedule(intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult`; source substitution seam is `SimulatedWorld._read_scheduling_raw(operation: str, request: ReadRequest) -> bytes`. Provider compatibility/S0/CAS already operates behind these methods. Existing gateway helpers are `_active(case_id, binding=None, intent=None) -> PhaseCheckpoint`, `_configured_original(binding) -> tuple[PhaseCheckpoint, CanonicalRequest]`, `_source_validators(binding, checkpoint, *, recipient_key=None, packet=False) -> dict`, `_facts(scope, fields, *, attempt_id=None, deadline=None, purpose=None, validators=None) -> tuple[AuthorityObservation, ...]`. `qualified_observations(profile, object_id, observations) -> dict` indexes qualified facts. Engine `_save(checkpoint, **changes) -> PhaseCheckpoint`, `_transition(checkpoint, request, operation, *, facts=None) -> PhaseCheckpoint` and `RegisteredAdmissionOwner.guard_execution(execution, gateway, *, entry_kind=None)` are existing interfaces. Test fixture `support.build_test_runtime(folder, before_commit=None, *, request=None, profile_name='flat-v1.2') -> RuntimeFixture` supplies engine/store/world/clock/profile/auth/request; use profile_name='flat-window-readiness-v1'.

**New interfaces produced:** `ActionGateway.read_window_readiness(case_id: str) -> tuple[AuthorityObservation, ...]`; private `_window_readiness_checkpoint(case_id: str, expected: PhaseCheckpoint | None = None) -> PhaseCheckpoint` validates timing/execution/current state and never writes; `WorkflowEngine._window_readiness(checkpoint: PhaseCheckpoint, request: CanonicalRequest) -> PhaseCheckpoint` owns the finite branch and save; `WorkflowEngine._save_window_readiness(expected: PhaseCheckpoint, **changes) -> PhaseCheckpoint` compares original fences and saves inside the existing nested-capable `CaseStore._transaction()`. Import existing AuthorityObservation to annotate the gateway result; do not add a contract model.

- [x] **Step 1: Write positive and ownership red tests.** Use existing `build_test_runtime(..., profile_name='flat-window-readiness-v1')`. For isolated helper tests, admit an original with existing `store.admit(binding, request, checkpoint)` using `make_checkpoint` at phase `window_readiness`, next_gate `read_authority`, profile v1.3, process v2-window-readiness, ownership accepted/v1/0, then call within `gateway.execution_scope()` and `_auth_scope(fx.auth)`; `gateway` is `fx.engine.gateway`.

```python
def ready_fixture(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    fx = build_test_runtime(temporary.name, profile_name='flat-window-readiness-v1')
    self.addCleanup(fx.store.close)
    binding = make_binding(fx.request)
    checkpoint = make_checkpoint(binding=binding, phase='window_readiness',
        next_gate='read_authority', profile_version='v1.3', process_version='v2-window-readiness',
        ownership_state='accepted', ownership_state_revision='v1', ownership_epoch=0)
    fx.store.admit(binding, fx.request, checkpoint)
    return fx

def test_exact_four_reads_and_original_state(self):
    fx = self.ready_fixture()
    before = fx.store.checkpoint('C1')
    with fx.engine.gateway.execution_scope(), fx.engine.gateway._auth_scope(fx.auth):
        observations = fx.engine.gateway.read_window_readiness('C1')
    after = fx.store.checkpoint('C1')
    self.assertEqual([(c.operation, c.purpose) for c in fx.world.calls], [
        ('read_case', 'window_readiness_identity'),
        ('read_principal', 'window_readiness_identity'),
        ('read_owner', 'window_readiness_identity'),
        ('list_permitted_slots', 'window_readiness')])
    self.assertEqual(len(observations), 10)
    self.assertEqual(after.budget.tool_calls - before.budget.tool_calls, 4)
    self.assertEqual((after.binding, after.deadline), (before.binding, before.deadline))
    self.assertEqual(fx.world.effect_count('reschedule'), 0)
```

`test_owner_validation_precedes_settlement` mutates ownership.owner to '', True, 1, None and 'OTHER' with matching epoch/revision and records calls to the real `_settle` via a wrapping spy. Assert the owner read settles with completed=False, three physical reads/debits are retained, scheduling is not called and no packet fact appears in targets. Control comparison with U1 passes. Mutate authorization/binding/generation/request revision/consent revision/state/state revision/epoch one at a time. Reject bool epoch despite `True == 1`. Test absent auth, wrong thread, no active timing, wrong original kind/profile/process/version/deadline/next_gate and v2 stop token entry without any physical readiness read.

- [x] **Step 2: Run red.** `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_engine -v`.
- [x] **Step 3: Implement the helper with source validators and rechecks.** `_window_readiness_checkpoint` requires creator thread, `_execution_active`, nonnull `_timing`, authenticated caller, `_active(case_id)`, `_configured_original`, exact candidate and original kind, bound profile/process/policy versions, phase/next gate, accepted ownership, no stop and original deadline. Use the inspected `ExecutionTiming.remaining_seconds(checkpoint.deadline) > 0`; that method intersects the case deadline with an active registered execution window. Compare every fence to `expected` before scheduling and after final read, but exclude budget and observations from equality so legitimate lease settlement is retained. Registered guard is called with exactly `self._admission_owner.guard_execution(self._timing.execution, self)`.

```python
checkpoint = self._window_readiness_checkpoint(case_id)
validators = self._source_validators(checkpoint.binding, checkpoint)
ordinary_owner = validators['ownership']
def strict_owner(reply):
    current = {o.authority + '.' + o.fact: o.value for o in reply.observations}
    for key, schema in (('ownership.owner', Identifier), ('ownership.state', OwnerState),
                        ('ownership.state_revision', Revision), ('ownership.epoch', NonnegativeInt)):
        TypeAdapter(schema).validate_python(current[key], strict=True)
    if current['ownership.owner'] != self.auth.caller_id:
        raise GateDenied('scope_denied')
    ordinary_owner(reply)
validators['ownership'] = strict_owner
identity = self._facts(checkpoint.binding, IDENTITY_FIELDS | OWNER_FIELDS,
    deadline=checkpoint.deadline, purpose='window_readiness_identity', validators=validators)
self._window_readiness_checkpoint(case_id, checkpoint)
slot = self._facts(checkpoint.binding, {'scheduling.slot'},
    deadline=checkpoint.deadline, purpose='window_readiness')
if len(slot) != 1 or type(slot[0].value) is not str or slot[0].value != 'S0':
    raise GateDenied('scope_denied')
self._window_readiness_checkpoint(case_id, checkpoint)
return identity + slot
```

No packet=True, added consent-mode/fingerprint/policy read, or caller-supplied facts/deadline. `_AUTHORITY_READS` already orders case/customer/ownership correctly when only those fields are requested. `_leased_read` retains all existing fresh-time, exact-fact-set and settlement checks.

- [x] **Step 4: Write races/save-failure red tests.** Wrap actual scheduling.list_permitted_slots so it first performs its physical read, then mutates one current fence: sticky stop, deadline expiration, binding generation, process/policy version, ownership state/revision/epoch, or next_gate. Test mutations before operation 4 and after it. Wrap store.save_checkpoint to fail only when the proposed phase is window_gate, and separately arm `CommitFault` immediately after readiness source read. Snapshot binding/deadline/intent count, budget debits and stop before/after. Assert phase never becomes window_gate on failure; no intent or handoff is invented; newer stop is not cleared. Do not use arbitrary exception swallowing to make failure appear successful.

- [x] **Step 5: Implement finite branch and latest-state save.** In `run_one_approved_phase`, handle exact phase window_readiness before generic `_LOCAL`. Save selection next_gate=read_authority first through `_save_window_readiness`, accepting the initial next_gate=window_readiness only for this selection. Call gateway helper, reread/fence the latest checkpoint, index existing and returned observations by qualified `authority.fact`, replace only the returned keys, and preserve all other fields from the latest checkpoint. Use `self.process.next_phase` over the newly merged facts, then save observations and the exact window_gate advancement together through `_save_window_readiness`. Return advancement only after that transaction commits. Catch gate/budget failures into unavailable only when a fresh load still names this readiness phase; save from that fresh object. Journal save failure must propagate without a later advancing save. Sticky stop returns the fresh stopped checkpoint. Never restore a captured pre-read budget.

```python
def _save_window_readiness(self, expected, **changes):
    fences = ('binding', 'phase', 'next_gate', 'profile_version', 'process_version',
        'policy_version', 'ownership_state', 'ownership_state_revision',
        'ownership_epoch', 'deadline', 'stop')
    with self.store._transaction():
        current = self.store.checkpoint(expected.binding.case_id)
        if any(getattr(current, key) != getattr(expected, key) for key in fences):
            raise GateDenied('scope_denied')
        if current.stop.requested or self.gateway._timing.remaining_seconds(current.deadline) <= 0:
            raise GateDenied('scope_denied')
        if self.gateway._admission_owner is not None:
            self.gateway._admission_owner.guard_execution(self.gateway._timing.execution, self.gateway)
        return self._save(current, **changes)
```

`CaseStore._transaction` already enforces creator thread and BEGIN IMMEDIATE, and explicitly supports nested transactions for atomic host operations. `save_checkpoint` already retains sticky stop and preserves budget but does not compare phase/ownership fences, so the new finite engine wrapper adds that comparison under its outer transaction. Inject concurrent-state changes before the outer transaction comparison, and inject a real before_commit failure to prove no advancement commits; two unlocked reads are insufficient. No journal interface or schema change is needed.

- [x] **Step 6: Write stale/direct-intent and full-path red tests.** A trusted callback moves source slot from S0 after readiness to another slot before full material reread; another does so after that reread but before dispatch; build a direct otherwise-valid candidate intent with current revisions while slot is not S0. All must have zero new reschedule effects. Positive original readback after reschedule to S1 must still verify without S0. Full positive test uses the unmodified engine and records every physical call and lease; require one verified effect, zero handoff, original deadline, tool_calls equal actual calls and <=24, active_seconds <=120, each physical deadline allowance <=10. Include admission calls in the registered Task 4 path. The static preflight in `j05-budget-preflight.md` predicts exactly 15 calls (3 admission + 4 readiness + 6 material + dispatch + original readback); it is not runtime evidence. The existing 10-call pre-positioned gateway test omits full process admission/readiness and cannot satisfy this witness.
- [x] **Step 7: Add fresh policy fence and real-engine preservation/domain tests.** In `PolicyGate.evaluate`, exact candidate window reschedule additionally requires fresh `values['scheduling.slot'] == 'S0'` with strict str, alongside the existing full source/policy/owner/consent checks. Consume Task 2's complete provider/CAS interface unchanged. In `test_committed_effect_survives_unreadable_original`, run the real candidate engine from a fresh case and substitute raw read failure only for original_effect after its real dispatch commits. Assert one effect, retained journal intent/provider key/debt and unknown original result with zero resend/undo. In `test_legacy_reference_domain_contrast`, run fresh complete baseline/candidate window and exact-slot workflows with 1024/1025 references; candidate out-of-domain pre-write has zero business calls/effects. These tests live only in test_window_readiness_engine. Run `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_engine test_gateway test_gateway_control test_workflows test_stop test_observed_stop_v2 test_factory_registration.FactoryRegistrationTests.test_legacy_serialization_matches_prechange_literal_vectors -v`. If the full path does not fit unchanged bounds, stop qualification with a fit blocker; do not increase limits, hide reads or declare the candidate complete. Independent reviewer checks before controller-owned scoped commit.

### Task 4: Closed composition and complete registered path

**Files:**

- Modify: `runtime/src/proofkey/host_admission.py`, `runtime/src/proofkey/synthetic_provisioning.py`, `runtime/src/proofkey/host.py`, `runtime/src/proofkey/profiles.py` (closed selected-profile validator only).
- Create: `runtime/tests/test_window_readiness_composition.py`.
- Modify: `runtime/tests/support_window_readiness.py` (registered wrapper only; consume its existing candidate_case_data).
- Read-only dependencies: `runtime/tests/support_synthetic_provisioning.py`, `runtime/tests/support_observed_stop_v2.py`, `runtime/tests/test_synthetic_provisioning_cli.py`, `runtime/tests/test_host_admission.py`.

Anchors: `host_admission.py:138` implementation paths, `:238` composition and `:901` guard; `synthetic_provisioning.py:219` initial input, `:557` prepared revalidation; `host.py:264` runtime construction. Keep v2 stop code and its tuple/all-package test unchanged.

**Interfaces consumed:** `proofkey.profiles.is_window_readiness_profile(profile: EnvironmentProfile) -> bool`; `WINDOW_READINESS_IMPLEMENTATION_PATHS: tuple[str, ...]` is the independently written 86-name literal; `load_profile('flat-window-readiness-v1') -> EnvironmentProfile` loads the reviewed exact candidate. Test source `support_window_readiness.candidate_case_data() -> tuple[CanonicalRequest, dict]` returns the complete typed packet catalog/access, matching identities and S0 before hashing; `support_synthetic_provisioning.cj(value) -> bytes` and `context(clock, seconds=5) -> ExecutionContext` are existing helpers. Existing production interfaces are `prepare_synthetic_release(spec, *, parent, clock, execution, factory_key='fixed-synthetic-v1') -> PreparedSyntheticReleaseV1`, `configure_registered_cli(prepared, *, approvals, review_id, auth_resolver, clock, execution, host_limits, interface_limits, total_seconds, publication_reserve_seconds, shutdown_seconds) -> CliConfiguration`, `RuntimeFactory.create_registered(release, clock, *, composition, execution) -> RuntimeResources` and `RuntimeResources.run_registered(request, auth, *, execution) -> CaseResult | SavedResult`. No new CLI override is introduced.

**New private interfaces produced:** `_profile_commitment(factory_key: str) -> tuple[str, str, str, str, str]` in synthetic_provisioning returns explicit `(resource_name, file_sha256, release_hash, process_hash, policy_hash)` for exactly v1/v2/v3; the v3 values are derived from reviewed candidate resource bytes then fixed. `_validate_selected_profile(factory_key: str, profile: EnvironmentProfile, request_kind: str | None = None) -> None` in profiles enforces exact selection/versions; both provisioning boundaries and host composition call it. `support_window_readiness.opened_candidate_case()` is a test-only context manager modeled on existing `support_observed_stop_v2.opened_case`, consuming the already complete candidate_case_data fixture and creating fresh roots.

The actual signature for `_validate_selected_profile` must include an explicit return contract of rejection by `ValueError` on unsupported selection; each boundary maps it into its existing safe error code. The v1/v2 branches require the fixed flat-v1.3 release/process/policy identity, not just family version. The v3 branch requires the full Task 1 exact candidate matcher and, when request_kind is supplied, `reschedule_window` only.

- [ ] **Step 1: Write closed initial/revalidation/composition red tests.** Consume the existing `support_window_readiness.candidate_case_data() -> tuple[CanonicalRequest, dict]`, which returns a complete source snapshot including typed empty packet catalog/matching access and scheduling.slot=S0, all set before hashing. Pass `cj(source)` to real SyntheticCaseReleaseSpecV1. Default v1/v2 tests continue using their original fixtures. Build fresh grant/composition using existing SyntheticReviewGrantV1 and LocalAdmissionCompositionV1. No post-preparation injection, source-capture relaxation or readiness packet read is allowed. Both library and CLI positive tests consume this identical helper. The new wrapper below is added to the same support module, so candidate_case_data is already locally defined; it is not reimplemented here.

```python
@contextmanager
def opened_candidate_case():
    with tempfile.TemporaryDirectory() as folder, paced_clock() as (clock, state):
        parent = Path(folder).resolve()
        parent.chmod(0o700)
        request, source = candidate_case_data()
        spec = SyntheticCaseReleaseSpecV1('J05-H', 'J05-L', 'J05-R', request, cj(source))
        prepared = prepare_synthetic_release(spec, parent=parent, clock=clock,
            execution=context(clock), factory_key='fixed-synthetic-window-readiness-v3')
        grant = SyntheticReviewGrantV1('j05-review', prepared.binding.artifact_hash,
            'j05-synthetic-reviewer', 'admit_fixed_local_replay', 'synthetic_rehearsal',
            clock.now(), clock.now() + timedelta(minutes=10))
        composition = LocalAdmissionCompositionV1(prepared.registry, prepared.binding,
            ProvisionedReviewResolverV1((grant,)), grant.review_id, prepared.control_parent)
        runtime = RuntimeFactory().create_registered(prepared.host_release, clock,
            composition=composition, execution=context(clock))
        try:
            yield SimpleNamespace(prepared=prepared, runtime=runtime, request=request,
                clock=clock, state=state, composition=composition,
                auth=AuthContext(caller_id=request.principal_id, proof_reference='j06-synthetic-proof'))
        finally:
            runtime.close()

def test_v3_preparation_and_run_are_explicit(self):
    with opened_candidate_case() as fx:
        self.assertEqual(fx.prepared.binding.host_factory_key, 'fixed-synthetic-window-readiness-v3')
        self.assertEqual(fx.runtime.profile.profile_id, 'flat-window-readiness-v1')
        result = fx.runtime.run_registered(fx.request, fx.auth, execution=context(fx.clock, seconds=120))
        self.assertEqual(result.effects['reschedule'].status, 'verified')
        self.assertEqual(fx.runtime.world.effect_count('reschedule'), 1)
        expected_calls = [
            ('read_case', 'bind_request'), ('read_principal', 'bind_request'), ('read_owner', 'bind_request'),
            ('read_case', 'window_readiness_identity'), ('read_principal', 'window_readiness_identity'),
            ('read_owner', 'window_readiness_identity'), ('list_permitted_slots', 'window_readiness'),
            ('read_case', 'material_authority'), ('read_principal', 'material_authority'),
            ('read_delivery', 'material_authority'), ('read_case', 'material_authority'),
            ('read_owner', 'material_authority'), ('list_permitted_slots', 'material_authority'),
            ('reschedule', 'dispatch'), ('read_schedule', 'reconcile_original')]
        self.assertEqual([(c.operation, c.purpose) for c in fx.runtime.world.calls], expected_calls)
        budget = fx.runtime.store.checkpoint(fx.request.case_id).budget
        self.assertEqual(budget.tool_calls, 15)
        self.assertLessEqual(budget.active_seconds, 120)
        self.assertEqual(fx.runtime.world.effect_count('enqueue_handoff'), 0)
```

`run_registered` returns the engine result through `RegisteredAdmissionOwner.run`; the source confirms its effects field is available on the fresh result. For both validation boundaries and host composition, swap key/profile/kind/version/resource hash/source pin and require denial. Test candidate exact-slot/goods preparation rejected while in-domain adapter-only exact comparison remains allowed. Test multiple registry releases, malformed path inventory, stale bytes and source aliases. Assert no child allocation for initial invalid input, and retained root/code `identity_changed` on prepared mutation.

For the exact witness, additionally wrap the real transport methods to record target authority, lease ID and deadline without skipping/delegating twice. Calls 8 and 11 above must remain separate case/policy authority leases even though both use read_case. Capture each lease's reserved and elapsed time and the host elapsed/remaining window separately: `15 < 24` does not prove timed fit, and `15 * 10` does not prove timeout because settlement refunds unused active reservations. Require three imported admission debits, four readiness debits, six fresh material debits, one dispatch and one original read, with no reset, retry, extra control read or pre-positioned phase. Fault/debt paths have separate denominators and may legitimately consume more calls.

After run_registered returns, use `runtime.admission.claim_for_case(case_id, execution=context(clock))` and `route_for_case` to assert finalized `admission_observed`, exact original binding/route identity, and the final source/journal hashes recorded in the claim. Capture the real source again and compare its content hash with the finalized claim under the unchanged source state; assert that the capture contains the window full-ID row. A verified engine result without successful final capture/route/claim is a failing registered witness. Capture/packet fixture checks add local work but no physical ports to the 15-call count.

- [ ] **Step 2: Run red, implement closed selection.** Run `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_window_readiness_composition -v`. Add v3 branch to `_implementation_paths` returning Task 1's literal tuple. `_profile_commitment` selects flat-v1.3 for v1/v2, candidate for v3, otherwise fails. Initial validation and revalidation compare the same exact file and semantic commitments; revalidation rereads the stored original request and enforces the v3 window kind too. Host composition preserves all source/resource/account/grant/writer/route checks and singleton registry, replacing only the blanket all-v1 version test with the exact candidate selector. No implicit key upgrade.
- [ ] **Step 3: Write/run control and CLI comparisons.** Exercise configured library and CLI run on fresh v3 roots using the existing trusted configuration pattern from `test_synthetic_provisioning_cli.py`. Test recovery/reply/stop/transfer via each existing registered entrypoint and deny v3; v1 remains run-only, and exact v2 current-owner stop continues passing its existing suite. Wrong auth/ACL must create zero unauthorized effects without removing legitimate admission/audit records. Independently review that no check uses `factory_key != v1` as a control grant. Run `test_window_readiness_composition test_synthetic_provisioning test_synthetic_provisioning_cli test_host_admission test_observed_stop_v2 test_observed_stop_v2_acceptance` with the fixed runner.

This task's independently reviewable result is closed v3 composition with complete registered finalization and intact v1/v2 controls. Its test-source snapshots are local integration evidence, not final J05 source qualification. No final source-pin fixture is generated here.

### Task 5: Explicit current/historical lanes, final freeze and source evidence

**Files:**

- Create: `runtime/tests/support_factory_lanes.py`, `runtime/tests/test_factory_current_v1.py`, `runtime/scripts/qualify_window_readiness.py`, `runtime/tests/test_window_readiness_evidence.py`, `runtime/tests/fixtures/window-readiness-current-registration-v1.json`.
- Modify: `runtime/tests/test_adaptation_factory.py`, `runtime/tests/test_factory_registration.py`, `runtime/tests/test_factory_qualification.py`, `runtime/scripts/qualify_factory.py`.
- Read-only dependencies: `runtime/tests/test_window_readiness_registration.py`, `runtime/tests/test_window_readiness_envelopes.py`, `runtime/tests/test_window_readiness_engine.py`, `runtime/tests/test_window_readiness_composition.py`, `runtime/tests/test_observed_stop_v2.py`, `runtime/tests/support_window_readiness.py`, all 86 package files named by the independent literal tuple.
- Create evidence only in a fresh `outputs/window-readiness-final-XXXXXXXX/` parent using the commands in this task.
- Update after final review: `openspec/changes/window-readiness-adaptation/tasks.md`; create `openspec/changes/window-readiness-adaptation/review.md`; archive this child through the repository OpenSpec workflow into its dated archive directory and update only its four named living capabilities.
- Preserve unchanged: `runtime/tests/fixtures/factory-current-registration-v1.json`, `runtime/tests/fixtures/factory-legacy-vectors-v1.json`, `runtime/src/proofkey/factory/proposal.py`'s `REGISTERED_IMPLEMENTATIONS`, stop-v2 literal inventory and all historical receipts.

This task owns the necessary test/helper and outer qualifier migration before the final full-discovery gate. All package edits precede its final freeze; no per-task repinning.

**Interfaces produced:**

- In new test-only `support_factory_lanes.py`: `current_v1_registration() -> SyntheticImplementationRegistration` loads only the fixed `runtime/tests/fixtures/window-readiness-current-registration-v1.json`, checks its J05 identity and 86-name inventory, selects the six exact legacy path names from those already frozen entries, and returns registration ID `synthetic-factory-j05-current-v1` with provenance `local_controlled_synthetic`. It accepts no path, bytes, inventory or callback argument. It does not hash submitted material to select expected pins.
- In that support file: `current_v1_context(material: ProposalMaterial, *, registration: SyntheticImplementationRegistration, regressions=(), reviews=(), pending=(), inventory=True) -> FactoryContext` returns the existing immutable context with the passed registration explicitly set and process_delta_registration=None. It uses the material baseline hash for existing inventory binding and NOW for synthetic time, exactly as existing factory_for does. Caller-supplied unit registrations are allowed only in unit mutation tests and confer no runner qualification.
- In existing `test_adaptation_factory.py`: `factory_for(mat=None, regressions=(), reviews=(), pending=(), inventory=True, *, implementation_registration)` removes the implicit default/sentinel. `reviewed(mat=None, pending=(), *, implementation_registration, **context_changes)` also requires the named registration and passes it to both constructions. Preserve the existing `current_registration()` function as the historical fixture loader; do not silently change what it reads. Existing `material(candidate=None, **changes)` still reads the six current source files; its bytes never determine expected pins.
- In both existing behavioral TestCase classes: a lazy `comparison_registration` property invokes fixed `current_v1_registration()` when used. Every behavioral call to factory_for/reviewed and registration mutation starts from an explicit `self.comparison_registration`; no module global is replaced. The literal-vector test remains byte-for-byte in its assertion/material logic and never reads this lazy property, so Tasks 1-3 can run it before final pins exist.
- In existing `qualify_factory.py`: `preflight(root, *, lane='legacy-v1')`; `child(output, *, lane='legacy-v1')`; `capture_artifacts(helper, output, execution_id, *, registration)`; `main()` adds `--lane` with exactly choices `legacy-v1` and `current-source-v1-comparison-v1`, default `legacy-v1`. It accepts no arbitrary module/profile/pin-path selector. `capture_artifacts` passes the explicit selected registration to every factory_for call. Child dispatch transmits only the fixed selected string.
- Extend existing `run_inner(modules, report, output, *, expected_ids=None)` internally: legacy keeps its existing ordering when expected_ids is None; current selection sorts test objects by `test.id()` and requires the resulting exact list to equal trusted expected_ids read by the fixed lane preflight. No CLI or environment argument supplies expected_ids. The J05 runner uses the same sorted-ID rule against its fixed fixture list.
- In `test_factory_qualification.py`: `launch(root, extra_python_args, output, cwd, env_changes, *, lane='current-source-v1-comparison-v1')` and `run_lane(..., lane='current-source-v1-comparison-v1')` make the current comparison explicit at every positive/inner-injection test. The new default-lane negative launches without any --lane option. Shared happy result cache is keyed by the explicit lane, never reused across lanes.

- [ ] **Step 1: Refactor existing behavioral tests into explicit current contexts.** Update all factory_for/reviewed call sites in test_adaptation_factory.py and test_factory_registration.py to pass their registration argument; mutation tests still pass their deliberately altered registration. Keep literal old vector reconstruction untouched. Rename the current-byte equality test to `test_current_comparison_pins_match_selected_source_bytes`, read expected hashes from the fixed final fixture subset and assert the new registration ID. Replace the old live-current golden digest assertion with the new fixture's independently frozen `current_v1_inventory_sha256`; preserve the old literal object and digest as a separate historical-fixture/serialization assertion, never as a claim about new source. Keep None-registration and old explicit-registration rejection tests, and rename docstrings/reports to identify J05-era current-source comparison. Update the detached-registration ID assertion to the new comparison identity. No global monkeypatch, environment-selected registration or implicit registration default is permitted.

Create `test_factory_current_v1.py` with `CurrentSourceV1ComparisonTests`: `test_fixed_current_lane_executes_supported_v1` stages the existing supported_candidate through explicit current_v1_context and real executed_cases; `test_historical_registration_rejects_current_source` verifies historical current_registration plus current material raises unsupported_adapter_implementation; `test_default_registration_rejects_current_source` verifies explicit None does likewise; `test_comparison_identity_does_not_claim_historical_source` checks new ID and current fixture binding. These four tests are ordinary inner behavior tests and launch no runner. The older unsupported adaptation candidate remains non-v1/unavailable; this comparison lane does not silently turn it into the J05 exact candidate.

```python
def test_historical_registration_rejects_current_source(self):
    mat = material(supported_candidate())
    with self.assertRaises(FactoryDenied) as caught:
        factory_for(mat, implementation_registration=current_registration())
    self.assertEqual(caught.exception.reason, 'unsupported_adapter_implementation')

def test_fixed_current_lane_executes_supported_v1(self):
    registration = current_v1_registration()
    factory, proposal, regression, approval, packet = reviewed(
        implementation_registration=registration)
    stage = factory.release_profile(packet, approval, [])
    self.assertEqual(stage.status, 'staged_simulation')
    self.assertEqual(factory.context.implementation_registration.registration_id,
                     'synthetic-factory-j05-current-v1')
```

- [ ] **Step 2: Add the closed runner lane and refactor all affected outer tests.** The default legacy preflight retains its exact six names, old fixture, old identity, old source-equality check and failure reason. It must reject this changed source before importing current behavioral modules. No `--lane` invocation may retry under another lane. Historical positive qualification remains evidence from its original executable/source snapshot; this work does not rerun or modify that snapshot. The new current lane preflight checks all 86 final expected package bytes before importing, then obtains its six-entry comparison registration from the fixed new fixture. Its manifest records `lane='current-source-v1-comparison-v1'`, the new registration ID, and full J05 expected source binding separately from the six-file semantic registration. No claim that changing an unpinned factory module preserves historical executable qualification is allowed.

All existing happy-result and adversarial runtime tests in test_factory_qualification.py use the new explicit current lane, including optimization, output collision, timeout, preload, wrong-origin/replaced-helper, binding mutation, source drift, skipped/omitted/duplicate/failing tests and missing-artifact cases. Update launch arguments inside direct `sys.argv` patches and preload child scripts too. Their test-root injection remains deliberate hostile test data; it never replaces a registration global. Preserve every old assertion's meaning but replace the hardcoded 37 count/modules with the independently recorded current lane planned ID list. Change the expected registration identity/digest to the fixed current comparison identity and fixture commitment. The untracked-module test may add an executing module under runtime/tests (covered by broader source/import inventory); an added package module must now be rejected by 86-name closure. Keep separate tests for both outcomes.

For targeted skipped/failing/omitted/import-origin tests, modify an existing required test body or its local execution seam in the copied root while preserving its test ID; do not append an extra test and mistake earlier fixed-ID rejection for the targeted failure. Test addition/duplicate-ID rejection separately. Each adversarial case starts from a successful untouched current-lane control, verifies its intended rejection stage, and never alters expected source-pin values to get past preflight.

Add outer `test_default_lane_rejects_changed_current_source`: run current script without --lane, require nonzero exit, invalid manifest with `pinned source mismatch`, no tests/behavioral artifacts, and old registration/default lane selection. Add `test_unknown_lane_rejected_before_execution` for arbitrary module-like/path-like strings. Neither negative may be marked expectedFailure or skipped. Positive artifact tests continue checking all cross-artifact hashes, actual execution IDs and synthetic/staged limits, now under the explicit new lane.

Keep the default legacy manifest shape and old failure behavior; new `lane`/full-source metadata is emitted only by the new current selector. Because existing legacy preflight raises before assigning its returned registration, the default negative may correctly have registration=null: assert unchanged old fixture selection by inspecting the exact default branch and fixture hash, not by inventing a populated failed-preflight field. The old default never falls through to current comparison.

- [ ] **Step 3: Pin nonrecursive module and test boundaries.** Use these literal tuples, with no caller override, discovery or load_tests hooks in inner children:

```python
# qualify_factory.py
LEGACY_INNER_MODULES = ('test_adaptation_factory', 'test_factory_registration')
CURRENT_V1_INNER_MODULES = (
    'test_adaptation_factory', 'test_factory_registration', 'test_factory_current_v1')

# qualify_window_readiness.py
INNER_MODULES = (
    'test_window_readiness_registration', 'test_window_readiness_envelopes',
    'test_window_readiness_engine', 'test_window_readiness_composition',
    'test_adaptation_factory', 'test_factory_registration', 'test_factory_current_v1',
    'test_observed_stop_v2')
FORBIDDEN_INNER_MODULES = frozenset({
    'test_window_readiness_evidence', 'test_factory_qualification',
    'test_observed_stop_v2_acceptance', 'test_synthetic_provisioning_acceptance'})
```

The two refactored factory behavioral modules operate through their explicit current comparison registration and launch no subprocess qualifier. test_observed_stop_v2 is the exact current-source v2 comparison; its historical full-package tuple remains unchanged. All acceptance tests and outer runner tests remain outside the child. Inspect every selected module for any runner-launch helper; reject selection if it directly or indirectly enters either qualifier. At final freeze, independently enumerate/review the exact sorted planned test IDs for each tuple and record them in the external fixture as `current_v1_test_ids` and `j05_test_ids`. The runner requires exact equality between its class-based selection, that reviewed ID list and executed IDs. Add an outer subprocess test proving one launcher creates exactly one bounded child; child mode rejects attempts to enter main/launch again, and errors if an outer/forbidden module appears in its selected modules or planned IDs. Do not install a global monkeypatch to fake this assertion; record launcher/child role in the manifest and inspect actual child launch events in an isolated outer test.

No current-lane green assertion runs until Step 4's single final freeze exists. Red tests before it may assert fixed-fixture-unavailable; package code is not repinned merely to satisfy a task's intermediate test.

- [ ] **Step 4: Freeze final expected source/resource inventories only after all package and lane changes are reviewed.** Enumerate the exact 86 names; compare test-discovered package `.py`/schema names with both independent tuples, and inspect AST to require literal strings for J05 (runtime equality cannot distinguish an alias). Hash final source bytes with SHA-256 into the new `runtime/tests/fixtures/window-readiness-current-registration-v1.json`; separately include reviewed candidate file/profile/process/policy hashes, current_v1_inventory_sha256 over the six sorted path/hash entries, and reviewed test ID lists. Store its before/after snapshot and commit identity in evidence. Expected pins must be read from that already reviewed fixture before constructing submitted runtime material. Never regenerate expected pins inside a test from bytes it is about to admit. The fixture is outside the 86-file package closure and contains neither its own digest nor a digest of an inventory that includes itself. No final source digest is pasted into profiles.py, synthetic_provisioning.py or any other file being hashed. A broader execution inventory may independently hash the external fixture. Do not alter old pins or old serialization vectors. If any source changes after freeze, invalidate that J05 run, review/freeze a new current inventory and retain the failed attempt; do not incrementally repin each earlier task.

The external fixture has exactly keys `registration` (the eight-field J05 registration object with implementations represented as sorted [path, sha256] pairs), `candidate_file_sha256`, `current_v1_inventory_sha256`, `current_v1_test_ids`, and `j05_test_ids`. The loader reconstructs exactly the eight registration fields explicitly; additional fixture metadata never becomes a registration field. current_v1_registration takes only the six registered legacy names from fixture.registration.implementations, verifies their canonical inventory digest equals fixture.current_v1_inventory_sha256, and assigns the fixed distinct current-comparison ID. No caller argument selects any of these commitments.

```python
def test_independent_closed_literal_inventory(self):
    package = Path(proofkey.__file__).resolve().parent
    discovered = tuple(sorted(str(p.relative_to(package)) for p in package.rglob('*')
        if p.is_file() and (p.suffix == '.py' or p.name == 'schema.sql')))
    self.assertEqual(len(WINDOW_READINESS_IMPLEMENTATION_PATHS), 86)
    self.assertEqual(WINDOW_READINESS_IMPLEMENTATION_PATHS, discovered)
    self.assertEqual(OBSERVED_STOP_V2_IMPLEMENTATION_PATHS, discovered)
    module = ast.parse((package / 'profiles.py').read_text())
    assignment = next(n for n in module.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'WINDOW_READINESS_IMPLEMENTATION_PATHS' for t in n.targets))
    self.assertIsInstance(assignment.value, ast.Tuple)
    self.assertTrue(all(isinstance(n, ast.Constant) and type(n.value) is str for n in assignment.value.elts))
```

- [ ] **Step 5: Verify the source-only evidence runner and its rejection tests.** Implement the new runner's source/import and accounting code before Step 4 freezes source; execute its final verification now. Follow the existing qualifier algorithms while retaining its legacy default contract and selecting only Step 3's literal J05 module tuple. The new current-v1 selector shares infrastructure, never the old expected pins. Source inventory includes executing test/support/script files regardless of Git tracking, while package closure remains exactly 86. Reject optimized Python, missing/mismatched expected source, aliased modules, omitted/reordered/duplicated test IDs, forbidden outer modules, nested launcher/child entry, skips, expected failures, failures/errors and any before/after source drift. Keep observed external distribution identity separate from a complete transitive-closure claim. `test_window_readiness_evidence` is outer-only and checks all these failures in copied disposable test roots, not by changing production expected pins.

```python
def require_full_run(planned, executed, result):
    if (not planned or len(planned) != len(set(planned)) or planned != executed
            or result.testsRun != len(planned) or result.skipped or result.expectedFailures
            or result.unexpectedSuccesses or result.failures or result.errors):
        raise ValueError('incomplete_current_source_execution')
```

Runner creates bound proposal/regression/simulated-review/staged-manifest evidence only after exact execution coverage succeeds. Keep existing regression schema: proposal/baseline/candidate/test hashes, runner_id/provenance, execution_id/executed_at, result and each exact required case/output_hash. Capture raw bytes independently of normalization and final verification. A patched hash/import/registration/receipt/test omission must fail runner tests, leaving diagnostic output and a non-success manifest. Do not issue a successful receipt when a unittest group contains an unmeasured fit blocker.

- [ ] **Step 6: Run the explicit final lanes and all-green full discovery on frozen source.** The lane refactor is mandatory, not contingent on an unexpected failure. No deliberately red old-pin positive remains in discovery: historical behavior is asserted as an affirmative negative and literal serialization; current positive behavior uses the separate fixed current lane. Run these commands from the worktree root, with the fixed interpreter and no installation:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest test_adaptation_factory test_factory_registration test_factory_current_v1 test_factory_qualification test_window_readiness_evidence -v
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B -m unittest discover -s runtime/tests -v
```

Both commands must exit zero with all discovered planned cases executed and no skips/expected-failure masking. The controller then runs the standalone current-v1 and J05 lanes below. Use a fresh `mktemp -d` parent under outputs, resolve it to an absolute path, and pass new child paths current-v1 and j05 (the children must not exist; the parent may). The output path is the only variable argument; the lane never accepts a code, profile or pin path.

```bash
task_evidence_parent=$(mktemp -d "$PWD/outputs/window-readiness-final-XXXXXXXX")
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B runtime/scripts/qualify_factory.py --lane current-source-v1-comparison-v1 --output "$task_evidence_parent/current-v1"
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B runtime/scripts/qualify_window_readiness.py --output "$task_evidence_parent/j05"
```

The outer test's default-old-lane invocation is expected to exit nonzero and the test itself must pass its exact denial/no-artifact assertions; this is not a failed test hidden from discovery. No failure or stale-pin error is omitted from the run denominator. Retain every attempt's command, exit status, duration, test counts, failed cases and final hashes; refreeze only after a diagnosed correction and fresh review if package/source edits are needed.

- [ ] **Step 7: Separate evidence outcomes, independent review and finite child archive.** Emit a source qualification report with distinct sections for default v1, current-source v2, candidate in-domain behavior, candidate out-of-domain denials, measured calls/active/tool times, and unchanged goods/other paths. Include the exact raw-domain restriction and no-install/no-native-HTTP/no-live-provider/no-actual-human/no-activation/no-migration/no-retained-resolver/no-completed-timed-drill limitations. Record that the known J06 installed pair is completed-only: executable `/private/tmp/proofkey-j06-0yc_36hd/installed-env/bin/python`, original root `/private/tmp/proofkey-j06-installed-80e0d6f-attempt5/probe/library-window/case-feb2ba2f2de14021894506f99484d9c8`; current availability/authority/deadline support remains unestablished. Do not execute, reopen through candidate, repin or copy these roots for runtime reuse.

Historical pending status stays `unqualified`: a fresh fixture, completed phase with processing_status=pending, relocated package, copied root or recreated grant cannot establish it. Only an independently identified already-pending original pair with its actual old executable/dependencies/roots/authority/supported entrypoints and before/after identity/deadline/debt/effect/read accounting can alter that status in a separately authorized activity. The finite child may finish its implementation/reporting obligations while parent J05 remains open.

Obtain independent review of the final implementation and exact evidence, resolve findings with new relevant tests and refreeze if source changes, run child-only strict OpenSpec validation using the repository's already available OpenSpec command, then `/opsx:archive` only this completed child. Preserve shared v1/v2 living requirements and all unmet parent acceptance gates. Final task completion and archive occur only after the stated executed evidence and independent reviews.

## Self-review: coverage, interfaces and unresolved execution gates

| Requirement / boundary | Owner and named proof | Cross-task contract / result |
| --- | --- | --- |
| Exact identities and semantic delta; forbidden siblings | T1 ProfileDeltaTests and field mutants | Entire validated candidate comparison; exact two affected old IDs |
| Resource mirror, eleven profiles, old fixture/schema hashes | T1 resource tests; T5 freeze | File hash distinct from release hash; explicit package lists |
| Detached mutually exclusive registration; all reconstruction paths | T1 registration tests | New optional context field explicitly threaded through four paths |
| 86 names and bounds; independent expected source | T1 bounds; T5 AST/inventory/import tests | Literal tuple, external final hash fixture, no package files added; old pins unchanged |
| Proposal/manifest/receipt commitments and unit-vs-executed evidence | T1 staged binding; T5 runner mutants | Exact nine-field object, existing regression schema retained |
| Raw bytes precede model normalization | T2 typed-method poison test | Private data helpers; typed and raw consumers share source transaction |
| Strict full finite envelope domain | T2 boundary/schema matrix and Review Focus 2 | Single bounded read error; unknown dispatch without fabricated evidence |
| Full original join/digest/ACL/deadline/collisions | T2 original tests | Window automatic terminal proof only; exact-slot knob unchanged |
| Retained-source full-ID acceptance and corruption denial | T1 pure helper; T2 direct capture; T4 finalization | Shared acyclic explicit-field formula, no row repair or historical authentication claim |
| Unreadable committed effect and narrower exact read domain | T2 direct and T3 engine Review Focus 3/5; T5 report | Zero resend/undo; scoped parity only |
| Four physical leases, strict owner-before-settle | T3 Review Focus 1 and positive helper | Ten observations over four calls; no packet grant |
| Latest budget/stop and race/save fences | T3 Review Focus 4 | No advance on failed read/save; original identity/deadline retained |
| Fresh S0 policy/provider CAS and positive budget fit | T2 direct provider; T3 fresh policy/full path; T4 admission run | Fit must be measured; bounds immutable |
| Closed dual validation/host composition/CLI/control denials | T4 composition matrix | v3 run-only, v1 run-only, v2 stop retained |
| Required typed packet source before hashing | T1 fixture builder; T2 capture; T4 library/CLI | No post-prepare mutation or extra readiness packet reads |
| Explicit current-v1/legacy lane split and nonrecursive runner | T5 refactored helper/behavior/outer tests | Full discovery all-green; old default rejects changed bytes; exact inner tuples |
| Source-only evidence vs historical pending | T5 report/review/child archive | Completed pair never passes pending; parent J05 stays open |

Self-review found no intended spec-coverage omission. Draft interfaces are explicitly new where named; existing public signatures remain unchanged. Timing uses the inspected `remaining_seconds` API and engine saving uses the existing nested transaction facility. Source anchors were rechecked after the prerequisite freeze; re-resolve them if earlier tasks move the code. The exact J05 implementation/source/resource hashes intentionally do not exist yet: final J05 bytes are not implemented. The separate prerequisite stop-v2 freeze is recorded above. Budget fit, final independent implementation review and historical pending evidence remain execution gates; this document does not pre-answer them.

Review provenance: the corrected draft addressed preflight I1-I4/M1 with retained-source full-ID compatibility, a complete pre-hash typed packet fixture, provider-before-engine task ordering, mandatory explicit current/historical lane refactoring and literal nonrecursive inner suites. Its scoped rereview and handoff-hygiene rereview reported C0/I0/M0. The fifth task separates closed composition from final lane migration/freeze/evidence. Final independent review of this promoted plan remains a separate execution gate.
