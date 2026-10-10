## Context

The current test's narrative iteration passes; its malformed-artifact iteration
returns a generic denial, as required by `fresh-original-intake.md`. Both still
must stay outside prepared processing. An unavailable extractor and denied
access are different conditions.

## Decision

Keep production code unchanged. Create distinct positive and negative tests.
Use real EvidenceCatalog registration for the positive artifact path and for an
artifact whose access is revoked. Use a well-formed unknown ID separately from
a syntactically malformed ID. Fresh run must return canonical denial. Existing
recovery deliberately does not perform original intake: it may return an
authorized case observation with media/processing unavailable, but must not
read the rejected artifact, invoke prepared processing, expose evidence or
execute business effects. Case authorization is not evidence authorization.
Assert retained original identity, zero invocation reservations, zero planner
calls and zero business effects in both paths.

## Non-goals

No permissive fallback, mocked successful intake, new processor, provider call,
source repinning, changed recovery implementation, live server or installation.
