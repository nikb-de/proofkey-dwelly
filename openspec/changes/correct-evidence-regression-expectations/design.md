## Context

The current test's narrative iteration passes; its malformed-artifact iteration
returns a generic denial, as required by `fresh-original-intake.md`. Both still
must stay outside prepared processing. An unavailable extractor and denied
access are different conditions.

## Decision

Keep production code unchanged. Create distinct positive and negative tests.
Use real EvidenceCatalog registration for the positive artifact path and for an
artifact whose access is revoked. Use a well-formed unknown ID separately from
a syntactically malformed ID. Recovery of a rejected original must not bypass
its failure or execute the prepared consumer. Assert canonical denial, retained
original identity, zero invocation reservations, zero planner calls and zero
business effects where applicable.

## Non-goals

No permissive fallback, mocked successful intake, new processor, provider call,
source repinning, changed recovery implementation, live server or installation.
