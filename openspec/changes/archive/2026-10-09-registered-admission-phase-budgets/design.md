# Registered admission: two bounded control phases

## Evidence and decision

The preserved probe at
`.superpowers/sdd/2026-10-08-proofkey-runtime/task-13b4b-clock-panel-probe-001-report.md`
used the real engine and stores. A verified reschedule existed while the outer
call returned `timeout`, leaving `binding_sealed` and a reserved route.

The parent contract simultaneously allows full engine execution and caps
control work at five seconds. Interpret the latter as a phase budget. This
clarification does not give the engine or an expired request additional time.

## Invariants

1. The original exact `ExecutionContext`, request, authentication, association
   identity and durable `execution` wire record remain authoritative.
2. Initial preparation/sealing retains the existing original-start five-second
   ceiling; this fix does not relax pre-admission work.
3. Only after the real engine returns, validate the unchanged original parent
   and derive one observation context from the trusted UTC/monotonic clock.
4. Its duration is no greater than five seconds, the original UTC remaining
   budget, or the original monotonic remaining budget. Check backward readings.
5. Share that same phase context through journal capture, source capture, B3
   observation and claim persistence. Nested helpers can clip it, never renew
   it. Recheck the original parent around final publication.
6. Separate identity/parent checks from the ingress-only cutoff. An expired
   parent, changed original context or changed resource association still fails.
7. Any late failure retains actual effects, imported debt and pending claims.
   Never retry engine execution, fabricate observation, clear debt or repair a
   partially committed result.

## Implementation boundary

Use a small internal phase-derivation helper and explicit shared phase plumbing
in `RegisteredAdmissionOwner.run`. Keep public APIs and durable schemas stable.
Do not change `ExecutionContext` semantics or copy new anchors into the durable
claim. Existing `_ClaimStore.operation` can consume the phase context and keep
its existing finite transaction checks.

## Verification

Real-component regression: time the engine beyond five seconds but below the
parent cap; assert returned verified outcome, one effect, observed route/claim,
unchanged original timing and no pending-claim reopen blocker. Negative tests:
parent expiry, final phase exhaustion, changed context, backwards clock, and
combined phase work exceeding five seconds despite shorter individual steps.
Preserve RED then GREEN output. Run the module and full runtime suite; list the
seventeen known baseline failures explicitly if still present. A red full suite
does not become green because this narrower fix passes.
