## ADDED Requirements
### Requirement: Durable coordination commands
The local platform SHALL atomically persist versioned coordination commands and an internal canonical-case audit event. Every mutation SHALL require current source revision/hash, workflow version and a body-bound idempotency key. Existing case APIs SHALL remain compatible.
#### Scenario: Concurrent acceptance
- **WHEN** two commands use the same workflow version
- **THEN** at most one distinct command is admitted and exact idempotent replay returns the original result
#### Scenario: Oversized audit
- **WHEN** a valid command's complete audit would exceed the canonical event text limit
- **THEN** the platform returns `coordination_audit_too_large` and changes neither the aggregate nor the case head

### Requirement: Cancellation and replacement terms
The platform SHALL distinguish cancellation request from confirmation, preserve complete versioned terms and require explicit recipient acceptance before a booking request. Dispatch and recipient evidence SHALL be source-bound and declared-identity checks SHALL NOT be described as authentication.
#### Scenario: Counteroffer changes
- **WHEN** a replacement offer changes date, handover or charge
- **THEN** prior acceptance is invalidated and no booking request may use it

### Requirement: Confirmed coordination outcome
The platform SHALL mark a booking confirmed only on a correlated Dispatch readback after its request, and SHALL continue to describe physical delivery as unconfirmed.
#### Scenario: Request sent
- **WHEN** a booking request is recorded without its correlated confirmation
- **THEN** coordination remains booking_pending with zero external effects
#### Scenario: New case information
- **WHEN** the canonical head moves beyond the last coordination audit
- **THEN** the case projection marks coordination freshness as stale without erasing its historical phase or claiming a current resolution

### Requirement: Honest scenario and model evidence
The scenario adapter SHALL preserve frozen source provenance, exclude authored expected states and future events from inference, label any date or directory adaptation, and retain source facts. Model configurations SHALL keep historical baselines separate from current candidates.
#### Scenario: Historical source
- **WHEN** a future-dated executable demo is prepared from the February source
- **THEN** the derivative records its date transformation and does not mutate the original source or weaken future-slot admission
#### Scenario: Inconsistent final readback
- **WHEN** the scripted backend replay's final GET disagrees with the last command receipt
- **THEN** the replay fails instead of producing a success receipt
