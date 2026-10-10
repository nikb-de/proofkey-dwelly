## Context

This is the next finite, offline J05 adaptation leaf. It formalizes private design revision 3 and its accepted rereview; it is not implementation or execution evidence. The current factory rejects executable process edits even with source registration. Scheduling adapters presently receive normalized typed world results, and the window graph goes directly from `read_authority` to `window_gate`.

The design depends on completed and archived `observed-route-stop-v2` and its source freeze. Shared provisioning requirements here include the complete v1/v2 post-archive behavior and add v3 selection only. A separate reviewed Superpowers plan must follow this change's tasks before implementation. Source anchors below describe inspected structure, not final hashes.

The historical-pair discovery found a matching J06 installed package and original registered resource root with a **completed** window case. No qualifying historical pending case was found in that bounded search. That evidence distinction is part of the acceptance contract.

## Goals / Non-Goals

**Goals:** execute one explicitly registered synthetic window process change; independently read readiness; expose real raw source responses; normalize only a finite envelope domain; preserve original identity and debt through ambiguous outcomes; bind exact semantic and source material into proposal and staging evidence; compare current-source behavior honestly.

**Non-Goals:** general process interpretation, arbitrary semantic deltas, new package modules/dependencies/DDL, native HTTP or live providers, installation, authentic human approval, activation, retained-version resolution, migration, a timed adaptation drill, or automatic completion of J05. Candidate registered recovery/reply/stop/transfer remain unavailable. Historical preservation is a separate unresolved evidence gate.

## Decisions

### Closed identities and semantic delta

| Item | Fixed value |
| --- | --- |
| Host factory key and factory ID | `fixed-synthetic-window-readiness-v3` |
| Candidate profile ID and resource | `flat-window-readiness-v1`, `flat-window-readiness-v1.json` |
| Profile contract family | `v1.3` |
| Window process ID and version | `reschedule-window-readiness-v2`, `v2-window-readiness` |
| Scheduling capability version | `synthetic-scheduling-dual-v1` |
| Raw discriminator | `synthetic-scheduling-envelope-v1` |
| Semantic registration ID | `synthetic-window-readiness-delta-v1` |
| Registration provenance | `local_controlled_synthetic` |
| Baseline | `flat-v1.3`, `5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4` |

Keep v1.3 because packet/ownership family validation already distinguishes v1.3/v1.4. New profile ID, derived release/process hashes and window process version identify the actual change; a family-version bump would unnecessarily widen unrelated packet compatibility.

Exactly one graph edge is replaced, one phase inserted immediately before `window_gate`, two escape edges appended, and one prerequisite appended:

```text
read_authority --check_window--> window_readiness --read_authority--> window_gate
window_readiness --request_stop--> stop
window_readiness --ask_operator--> wait_operator
prerequisite: {phase: window_gate, authority: scheduling, fact: slot, expected: S0}
```

The existing operation names already exist. All other edges, operations, prerequisites, waits, approvals and completion remain canonical-byte equal. Besides process identity/version/hash, only its `acknowledgements.reschedule` and `readbacks.reschedule` change to match the new capability contracts. `S0` is an explicit synthetic readiness rule, with no real-world permission implication.

Only capability `reschedule` changes: its version is `synthetic-scheduling-dual-v1`; acknowledgement basis is exactly `synthetic-scheduling-dual-v1: window v2 envelope ack only; exact v1 typed ack`; readback basis is exactly `synthetic-scheduling-dual-v1: bounded original scheduling receipt; out-of-domain unavailable`; both evidence references are `synthetic-scheduling-envelope-v1`, status stays supported and covered fields stay empty. All permission, authority, idempotency, conditional coverage, terminal basis, timeout, evidence mode, account/quota/rate settings remain equal to baseline. Mappings, authorities, policy hash, capability/process key sets and every other process are unchanged. There is no handoff supplement edit.

The complete semantic top-level diff is exactly `capabilities` and `processes`. `_affected` yields exactly old identities `capability:reschedule:v1.1` and `process:reschedule_window:v1`. Review material separately identifies unchanged exact-slot as a consumer of narrowed scheduling-read coverage; it does not invent a changed exact-slot process identity. Hashes are recomputed, never accepted through a hash exception.

### Four real readiness reads and race boundaries

Implement `ActionGateway.read_window_readiness(case_id) -> tuple[AuthorityObservation, ...]` without caller-selected facts, expected values, endpoint, deadline or authentication. Require authenticated engine caller, owner-thread active timing/execution, the exact candidate profile/window checkpoint, original request kind `reschedule_window`, bound versions/deadline, phase `window_readiness`, next gate `read_authority` and no stop. Registered entry calls `self._admission_owner.guard_execution(self._timing.execution, self)` without a control entry kind.

Use `_facts` and existing leases with the identity/owner validators, purpose `window_readiness_identity`, for these three physical operations in existing authority order:

| Order | Operation | Facts |
| --- | --- | --- |
| 1 | `case.read_case` | `case.authorization`, `case.binding`, `case.generation`, `case.request_revision` |
| 2 | `case.read_principal` | `customer.consent_revision` |
| 3 | `operator.read_owner` | `ownership.epoch`, `ownership.owner`, `ownership.state`, `ownership.state_revision` |
| 4 | `scheduling.list_permitted_slots` | `scheduling.slot` |

Wrap the ownership validator to require a strict nonempty owner equal to authenticated `self.auth.caller_id`, plus strict owner state/revision/epoch types, **before settlement**. Do not enable packet reads through `packet=True`. Before operation 4, recheck active binding, phase, next gate, versions, owner state/revision/epoch, stop, original deadline and registered execution. Operation 4 uses `_facts` purpose `window_readiness` and the checkpoint deadline, with no unrelated case/owner validator. Require a fresh scoped string `S0`.

After the final read, recheck the same state and execution. Return all observations; the engine replaces qualified keys in the **latest** checkpoint, retaining all debited budget, then advances to `window_gate` only after successful save. It saves `next_gate=read_authority` before entry. Failure remains at readiness with `processing_status=unavailable`, no physical handoff, no invented operator reply, no intent/generation/deadline creation and no cleared stop. Save failure cannot advance.

These reads are not atomic. Existing full fresh material/policy reread must reevaluate S0 before dispatch, and the provider must enforce S0 for this exact candidate window process beside its existing CAS/source checks. Original-effect readback does not require S0 after a successful reschedule. Do not add consent-mode, request-fingerprint or policy reads to the four-call helper; those remain in the full pre-write path. Preserve each lease's ACL/freshness/pace/reservation/settlement. Full positive execution must fit 24 calls, 120 active seconds and 10 seconds per tool; fit is unmeasured. Raising limits or concealing reads is not an acceptable remedy.

### Real raw source assembly and strict adapter domain

Keep public `SchedulingPort` signatures unchanged. Factor existing world transaction/read assembly into private data-returning helpers so legacy code constructs typed results and candidate code serializes raw UTF-8 JSON bytes directly. Do not dump an already normalized public result. Preserve transaction timing, reservation and idempotency semantics. Raw fault emission, bytes, adapter result and independent final verification are distinct test seams.

All candidate scheduling reads use raw envelopes because `ReadRequest` has no process version. Candidate window dispatch uses raw; candidate exact-slot dispatch remains typed. Legacy profiles remain typed. Exact envelopes require all listed fields (nullable fields are present):

```text
dispatch = {
  contract: "synthetic-scheduling-envelope-v1", http_status: 200|429|503,
  operation: "reschedule",
  body: {status: "acknowledged"|"rejected"|"outcome_unknown"|"business_failed",
         provider_request_id: Identifier|null, evidence_refs: Identifier[], reason: string|null}
}
read = {
  contract: "synthetic-scheduling-envelope-v1", http_status: 200|429|503,
  operation: "list_permitted_slots"|"read_schedule",
  body: {operation: Identifier, object_id: Identifier, observations: AuthorityObservation[],
         provider_request_id: Identifier|null, action_id: Identifier|null, fingerprint: Hash|null,
         stage: Identifier, nonexecution: NonexecutionProof, as_of: Timestamp,
         evidence_refs: Identifier[]}
}
AuthorityObservation = {authority: Identifier, fact: Identifier, object_id: Identifier,
  value: JsonValue, revision: Revision, provider_at: Timestamp|null,
  observed_at: Timestamp, evidence_ref: Identifier}
NonexecutionProof = {status: "unknown"|"proven", basis: Identifier|null, evidence_ref: Identifier|null}
```

Types retain the existing strict public-contract meanings and ISO-aware timestamps; proven nonexecution requires its basis and evidence. Outer operation equals the invoked method; original-effect body operation remains `reschedule`, not `read_schedule`. Every returned identity/time/evidence value is source-owned and preserved, never filled from expectations.

Bounds are inclusive and conjunctive: complete UTF-8 bytes at most 262,144; container depth at most 16 starting with root object depth 1; at most 128 observations; identifiers/revisions/reason at most 1024 Unicode code points; at most 128 **evidence occurrences** across all body references, each observation reference and non-null nonexecution reference, counting repeats. Validate the complete body before emitting a public object. Reject duplicate, unknown or missing keys at every level, nonfinite numbers, numeric/bool/string coercions, invalid UTF-8/JSON, unknown discriminator and wrong operation. These limits narrow candidate reads; they do not change legacy typed contracts.

| Input | Normalization and consequence |
| --- | --- |
| Window dispatch: valid HTTP 200 acknowledged with nonempty provider ID and evidence | Preserve acknowledged fields; independent original read is still mandatory |
| Window dispatch: business_failed, rejected, outcome_unknown, 429/503, non-200 acknowledged, malformed/over-bound/exception | `DispatchResult(outcome_unknown, provider_request_id=None, evidence_refs=[], reason="synthetic_envelope_unresolved")`; retain raw source evidence separately, never fabricate public evidence |
| Candidate read: valid HTTP 200 | Return exact body; existing scope/freshness/fact-set and original-identity verifier decides business result |
| Candidate read: non-200, malformed/over-bound/exception | One bounded adapter contract error; authority path unavailable/scope-denied, original path `outcome_unknown/original_read_unavailable` |
| Legacy or candidate exact-slot dispatch, other dispatch | Existing typed behavior |

A dispatch response never establishes definite candidate window rejection. Only independently joined original terminal proof does. `http200_business_failed` is a new trusted synthetic fault that writes neither effect nor terminal row. Existing window `business_rejection` and `final_rejection_unknown` write the correctly namespaced terminal row. No input-supplied callback is added.

Choosing a finite parser sacrifices complete legacy input coverage. There is no typed fallback, limit relaxation, truncation or observation/effect deletion. Over-bound pre-write data causes no new business dispatch; over-bound post-write readback preserves the possibly committed effect, original key, intent and debt with unknown status and zero resend/undo. Universal parity was rejected because legacy identifiers and JSON can exceed the candidate bounds.

### Window-only original classification within the source

Use existing `effects` and `final_rejections` columns with no DDL. After exact candidate profile/process/operation and current source identity/consent validation, window raw dispatch alone mints:

```text
request_id = "provider:window-envelope-v1:" + fingerprint({
  domain: "synthetic-window-original-v1", account_id, provider_key,
  case_id, object_id, operation, generation, action_id, fingerprint, identity_hash
})
```

All identity values come from the validated intent and provider-selected account; `identity_hash` is the existing fingerprint of the complete serialized intent. Use the full lowercase 64-hex digest. Legacy/exact-slot IDs keep `"provider:" + fingerprint({account, provider_key})[:24]`. Equal-intent repeated keys return their stored ID; a different identity hash conflicts; malformed stored window IDs are not repaired or adopted. Caller-supplied namespace/request IDs are prohibited.

Within the existing immediate transaction and after same-key handling, search **both** tables for the exact minted request ID. Any row with different original join fields or identity hash prevents insertion as a collision/conflict. This is not a uniqueness-index or authentication claim.

Raw original reschedule reads preserve reservation, deadline and reader ACL checks first, then use the same parameterized eight-field join in both tables:

```sql
WHERE account_id=? AND case_id=? AND object_id=? AND operation=?
  AND generation=? AND action_id=? AND provider_key=? AND fingerprint=?
```

Arguments are provider account, request case/object and target operation/generation/action/provider-key/fingerprint. Never search by prefix, latest ID, current slot/consent or caller purpose. Automatic terminal proof requires zero effects, exactly one terminal row, supported terminal contract, strict stored values and exact digest recomputation from joined row fields including 64-hex identity hash. Require aware `created_at <= read time` and preserve final tool-deadline check. Nonunique matches, effect-plus-terminal coexistence, malformed namespace or digest produce unknown/unavailable.

Non-window rows keep the existing `terminal_not_executed` behavior gate. Thus in-domain legacy/candidate exact-slot `final_rejection_unknown` stays unknown without the knob and can expose exact proof with it; candidate window needs no knob. All candidate proofs remain subject to raw bounds. Early unavailable/timeout/business-rejection read faults remain effective. Purpose changes cannot affect classification. The namespace is a trusted-source discriminator, not authentication, a signature or a claim against database tampering.

### Exact trusted semantic registration

Add frozen/slotted `WindowReadinessRegistrationV1` in existing `factory/proposal.py`, with exactly eight fields:

```text
registration_id, provenance, host_factory_key,
baseline_hash, candidate_hash, process_hash, policy_hash, implementations
```

Require exact type (no subclass), fixed first three identities above, strict lowercase hashes, exact frozen baseline and unchanged policy hash, and actual candidate/process hashes. Implementations is a sorted unique exact tuple of exact two-string tuples `(relative_path, sha256)` with the 86 literal names below. No normalized alias, extra field, callable or caller import path. Submitted source is immutable nonempty bytes, at most 1 MiB per file and 8 MiB aggregate. The existing registered-artifact 8 MiB total including all blobs, envelope limits and 2 MiB proposal JSON-material bound remain independent stricter gates.

`FactoryContext.process_delta_registration` defaults to None. Reject coexistence with `implementation_registration` before reading candidate material. Reconstruct a detached frozen registration once; snapshot tuples/bytes under bounds. Explicitly pass the retained registration to every `_material_proposal` call: constructor, `_resolve`, `_proposal_hash`, `prepare_proposal`; check and staging use those reconstructed paths. A new-mode context accepts only this exact delta, never mixed historical/J05 materials. Separate legacy/new contexts may coexist. None and legacy six-file mode preserve literal proposal bytes and all denial rules.

New-mode proposal body includes exactly one `process_delta_registration` object:

```text
{registration_id, provenance, host_factory_key, baseline_hash, candidate_hash,
 process_hash, policy_hash, inventory_sha256, registration_sha256}
inventory_sha256 = sha256(canonical([{path, sha256}, ...]))
registration_sha256 = sha256(canonical(explicit dictionary of the first eight fields))
```

Use sorted registered inventory order, exclude `registration_sha256` from its own hash, retain the independent sorted `adapter_sources` list and bind the full body into `proposal_hash`. Copy the reconstructed exact object into staged manifest; release hash covers that manifest. Never copy a caller packet. Emit no legacy registration key in new mode and no new key in legacy modes. Preserve the existing regression receipt schema and required-case/output, runner/provenance, execution ID/time, baseline/candidate/test/proposal bindings; registration mutation invalidates old evidence.

The semantic matcher admits only the enumerated profile delta plus independently registered source bytes. Source-pin equality alone does not authorize semantics. Lift non-v1 dispatch unavailability only after exact matching and bound execution evidence. Keep staged status, zero-pending admission and other unmet requirements; do not remove activation, resolver, migration, human or timing limitations.

### Existing-file layout and literal implementation closure

`profiles.py` owns fixed identities, the exact compatibility helper, the pure explicit-field window-original request-ID formula and an independent literal J05 tuple. `factory/proposal.py` owns semantic registration; `adapters/scheduling.py` owns private models/decoders; `adapters/world.py` owns raw source assembly. `source_retained_state.py` uses the same pure formula to validate exact-candidate reschedule rows with the full window namespace, retaining the legacy request-ID rule for every other row/profile. The new ID-validation path must import its helper only from profiles, introduce no world import or import cycle, infer no identity from current slot/consent and never repair an invalid persisted row. The pre-existing function-local world import for material-key/revision validation is retained unchanged; moving that separate contract is outside this change. The other existing engine/gateway/host/provisioning files carry their scoped integration. No new package modules or dynamic graph interpreter are introduced, preserving stop-v2's all-package path assertion.

The following **86 path names**, relative to `runtime/src/proofkey`, are copied from the current stop-v2 literal inventory and must be independently written as a sorted J05 literal. This is not an alias, runtime glob or final hash inventory. Keep the stop-v2 tuple and its equality test unchanged. Final J05 source hashes are frozen after implementation and the prior leaf freeze; old historical hashes are not repinned.

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

### Closed provisioning and two evidence groups

Add byte-identical `runtime/profiles/flat-window-readiness-v1.json` and `runtime/src/proofkey/resources/profiles/flat-window-readiness-v1.json`, explicit `pyproject.toml`/`MANIFEST.in` entries and trusted loader name. Extend exact resource inventory tests with its newly derived hash without changing the ten old hashes or fixed fixtures. Negative raw fixtures stay in tests.

Both `_validate_input` and `_revalidate_prepared` use a closed factory-key/profile commitment map: v1 and observed-stop-v2 retain their flat-v1.3 process-v1 behavior; v3 accepts only the new profile and `reschedule_window`. Host composition validates the exact key/process tuple and singleton registry. Trusted candidate exact-slot adapter comparisons do not imply registered exact-slot preparation support. Candidate controls remain denied by key-specific guards even after v2 adds same-owner stop. Versions swapped against current source `window` versus `exact_slot` consent are denied. Non-scheduling v2 operations are accepted only where declared by the exact window process; do not blanket-allow v2 for goods/service.

Evidence group A is **current-source behavior**: exact declared four-read positive within budget; parser/source/identity negatives; default v1 and applicable stop-v2 checks; in-domain exact-slot comparisons, explicit out-of-domain failures, and unchanged goods/other paths. New current-hash compositions are labelled as such. They do not validate historical source pins.

Because the changed source intentionally no longer matches the old six-file qualification fixture, current-source v1 comparisons use a separately named fixed lane and independently frozen final J05 pins outside the package files they hash. The old fixture, literal vectors and default legacy qualifier remain unchanged in meaning: that default rejects changed source rather than silently adopting new pins. Refactored test contexts select the new lane explicitly; the final full discovery must pass without hiding old-pin incompatibility as a skip or a historical positive. Inner qualification suites name exact nonrecursive behavioral modules/test IDs and exclude all outer runner tests. This test-lane split does not expand product factory selection or qualify historical execution.

Evidence group B is **historical pending-state preservation**: an independently identified already-pending original case must remain paired with its actual old executable/source, dependency context, profile/fixture, registration inventory, resource/control identity and supported entrypoints. Record absolute paths, hashes, claim/route IDs, saved keys/versions/postconditions/debts/deadlines, before/after state and every allowed effect/read. No candidate opening/rebinding of those roots, changed deadline, replaced marker/grant, new fixture, repinned route or copied evidence root can substitute.

The available J06 pair is `/private/tmp/proofkey-j06-0yc_36hd/installed-env/bin/python` with original root `/private/tmp/proofkey-j06-installed-80e0d6f-attempt5/probe/library-window/case-feb2ba2f2de14021894506f99484d9c8`. Prior discovery, not this authoring pass, verified 1,733 installed inventory entries and a complete/verified case with no waits. It is a completed-history comparison candidate only; current usability/authority/deadline support is not established. `processing_status=pending` alone is insufficient when phase is complete. Copied retained roots explicitly forbid runtime reuse.

Separate source-leaf completion from the unqualified historical pending claim. A report can complete implementation/current-source obligations and truthfully leave J05 open. Preserve the historical acceptance gate as unfinished; do not turn the absence of evidence into a pass or demand unsupported execution to manufacture it.

## Risks / Trade-offs

- Four extra physical reads may exceed the unchanged full-path budget → measure the complete path; stop and report a fit blocker if necessary, without hidden calls or raised limits.
- Candidate exact-slot/readback coverage is smaller than legacy → disclose the domain, test 1024/1025-character evidence and all other boundaries, keep out-of-domain results unavailable/unknown without fallback.
- A write may commit before an unreadable response → retain original effect/intent/key/debt and prove zero resend/undo on failed original reads.
- Common raw/typed source refactoring can perturb legacy timing or idempotency → independent legacy regressions and source-row comparisons, including terminal knob behavior.
- Same names with changed source bytes invalidate old pins → independent frozen J05 hashes; unchanged historical vectors; no claim from path-name equality alone.
- Existing-file-only layout concentrates code → finite helpers and exact matching constrain the surface while retaining stop-v2 closure.
- No historical pending baseline exists in inspected evidence → historical claim remains unqualified and parent J05 remains open, regardless of current-source success.

## Migration Plan

1. Complete/archive stop-v2; refresh source anchors and validate this child's shared deltas against resulting living specs. Review this change, then write/review a separate Superpowers implementation plan.
2. Implement and test offline in the existing files, stage new candidate resources separately and freeze final source/resource hashes only after review. Never change historical pins to pass current tests.
3. Provision fresh v3 roots for authorized current-source runs. Keep old roots paired with their old executable; no state migration or activation is offered. Withhold v3 selection if the new path fails; preserve diagnostic roots and old state rather than deleting or repinning them.
4. Record separate source qualification and historical-evidence status. Archive only this finite child after its own completed checks; keep unmet parent requirements open. No installation or external release step is included.

## Open Questions

No semantic design choice remains open after revision 3 rereview. Execution questions remain: whether the full four-read workflow fits the unchanged budget; exact final candidate/source hashes after implementation; and availability plus supported usability of an actual historical pending executable/resource pair. The known completed pair cannot resolve the last question. None is answered by this specification or by strict OpenSpec validation.
