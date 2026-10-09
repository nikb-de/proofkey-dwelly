# Common execution-window implementation refinement

9 October 2026. This closes internal implementation seams of approved Task10's common finite library/CLI/API/batch pipeline; it introduces no business operation, wire authority, native integration or live enablement. Parent written design and sixteen-task execution were approved by the user. This refinement was inspected by root against those requirements; it is not a claim that the user reviewed this newly written artifact, nor a runtime receipt. Implementation remains gated on the complete C2 consumer review and source8B fix review.

## Fixed boundary

One trusted-host immutable `ExecutionContext.capture(cutoff, clock)` object is reused across cases/retries/control within a host execution. Its cutoff excludes host export reserve. Source bodies/models never supply context/deadline/permission. `execution=None` preserves finite legacy behavior and clocks without monotonic methods. Already Approved Task10A storage scope caps both durable leases and reserved slices; this stage adds end-to-end consumer pacing/transport/settlement enforcement without changing storage/schema/wire models.

Six files only: existing engine.py, gateway.py, replay.py and providers/invocations.py; new execution_consumer.py and test_execution_context_consumers.py. Adapter/source/profile/policy/verifier/wait/ownership/store/export/factory/assessment interfaces are unchanged. No high-level transfer entry until its separately reviewed ownership lifecycle is available.

## Additive host APIs

```python
WorkflowEngine.run(request, auth, *, execution=None)
WorkflowEngine.recover(case_id, auth, *, execution=None)
WorkflowEngine.reply(reply, auth, *, execution=None)
WorkflowEngine.stop(case_id, generation, auth, *, execution=None)
ActionGateway.execution_scope(execution=None)
ReplayService.lookup(request, auth, *, execution=None)
InvocationService.call(role, input_hashes, usage_ceiling, invoke, *, execution=None)
```

Exact ExecutionContext or None only; no body join flags or thread-local/global authority. Existing return types remain. Context-aware clock must provide aware UTC now(), finite monotonic() and bounded wait(). Invalid/wrong-thread/recursive/expired public entry denies before auth/controller/journal mutation.

`ExecutionTiming(clock, execution)` is a frozen host-only companion for current window(deadline), remaining_seconds(deadline), monotonic_anchor() and elapsed_since(anchor). It wraps approved timing arithmetic, not a grant/receipt. Consumers never query private store execution state or SQL to obtain timing.

## Owner scope and composition

Engine guard runs first. It enters the SAME injected gateway's creator-thread/nonreentrant scope, which enters approved store.execution_scope ONCE if a context exists and yields its explicit timing companion. Timing and scope-active state restore in finally. With an explicit ExecutionContext, prior auth also restores in finally, including errors/crashes. With default None, retain the legacy gateway's last supplied AuthContext after public engine entry, including ProcessCrash; existing trusted-host direct gateway calls depend on that behavior. This compatibility exception does not supply or derive proof, bypass fresh source checks, permit cross-thread/reentrant use, or enable the future host to omit its per-command external proof resolution and explicit execution context. Scope entry validates timing/ownership, not yet caller auth; physical paths still perform their existing source-authentication gates. Default None must not reject a fresh engine merely because no gateway auth was installed before its first run.

Standalone replay/invocation public entries own a creator-thread scope and share the same bodies with explicitly private in-scope engine composition. Engine passes the yielded timing companion explicitly to replay's private body; it never reads mutable private gateway/store timing. No public already_scoped flag or reentrant exemption. A different public recursive entry still denies.

The immutable saved case/intent horizon is distinct from the ephemeral host cap. Do not pass a short host cutoff to the old saved-horizon admission check and reject a valid saved case merely because its historical deadline is longer. New admission can tighten its durable deadline through approved storage accounting; saved cases/results/intents remain byte-identical, with current physical leases constrained instead.

## Physical transport sequence

Current original/source/permission checks → compute current cutoff → full required pacing if it fits → resample cutoff → durable reservation → resample/clamp lease/transport deadline immediately before port/provider entry → at most one physical invocation → classify/settle conservatively → lawful local outcome recording.

Full declared account pacing must fit both UTC and captured monotonic allowance. Never clip delay and dispatch early. Resample after waiting and after storage/lease/request construction; expiry consumes no new source entry. After an already committed reservation, expiry means zero subsequent port call and retained debt/dispatching-unknown state, not fabricated nonexecution/rejection or a free retry. Customer/operator wait expiry remains separately enforced by the Approved C3 path and cannot be replaced or extended by host timing.

Every read uses the existing admission/control/ordinary/original reservation selection. Outbound ReadRequest deadline is min(current cutoff, exact original/current scope, committed lease); gateway effects likewise include tagged wait expiry. No callback rebuild, altered content/key, budget reset or new ownership grant. Original readbacks cannot begin after expiry.

Replay still requires current scoped disclosure proof/binding/ACL and returns the exact historical result/as-of/generation only if that read is lawful. No expired public entry discloses saved details. A backwards UTC shift may deny evidence but never restore elapsed allowance.

## Elapsed/debt rules

Context-aware transport captures a monotonic anchor immediately before public reservation; it conservatively includes lock/commit/setup time rather than inventing a monotonic start from a persisted UTC lease. Known timely completion can settle actual measured duration; unknown/invalid/throw/interruption/failed finalization retains full slice. Reversed/nonfinite elapsed rejects without refund. An overrun cannot initiate readback or be described as on-time success. Factual already-verified evidence is not erased just because later local finalization runs past a scheduling cutoff; the future host/batch records actual finish/overrun separately.

Default None preserves existing gateway/replay measurement behavior and existing invocation monotonic checks. No SystemClock or native cancellation is claimed here. Hard exit preserves predebit; reopening never recaptures a free execution context for the same host run.

InvocationService retains actual permit/role/input/identity/cost scope and simulated-only route. Check creator thread before lock/ID/request/context work; after reservation recheck before invoke(). processing_context timeout uses min(current host remaining, immutable lease remaining, reserved slice minus monotonic elapsed). Expired post-reservation preserves unknown/charges with no callback. Actual provider/engine evidence-planning enablement is a different gate.

## Required evidence

Behavioral tests must cover all four public engine entries before auth, new/saved short horizons, reused context/sequential cases, full-delay pacing exhaustion/delayed UTC, after-real-reservation expiry with zero port entry, exact historical replay/current ACL, reply/control/original scope, backwards UTC/monotonic debt, scope restoration/thread/reentry, and real simulated processing timeout/permit reservation. Keyword/import absence is scaffolding, not behavioral RED. Genuine subprocess crash receipts are distinct from deterministic clock injection and timed drills.

Exact six-file author report/diff plus independent nonauthor spec+quality review is required. Named source/test/data manifests are explicit snapshots, not complete environment closure. FullTask10/M1 additionally needs host clock/creator-thread dispatcher/queue, approved auth/profile registry, library/CLI/API parity, every-input batch inventory/export reserve/manifest and ownership transfer command; no such completion follows from this refinement.
