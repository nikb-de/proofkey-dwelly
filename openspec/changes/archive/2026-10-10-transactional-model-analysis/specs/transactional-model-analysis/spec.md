## ADDED Requirements

### Requirement: Evidence-only model proposals
The model SHALL receive only the selected evidence projection and SHALL NOT receive author references or authority to execute business actions.
#### Scenario: Invalid proposal
- **WHEN** a model invents an actor, evidence ID or unsupported action
- **THEN** the host rejects the candidate without substituting a successful baseline

### Requirement: Atomic model admission
Job submission, idempotency binding and conservative budget reservation SHALL commit atomically in PostgreSQL.
#### Scenario: Concurrent identical submissions
- **WHEN** clients submit the same key and frozen specification concurrently
- **THEN** they observe one job and one reservation

### Requirement: Conservative dispatch recovery
The system SHALL persist dispatch before transport and SHALL NOT automatically replay a possibly dispatched provider request.
#### Scenario: Crash after dispatch
- **WHEN** a lease expires without a durable provider response
- **THEN** the job becomes outcome_unknown and retains its reservation without another provider invocation

### Requirement: Durable visible analysis lifecycle
The UI SHALL show model-job state, candidate state and provider receipt as distinct facts and ignore stale polling responses.
#### Scenario: Selection changes while running
- **WHEN** a user selects a different case, step or profile
- **THEN** the old result does not replace the new selection and no cancellation or successful external action is inferred
