# Existing-parent processing composition

9 October2026. Internal12B4a prerequisite of the approved Task12 engine integration, not a processing recipe, content consumer or provider enablement. Exact THREE: existing runtime/src/proofkey/gateway.py, existing runtime/src/proofkey/providers/invocations.py and NEW runtime/tests/test_processing_parent_scope.py. Implementation GO follows the13B1 independent gate and exclusive handoff of every actual shared dependency. Journal/schema/engine/catalog/clients/planner/contracts/profiles/source/old tests/helpers/package remain unchanged.

## Intent and chosen boundary

The engineer must be able to compose a durably charged processing role inside the engine's existing creator-owned gateway/journal execution scope. Ordinary InvocationService.call(execution=original) would nest that journal scope; calling it with execution=None would lose the service's original monotonic cap. Add verified parent composition, without splitting run/recover/reply or calling a private invocation implementation from the consumer.

Borrowing timing grants no customer, source, campaign, role, retry, privacy or effect permission. Existing independent reservation, campaign/identity/original/stop/ownership checks and all debt rules remain mandatory. Parent is trusted construction, never a request/body/attachment/model-output choice. Tests are synthetic; native participation and actual model/media quality remain unqualified.

## Exact additive public interfaces

```python
class ActionGateway:
    def processing_parent_timing(self, *, store, clock) -> ExecutionTiming: ...

class InvocationService:
    def __init__(self, case_id, store, clock, campaign, processor_identity, *,
                 worst_case_cost=None, invocation_id_factory=None,
                 parent_gateway=None): ...

    @property
    def parent_gateway(self): ...  # constructor-bound object or None; no setter

    def call_in_parent(self, role, input_hashes, usage_ceiling, invoke) -> ProcessingReceipt: ...
```

Unconfigured services preserve ordinary call(execution=...) and legacy call(execution=None) exactly. A parent-configured service requires call_in_parent; ordinary call rejects before ID construction or debit rather than silently selecting an unscoped fallback. call_in_parent has no execution/Timing/already_scoped/boolean/token argument. Parent-configured construction requires the exact existing ActionGateway type, identical public store/clock objects and a detached fixed private association; no mutable parent setter or constructor alias dictionary. Reject bad associations before DB/source access. An inactive parent is valid configuration but cannot perform a call.

processing_parent_timing verifies its actual creator thread, active execution scope, same store/clock identity, and its exact currently installed ExecutionTiming with the original clock/context. Return that same timing object, not a clone or a new ExecutionContext.capture. An explicit original context must still have time remaining; legacy execution=None may return only the parent's already installed legacy timing, with no new monotonic guarantee. This accessor never opens a journal scope and is not authentication or a transferable entry handle. A retained returned timing does not bypass the service's fresh parent validation.

## Service-owned lifetime and continuous checks

call_in_parent requires the service's creator thread and existing nonreentrant lock before mutable current-request/timing state. Verify the fixed parent/store/clock association and actual active timing before invocation ID creation or any debit. The service owns delegation to its existing _call_in_scope; no consumer calls that private method.

Keep a task-private zero-argument parent verifier for this invocation. It asks the fixed gateway accessor for the current timing and requires object identity with the first captured parent timing, plus unchanged constructor-associated service store/clock. Verify before request setup, immediately before reservation, immediately after reservation/before callback, in processing_context before creating a usable context, after callback before validation/publication of a completed receipt, and before returning the saved result. A parent exit or exit/reentry with a different timing during the callback denies; it cannot renew the original window or return a usable successful receipt. No new public verifier callback or scope flag is accepted from callers.

Reuse existing request/permit construction, durable reservation, remaining committed lease calculation, observed elapsed settlement, receipt identity/usage/output validation, saved receipt readback and interruption behavior. Explicit original UTC/monotonic context includes setup and callback/context construction. Expiry after debit but before callback preserves consumed unknown debt with zero processor entry; expiry after processing cannot refund it. Unknown recording/necessary local cleanup remains possible after time exhaustion, as in the existing service. No automatic new attempt, campaign registration or role funding follows.

On every exit clear all service current request/owner/started/timing and private parent-verifier state, release its lock, leave the outer gateway and journal scope under their original owner, and preserve ordinary surrounding operations/restoration. Invalid parent/timing/association is a finite safe JournalFailure, not a raw object/data dump. Same-service recursion and recursive engine/gateway entry remain rejected by their existing independent guards. These are cooperative trusted-Python composition rules, not a sandbox against arbitrary private-field manipulation or a hard OS cancellation promise.

## Behavioral TDD obligations

Own task-local synthetic fixtures; do not invoke old unittest methods, weaken old tests, use real resource DBs or introduce a production callback hook. Through the public gateway scope and service entry prove:

1. Positive explicit original context: actual reservation precedes callback, public processing_context is constructed after reservation, returned exact receipt is durably saved, original monotonic elapsed/deadline/lease/debt are retained and the outer scope remains usable. Instrument the real store in the NEW test only to show exactly one scope installation, not a nested attempt.
2. Default unconfigured standalone explicit and legacy calls remain lawful. Parent configuration is fixed/no setter; bad/custom/foreign/inactive/exited/changed-store/changed-clock/wrong-thread parents deny before ID factory/callback/debit. Configured ordinary call and forged extra Timing/execution/flag keywords cannot select a fallback.
3. Setup and UTC-observation consume the original slice. Shortened positive context timeout is real; expiry immediately after reservation while overall host still has time prevents processor entry and retains debt/unknown. No capture/anchor/allowance renewal is performed.
4. Callback exception/invalid receipt/nonfinite or reversed clock/late completion retain consumed usage and restore the service. Parent exit and exit/reentry during callback cannot yield completed usable output. Test a subsequent valid separate scope/call to distinguish rejection from a leaked lock/owner state.
5. Public processing_context outside an owned reserved callback denies; same-service callback recursion and recursive engine/gateway entry deny; stopped or ownership-fenced reservation never enters. Existing original binding, campaign input set, usage/cost ceilings and fresh-only role funding remain enforced.

One final named cohort includes all new parent tests and a small root-selected set of unchanged invocation/execution/admission controls. Freeze actual late imported/opened source/data/private observer union including new retained_state.py/schema.sql, acquire current PRE/POST holds and root finalGO, preserve complete original failed/passed outputs. Root proportional checks, exact-three commit and DIFFERENT NONAUTHOR separate Spec+Quality gates precede the engine consumer. No repeated full API/V2/driver cohort is required solely for this composition foundation.

## Explicit downstream exclusions

Constructor recipe and independently registered exact permits, complete original content selection/ACLs, extraction-to-V2 planning, source-authorized suggestion conversion, structured-only engine integration, current-binding processing summary/disclosure, host activation, media/transcription and durable entry-local unavailable/replay disposition remain separate unfinished stages. No implicit campaign hash generation from fixture membership, public raw evidence export, refund, profile/process rewrite, fresh grant, provider/network/server/install/spend, human/coding provenance or wholecandidate/readiness claim.
