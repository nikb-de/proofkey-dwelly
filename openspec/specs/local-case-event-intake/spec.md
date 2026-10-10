# local-case-event-intake Specification

## Purpose
Accept bounded local case information as immutable, replay-safe revisions while keeping analysis, identity verification and operational authorization explicit and separate.

## Requirements
### Requirement: Revisioned local input
The service SHALL accept closed bounded JSON case declarations and events over its existing authenticated local HTTP boundary, persisting immutable canonical snapshots in its private SQLite database. Declared links SHALL NOT be runtime bindings or authentication evidence.

#### Scenario: Create and append
- **WHEN** an authenticated operator creates a valid English-labelled local case and appends a valid event at its current revision
- **THEN** revision advances exactly once, the prior snapshot remains retrievable, and the new snapshot has a new hash and pending-not-started analysis status

### Requirement: Atomic replay and conflict handling
Case/event requests SHALL require idempotency keys. Exact retries SHALL return their original committed snapshot. Changed bodies, duplicate event IDs under another key and stale expected revisions SHALL fail without changing state.

#### Scenario: Concurrent append
- **WHEN** two different events race with the same expected revision
- **THEN** at most one is committed and the other receives a revision conflict

### Requirement: No inferred execution or authority
Every response SHALL disclose local-fixture provenance, no runtime binding, unverified authorization and zero operational effects. Intake SHALL NOT invoke model providers, jobs, runtime, adapters or media extraction.

#### Scenario: New information
- **WHEN** a message, photo, voice or call metadata event is appended
- **THEN** its new immutable revision is pending analysis and no provider call or operational action is reported or performed

### Requirement: Bounded metadata and safe readback
Inputs SHALL validate participant references, English declaration, aware source timestamps, event-specific fields and media limits; unsupported fields including fetch URLs and filesystem paths SHALL fail closed. Persisted readback SHALL validate schema and content hash.

#### Scenario: Unsafe or corrupt input
- **WHEN** the event is oversized, references a foreign participant, contains unsupported media fields or persisted content is malformed
- **THEN** the service returns a bounded error without exposing raw input or claiming a usable snapshot

### Requirement: Preserve existing service behavior
The existing fixed-bundle jobs, explicit live opt-in, local ownership and cloud refusal SHALL remain unchanged.

#### Scenario: Intake without model execution
- **WHEN** the service records input without live opt-in
- **THEN** existing job counts, provider budget and runtime state remain unchanged
