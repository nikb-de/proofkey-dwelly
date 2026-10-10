## ADDED Requirements

### Requirement: One durable case workspace
The platform SHALL list, create and append evidence to canonical PostgreSQL cases through a same-origin local API and show the same state after refresh. Existing v1 snapshots SHALL remain unchanged in meaning.
#### Scenario: Append then refresh
- **WHEN** an operator appends an event at the current revision
- **THEN** one new immutable revision and analysis intent are committed and visible after refresh

### Requirement: Independent state axes and immutable decisions
Lifecycle, evidence, analysis, decision and action SHALL be independent projections. Every decision and review SHALL bind to case ID, revision and snapshot hash. New evidence SHALL prevent old approvals from admitting a new action, without deleting historical results.
#### Scenario: New evidence after approval
- **WHEN** a new case revision arrives before execution
- **THEN** execution of the approved previous-revision decision is rejected as stale

### Requirement: Explicit deterministic and model boundaries
Deterministic analysis SHALL record checks and missing information, not impersonate a model. Optional model jobs SHALL receive evidence only, retain provider receipts, and never fabricate evaluation references or confer execution authority.
#### Scenario: Model completes
- **WHEN** a model job succeeds for a user-created case
- **THEN** its candidate is visible as a model proposal and neither a business effect nor case completion is inferred

### Requirement: Human-gated transactional sandbox actions
Only same-address delivery rescheduling SHALL execute, in a clearly labeled local PostgreSQL sandbox. It SHALL require a current revision, valid future bounded slot, visible source evidence and explicit operator approval attesting customer consent. Returns, refunds and address changes SHALL be escalated or blocked. Replay SHALL return the original sandbox result.
#### Scenario: Duplicate execution
- **WHEN** an approved reschedule is executed twice
- **THEN** one sandbox booking and one immutable receipt exist, with zero external business effects

### Requirement: Private media and honest readiness
The platform SHALL store bounded signature-checked image/audio bytes privately with computed hashes and case binding. Media upload SHALL NOT imply extraction, transcription, authenticity or authority. Retrieval SHALL require the local trusted origin boundary and never interpolate arbitrary filesystem paths.
#### Scenario: Invalid media
- **WHEN** an uploaded image has an unsupported MIME or invalid signature
- **THEN** it is rejected and cannot become case evidence

### Requirement: Product UI and truthful integration state
The primary UI SHALL provide cases, evidence, decisions, review queue, history and integration readiness, with evaluations as a separate destination. It SHALL distinguish local sandbox, unavailable providers and unimplemented live integrations.
#### Scenario: Missing model credentials
- **WHEN** no configured provider has a usable credential
- **THEN** local case operations remain usable and live analysis is unavailable rather than simulated as success

### Requirement: Explicit media processing and validation
The platform SHALL offer photo-analysis and ASR controls separate from upload. Processing SHALL validate bytes and content limits, persist immutable source-bound results and provider receipts, require human review of extracted content, and never silently append model output as customer testimony. Synthetic image generation SHALL remain separate from operational evidence.
#### Scenario: Media processing outcome
- **WHEN** a photo or audio file is analyzed through an explicitly configured provider
- **THEN** its source hash, processing mode, validation and result status are recorded independently from the case decision
#### Scenario: Uncertain media dispatch
- **WHEN** a provider request may have been sent but no reliable result is available
- **THEN** the record is outcome_unknown and the service does not automatically resend it
