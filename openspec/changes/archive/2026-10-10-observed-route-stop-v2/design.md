## Context

Date: 2026-10-10. Source basis: `71b4cd4`. Planning only: no source changes, runtime construction, retained-store opens, tests, provider calls, or network. This is a proposed next leaf, not a completed J07 claim. This design is supported by source-backed discovery and independent architecture preflight. It removes unnecessary pre-stop source capture and route-store API expansion from the stop-only minimum.

## Goals / Non-Goals

**Goals:** authenticated same-owner same-clock stop with unchanged original identity, accounting and business deadlines.

**Non-Goals:** recover, reply, reopened-owner control, migration, live provider use or general activation.

## Decisions

Add one closed executable factory contract, `fixed-synthetic-observed-stop-v2`, with the existing fixed v1.3 profile / v1 processes. It permits ordinary registered run and **stop only for a case successfully observed by this very live owner using its original clock**. It does not permit registered recover, reply, transfer, any interrupted claim, or any reopened-owner control. The current `fixed-synthetic-v1` contract remains run-only, including when a new build provisions it.

No stored schema migration. Retain `HostExecutableBindingV1`, `LocalAdmissionCompositionV1`, `ReleaseArtifactV1`, `KnownFactoryV1`, `RegisteredReleaseV1`, `AdmissionClaimV1`, `RouteRecordV1`, the marker schema and existing journal/control database schemas. Version the executable contract through the new factory key and exact expanded inventory. Add a private in-memory `_ObservedStopV2` entry type. Do not claim a new wire version merely because the executable contract is v2.

## Dependency-manifest finding, verified from source

There is no class named `DependencyManifest` in this source tree. The relevant per-release object is canonical `dependency_json` with kind `route-closure-declaration-v1`. `registered_releases.py:273-287` accepts 1–512 sorted unique entries, each containing name, sha256 and a role from a closed set. It requires exact ordered equality among:

`dependency.entries (name, sha256) == KnownFactoryV1.implementation_pins == embedded implementations (name, sha256)`.

It also checks `KnownFactoryV1.dependency_hash == sha256(dependency_json)`. `KnownFactoryV1:186-202` accepts a nonempty factory identifier without hardcoding `fixed-synthetic-v1`. `ReleaseRegistryV1` resolves that declared known factory. Thus additional module hashes already fit the existing per-release schema, but they must be accompanied by their exact embedded bytes, the matching factory pins and a new dependency hash. Adding names to dependency JSON alone is rejected. The envelope remains capped at 8 MiB, each blob at 1 MiB, and 512 entries.

The hardcoded restriction is executable validation: `HostExecutableBindingV1.__post_init__:123-133` requires the v1 factory key and exact `FIXED_IMPLEMENTATION_PATHS`. Provisioning also selects that list/key at `synthetic_provisioning.py:237-263,618-634`. Modify these consumers with a **closed per-factory selection**, leaving the old list untouched. No global registered-release schema change is required.

Keep `completeness='unestablished'` as required by the existing declaration contract. A larger first-party inventory does not establish interpreter, stdlib, native-library or third-party environment completeness. Build/install provenance remains a separate qualification receipt.

## Exact versioning and provisioning changes

1. Keep `FIXED_IMPLEMENTATION_PATHS` unchanged and add `OBSERVED_STOP_V2_IMPLEMENTATION_PATHS`, an explicit sorted tuple of every first-party `.py` file and `schema.sql` listed in the appendix. The current aggregate source bytes are 1,321,799, measured with `wc`; this is feasibility evidence, not proof that the final encoded release fits. Existing aggregate/envelope validators must pass after changes before any private allocation. Any new runtime module added during implementation must be explicitly added to the tuple and reviewed. Never discover the allowed inventory by globbing the installed package at runtime.
2. In `HostExecutableBindingV1.__post_init__`, accept exactly two cases: both `factory_id` and `host_factory_key` are `fixed-synthetic-v1` with the old exact tuple, or both are `fixed-synthetic-observed-stop-v2` with the new exact tuple. Reject mixed pairs, unknown keys, missing/extra/duplicate/reordered names. Keep the current default `host_factory_key='fixed-synthetic-v1'`; v2 callers must explicitly pass v2. Retain all digest and identifier validation.
3. Change trusted provisioning to `prepare_synthetic_release(spec, *, parent, clock, execution, factory_key='fixed-synthetic-v1')`. The new keyword is a trusted library parameter, not a field in `CanonicalRequest`, host command, fixture or arbitrary configuration file. Reject all other values. `_validate_input` receives this key, snapshots it in `_ValidatedInput`, reads exactly its selected tuple using existing bounded no-follow `_installed_bytes`, and creates corresponding declarations. Construct `HostExecutableBindingV1(..., host_factory_key=factory_key)` explicitly. Do not silently select v2 because stop was requested.
4. Existing `PreparedSyntheticReleaseV1`, `_revalidate_prepared` and `configure_registered_cli` can remain their current schema/types: they reconstruct the binding and compare registered/pinned bytes. Audit their reconstruction calls to preserve the explicit factory key. `bootstrap.CliConfiguration._validate_registered` compares the factory with the binding and need not broaden clock/profile/process acceptance.
5. Existing `validate_composition` already compares artifact, resource, factory pins/dependency hash and installed bytes. With the two-key binding validator it can retain the same loop and exact checks. Create fresh v2 roots and a separately provisioned synthetic review grant covering their new artifact hash. No old review grant implicitly covers the new hash.
6. Existing marker configuration includes `binding_hash`, artifact hash and resource/control identities. Therefore v2 cannot adopt a v1 root by reusing its marker. Do not rewrite markers, claims, route records, dependency declarations or old receipts. A v1 root whose old installed pins differ from the new build continues to fail executable validation; it remains usable only with its original compatible installation. This leaf does not add side-by-side old-code loading.

## Public and internal API shape

New public library method:

```python
RuntimeResources.stop_registered(case_id: str, generation: str,
                                 auth: AuthContext, *, execution: ExecutionContext)
```

It checks exact owner type as `run_registered` does and calls:

```python
RegisteredAdmissionOwner.stop(case_id, generation, auth, *, execution)
```

No new `recover_registered` or `reply_registered` in this leaf. Existing public host command remains `StopCommandV1(release_id=..., case_id=..., generation=...)`; the factory contract, not user command shape, determines support.

At `HostDispatcher._execute`, preserve fresh resolver authentication and exact release checks. For registered commands: run keeps current behavior; recover/reply remain immediate scope denial; stop requires the v2 key **and already existing self._resources**. A stop with no live resources returns scope denial before `create_registered`; it must not open stores looking for eligibility. Stop then calls `self._resources.stop_registered`. A separately created/reopened RuntimeResources may exist through the library, but has no live observation receipt and therefore denies stop.

Add `entry_kind=None` to `WorkflowEngine._execution_scope`, `ActionGateway.execution_scope` and `RegisteredAdmissionOwner.guard_execution`. Only `WorkflowEngine.stop` passes `entry_kind='stop'`; existing other entrypoints retain None. The owner guard accepts a stop token only with the stop tag and exact execution object/snapshot. An admission token accepts the existing None tag and existing exact original admission-parent checks. This makes a stop token unusable for recover, reply or run even before bind. `require_entry` explicitly rejects a stop token. No relaxation of gateway.bind_request, prepare_entry or seal_before_admit is needed.

## Live receipt and minimal eligibility checks

Add an owner-private dictionary keyed by `(case_id, generation)`, initially empty. Mint a nonserializable immutable receipt only after the last successful parent/time check in `RegisteredAdmissionOwner.run` and after the observed claim write returned/read back successfully. Receipt records creator clock identity, immutable original request/binding, exact final claim bytes, exact final route bytes, original attempt (or its canonical immutable image), original admission execution window, and observation-time UTC/monotonic high-water marks. V1 runs do not mint stop receipts. `close` clears them. Any BaseException before all final checks leaves no receipt even if the route is already observed.

The stop wrapper executes this sequence:

1. Check exact owner/runtime associations, creator thread, open/non-uncertain state, no active entry, held writer lease and unchanged root/control/marker identities. Check `clock is _created_clock` where `_created_clock` was stored on construction; compare current finite UTC/monotonic with the last successful receipt/control high-water marks. The package clock is the same instance, never reconstructed or reanchored. This is an in-process guarantee, not resistance to arbitrary malicious Python code modifying all owner internals.
2. Validate detached exact typed AuthContext, IDs and ExecutionContext. Derive **one** `control_context(execution, clock)` at entry and use that clipped five-second context for preflight and engine stop. Copy/snapshot its four fields and use the exact object until exit. Do not renew the five seconds per suboperation. Admission claims retain their original execution window; stop does not compare its fresh I/O window to the old admission window.
3. Require v2 and a receipt for the exact key before querying private case state. Compare current auth caller to receipt binding principal/original claim caller and current proof-reference digest to original claim proof digest. This strict v2 leaf supports the original credential only; rotation/delegated controllers are explicitly unsupported. Still perform source authentication below: equality with a stored digest is not authentication.
4. Use current bounded `_ClaimStore.pending`, `.find`, `routes.get` and `routes.for_generation` calls with the one context. Require no pending claim anywhere. Require exact byte equality to the receipt's final claim and final route and both states observed. Their validated original join was established during this owner's successful run, so stop-only does not need a new public route-validator API or another call to `observe_admitted`. Never call its write transaction for a control.
5. Capture **one current bounded journal snapshot** with `CaseStore.capture_retained_state(execution=control, clock=clock)` outside the engine execution scope. Use the public snapshot envelope, not the private database connection. In the bounded image require exactly one current case, original request, request/binding/version row and original transferred admission attempt for this key; compare these identities to the live receipt. Select the attempt by `claim.attempt_id`, never `claim.claim_id`: AdmissionAttempt has neither claim_id nor binding. Join its explicit fields as specified below. Require the current checkpoint's binding and original profile/process/policy versions and original request to match, unchanged or shortened deadlines, and no dropped original admission debt/import linkage. The attempt remains exactly the transferred attempt recorded at observation. Retain every wait for the exact case/generation and its immutable envelope, including expiry, original wait budget/deadline, origin checkpoint, owner/graph/communication identity and accepted-reply fields. Exclude only lifecycle and successor_hash from the immutable wait projection; allow unchanged lifecycle/successor or pending→stopped with an audited nonnull successor hash. An observed stopped wait or checkpoint/request stop flag must never revert. Compare original budget counters/reservations by field semantics, not whole-checkpoint equality: successful source reads may add debt and stop may change audit/phase. The engine's public checkpoint reader will additionally check budget/audit/fence integrity within its own execution scope.
6. Enter private `_ObservedStopV2` containing the exact clipped context object/snapshot, receipt and current detached auth; invoke `self.engine.stop(case_id, generation, auth, execution=control)`. Keep receipt/capability nonserializable and clear the active capability in `finally`. A repeated valid same-owner stop is permitted while the clock/business cutoff remains valid; it creates no new registration/admission and may charge another control read.

The initial journal snapshot is a bounded preflight for inherited readers, not a complete hostile-runtime safety claim. It does not turn the existing constructor into a bounded reopen operation, and cannot prevent an unrelated privileged process from altering files. Keep the existing single-writer/no-external-mutation assumptions.

Compare continuity both to the original observation receipt and the last successfully observed stop view. Retain a successfully validated preflight view before dispatch; any later failure cannot make an already observed true stop flag or stopped wait eligible to revert. When a bounded postflight view is available, retain it too. Lack of time for postflight must preserve committed state and fail closed, never renew the context or erase the prior floor.

### Exact JSON and admission joins

Decode the canonical outer retained image with `_parse(snapshot.payload, 4194304)`. Do not call that canonical parser on stored inner model strings: journal checkpoint/request/binding/attempt/account/wait values are Pydantic `model_dump_json()` output, and versions_json uses ordinary json.dumps. Both can have legitimate noncanonical key order/spacing. Add a private bounded inner JSON decoder (UTF-8 <=262144 bytes, duplicate keys rejected, nonfinite values rejected, dict required) which does not require raw byte canonical order, then call `_model(decoded, ExactModel)`. Validate versions against the exact expected three-key dictionary. Keep existing claim `_parse` behavior unchanged. V2-produced waits are WaitRecordV1; unexpected legacy/unknown wait envelopes deny this capability.

At receipt creation and current-view validation, select the sole attempt row whose `attempt_id == claim.attempt_id`; require row and AdmissionAttempt state `transferred`, row claimed_case_id equal to binding.case_id, row dedup_hash equal to `route_data['dedup_hash']`, and exact mapping below. Here `route_data=json.loads(route.wire_bytes)` and `binding=claim.binding`; route/claim equality and observation commitments have already been validated.

```python
expected = dict(attempt_id=claim.attempt_id, claimed_case_id=binding.case_id,
    claimed_object_id=binding.object_id, claimed_principal_id=binding.principal_id,
    request_id=binding.request_id, request_revision=binding.request_revision,
    consent_revision=binding.consent_revision,
    claimed_caller_id=route_data['auth_claim']['caller_id'],
    proof_digest=route_data['auth_claim']['proof_digest'],
    business_fingerprint=route_data['business_fingerprint'],
    request_hash=route_data['request_hash'], dedup_hash=route_data['dedup_hash'])
```

Require each mapped field equal, deadline>created_at, and exact current attempt row/model equality to the observation receipt, preserving created_at/deadline. Imported AdmissionAccount must have the same claimed_case_id and zero pending_tool_calls/pending_active_seconds. Host claim_id participates only in exact host-claim identity; it does not select an AdmissionAttempt.

### Source checks that must stay in engine stop

No preliminary source snapshot is required. A source snapshot is not current authorization and would add irrelevant full-store capture/time overhead. `engine.stop:386-410` already checks the exact current generation, sets current AuthContext, calls `gateway.authenticate_control(..., purpose='stop')`, then calls `store.stop_waits_atomic` with the checkpoint returned **after** authenticated-read accounting. `gateway.authenticate_control:540-554` performs a real accounted case read, checks the current original binding, caller==principal, case authorization, generation and request revision; the source adapter verifies the proof. Preserve it intact.

Do not add consent refresh, customer approval reads, ownership grants, or effect reconciliation to stop. Stop revokes continued work; it is not new business permission. Wait fencing is done in the existing atomic journal operation. The source call required here is `read_case`; result construction reads existing local effects and does not send/undo/reconcile business effects. A wrong proof rejected by the owner produces no source calls; a once-valid proof revoked in the current source can still reach and fail the accounted source check, preserving its debt.

### Time and result semantics

Use fresh bounded stop I/O time, but preserve all original claim, checkpoint, budget, intent and wait cutoffs. Existing gateway control reads still clip transport to checkpoint.deadline; expired business cases therefore may be denied and are not promised post-deadline stop. Keep this limitation explicit. On a failure after durable `stop_waits_atomic`, retain the stop; do not roll it back to make the public result look atomic. Successful historical saved results remain unchanged. A late/denied public receipt does not establish that no stop was committed.

## Eight executable tests to implement

Use a new `runtime/tests/test_observed_stop_v2.py` with a trusted v2 fixture built through the new provisioning keyword. Reuse the exact SyntheticReplayClock class and the existing `paced_clock` technique for deterministic local timing; do not use FakeClock as the positive production-composition path. Tests below are implementation instructions, not executed evidence.

1. **Manifest/key compatibility.** Build `ReleaseBlobV1`, `KnownFactoryV1`, `ReleaseArtifactV1`, `ReleaseRegistryV1` using both inventories. Assert v2 embedded bytes/pins/dependency entry hashes round-trip via `RegisteredReleaseV1(wire_bytes)`. Construct `HostExecutableBindingV1(..., host_factory_key=...)`. Assert old key/old tuple accepted; new key/new tuple accepted; mixed key/list, missing extra module, reordered list, absent blob or mismatched hash denied. Provision old key by default and verify v1 control denial. Existing schema stays version 1.
2. **Positive run→stop, same resources.** `runtime = RuntimeFactory().create_registered(release, clock, composition=composition, execution=context(clock))`; `first = runtime.run_registered(request, auth, execution=context(clock, 120))`; `stopped = runtime.stop_registered(case_id, first.binding.generation, auth, execution=context(clock))`. Assert stop requested, verified historical effect unchanged, effect count unchanged, historical `store.saved_result` unchanged. Compare before/after claim and route bytes exactly, original request/binding/attempt exactly, original deadlines not extended, and retained snapshot admission table identities/counts unchanged. Assert post-run source operations are exactly the current stop read, with no business transport.
3. **Host parity without reopen.** Construct `HostDispatcher` with the v2 composition. `submit(RunCommandV1(...), resolver.handle(ref), execution)` then `submit(StopCommandV1(...), resolver.handle(ref), execution)` on the same dispatcher succeeds. A new dispatcher receiving stop first is denied; patch `RuntimeFactory.create_registered` with a spy that fails if called on that stop. RecoverCommandV1 and ReplyCommandV1 remain denied on the active dispatcher. Host v1 remains run-only.
4. **Current auth and target.** Parameterize foreign generation/case, wrong caller and wrong proof. Call `stop_registered`; assert no new source call and exact retained snapshot/claim/route equality. Add a source-authorization-revoked fixture/fault through test-only setup, keeping caller/proof initially matching: source read is charged and denies; no stop or business effect occurs. Do not require whole-snapshot equality for that accounted denial.
5. **No interrupted/reopened eligibility.** Reuse host-admission failure injections at preparation, route reservation, seal and final claim write (including route observed / claim sealed). Assert no minted receipt and stop denial. Close/recreate a successfully observed v2 runtime with the same clock; stop still denies because its receipt map starts empty. Existing `test_prepared_restart_blocks_without_new_journal_debt` and marker reopen denials remain unchanged. No subprocess timing success claim.
6. **Owner/capability bypass.** Parameterize changed marker, swapped runtime.engine/store/world, changed clock alias, cross-thread call, reentrant call, closed owner, and direct `runtime.engine.stop(..., execution=...)` without owner wrapper. All deny before new business/source entry. During a test-captured active stop scope attempt engine.run/recover/reply with the same execution object; the entry tag/require_entry guard rejects it. Restore aliases for cleanup and verify the original writer lease remains exclusively held until clean close.
7. **One five-second budget / original deadlines.** Advance the patched SyntheticReplayClock during claim/route/journal preflight so aggregate work reaches the cutoff; no engine/source call begins after expiry. Test zero/expired context, mutated context, backward UTC/monotonic and a stopped case past its original deadline; all fail without extension. Two successful calls use fresh I/O windows but preserve the original admission execution and business cutoffs. No clock anchor reset is permitted.
8. **Stop commit then interruption and continuity regressions.** Patch `CaseStore.stop_waits_atomic` to call its real method then raise a test `BaseException`. Capture the actual pending WaitRecordV1 first; after interruption and repeated same-owner stop compare its model_dump excluding only lifecycle/successor_hash, and assert original wait.expires_at, wait.budget.deadline and origin_checkpoint exactly preserved. Assert durable checkpoint/request stop flags cannot revert and stopped waits cannot become pending. Keep cleared owner.active, unchanged business effects, original request/attempt/claim/route and original deadlines. Pure projection tests should shorten an otherwise valid original wait expiry and require continuity rejection, then test stopped→pending rejection. Decode genuine unmodified captured model strings (assert at least one is noncanonical); reject duplicate keys/nonfinite values/oversized inner strings. Mutate captured attempt claimed_principal_id or proof_digest and require the explicit attempt join to deny; the normal distinct claim_id/attempt_id case must succeed. Registered recover remains denied.

For test 8, provision a fixture/request that reaches a real supported pending wait under the same fixed profile and is fully admission-observed. Do not manufacture a wait by directly changing production state or relax fixture admission requirements. Existing host-admission test helpers may build that trusted fixture; production provisioning must preserve its current checks.

## Source edit scope and completion boundary

Expected product edits: `host_admission.py` (per-key inventory/binding, live receipt, stop wrapper and tagged guard), `host.py` (registered stop method/dispatch), `gateway.py` and `engine.py` (entry tag plumbing only), `synthetic_provisioning.py` (trusted closed factory selection). `bootstrap.py` only if its exact reconstruction fails to preserve key; no semantic widening. New test file plus focused updates/additions to provisioning/host tests. No route/journal/source schema changes, no new stop semantics inside engine, no recover/reply enablement, no runtime clock changes, no new provider interfaces.

The expanded inventory does not mean every listed module is edited or executed. Before implementation, create the scoped OpenSpec proposal/design/tasks and Superpowers implementation plan. Before completion, run relevant tests and existing regression gates, record installed/new-release evidence, and archive only this stop leaf. Keep J07 overall and restart/recover/reply claims open.

## Appendix: frozen first-party inventory for v2

Use the following package-relative names as one sorted tuple; these are all `.py` files and `schema.sql` at the inspected HEAD. Profile/fixture JSON are separately exact committed release inputs. No arbitrary provider activation follows from including provider module bytes.

```text
__init__.py
adapters/__init__.py
adapters/case.py
adapters/delivery.py
adapters/messaging.py
adapters/operator.py
adapters/ownership.py
adapters/returns.py
adapters/scheduling.py
adapters/world.py
admission.py
admission_routes.py
api.py
assessment/__init__.py
assessment/audit.py
assessment/cache.py
assessment/contracts.py
assessment/coverage.py
assessment/drills.py
assessment/driver_contracts.py
assessment/drivers.py
assessment/isolation.py
assessment/labels.py
assessment/ledger.py
assessment/readiness.py
batch.py
batch_files.py
bootstrap.py
budget.py
cli.py
clock.py
contracts.py
engine.py
evidence/__init__.py
evidence/catalog.py
evidence/intake.py
evidence/processing_contracts.py
evidence/redaction.py
execution.py
execution_consumer.py
execution_trace.py
exporter.py
factory/__init__.py
factory/proposal.py
factory/release.py
factory/views.py
gateway.py
host.py
host_admission.py
host_contracts.py
host_files.py
host_writer.py
identity.py
journal.py
ownership.py
ownership_contracts.py
ownership_gateway.py
ownership_store.py
packet_contracts.py
packets.py
planner.py
policy.py
ports.py
process.py
processing.py
processing_orchestration.py
processing_summary.py
profiles.py
providers/__init__.py
providers/anthropic.py
providers/elevenlabs.py
providers/invocations.py
providers/protocols.py
providers/replay.py
providers/unavailable.py
registered_releases.py
release.py
replay.py
retained_state.py
schema.sql
source_retained_state.py
synthetic_provisioning.py
trace.py
verifier.py
wait_contracts.py
waits.py
```

## Risks / Trade-offs

- Existing retained-store constructors are not hostile-state bounded: require current-live-owner evidence and do not claim safe reopen.
- Larger inventory does not establish third-party or interpreter closure: keep completeness unestablished.
- Stop can commit before a late failure is returned: preserve durable fences and accounted work, never roll back or infer no stop from a failed response.
- Retained old roots require old exact executable pins: use fresh v2 roots, never silently repin.

## Migration Plan

Add the closed opt-in factory key and provision new artifacts, explicit synthetic review grants and new private roots. The default v1 contract stays run-only. No persisted schema migration or old-root edits occur. Rollback removes v2 entry support while preserving existing evidence.

## Open Questions

No blocking design question remains for this bounded leaf. Real execution must establish pending-wait fixture feasibility and exact encoded release bounds; failed checks remain failures, not permission to broaden scope.
