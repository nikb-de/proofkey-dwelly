# case-model-e2e Specification

## Purpose
TBD - created by archiving change case-model-e2e-controls. Update Purpose after archive.
## Requirements
### Requirement: Leakage-free authored case replay
The E2E tool SHALL replay existing source cutoffs through the canonical platform API while preserving goal, visible actor descriptions, messages and source provenance separately from expectations. It SHALL NOT provide future events or authored answer labels to the model.
#### Scenario: Negative branch before confirmation
- **WHEN** a cutoff precedes address-desk confirmation
- **THEN** later confirmations and completion labels are absent from the model input

### Requirement: Independent semantic and operational checks
The evaluator SHALL distinguish coordination-state assertions from durable execution checks and SHALL NOT mark missing model output as a pass. Scripted results SHALL NOT count as live semantic evidence.
#### Scenario: Premature completion
- **WHEN** a candidate claims completed before supporting confirmation
- **THEN** the completion check fails even if its JSON and transport are valid

### Requirement: Durable bounded model E2E
The runner SHALL use real HTTP, case revisions and PostgreSQL model jobs with explicit provider mode, frozen hashes, bounded polling, idempotency and retained result receipts. It SHALL NOT automatically resend an uncertain provider request.
#### Scenario: Lost acknowledgement or reload
- **WHEN** the original request is replayed or observed after reload
- **THEN** the same durable job is returned without a second dispatch

### Requirement: Current-state and work monitoring
The platform UI SHALL show model coordination state separately from transport and business state, with waiting target, proposed action, revision binding and dispatch metadata. It SHALL observe nonterminal work by read-only polling and never infer action authority from model completion.
#### Scenario: New evidence after a model result
- **WHEN** the current case revision advances
- **THEN** the old result is visibly stale and cannot mark the new case resolved

### Requirement: Truthful coverage and credential boundaries
Reports SHALL identify source independence, mode, requested/observed provider, checks and failures. Missing credentials SHALL produce explicit unavailable status; keys SHALL stay outside reports and version control.
#### Scenario: No provider key
- **WHEN** live preflight reports missing credentials
- **THEN** no model request is dispatched and the report does not claim live E2E success
