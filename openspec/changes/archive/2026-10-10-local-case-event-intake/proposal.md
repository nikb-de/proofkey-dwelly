## Why

The team selected a local pseudo API instead of a real CRM. Relationships currently come from JSON; new messages must invalidate the prior evidence view. The existing service only accepts jobs over a fixed imported bundle. Add durable revisioned input without claiming that a model or operational workflow has processed it.

## What Changes

- Add authenticated local case creation, event append and immutable revision retrieval to the existing service.
- Keep declared order/customer/operator links separate from verified runtime identity.
- Record every revision as pending analysis; do not silently invoke a model, enable spending or mutate runtime.
- Accept bounded English-labelled message/photo/voice/call metadata, not media bytes or arbitrary fetch URLs.
- Add private environment configuration and a tracked empty template; keep current explicit shell loading and CLI flags.

## Capabilities

### New Capabilities
- `local-case-event-intake`: durable, optimistic-concurrency, no-effect local case input.

## Impact

Only the local service and its SQLite schema gain input records. Existing job submission, fixed bundles, runtime policies, adapters and model schemas remain unchanged. Rescheduling is the first subsequent sandbox action; policy learning, typed planning, media extraction and cloud deployment are not delivered by this increment.
