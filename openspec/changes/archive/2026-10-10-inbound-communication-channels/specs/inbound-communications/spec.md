## ADDED Requirements

### Requirement: Bounded source normalization
The platform SHALL normalize versioned email, message, transcript and media envelopes without URL retrieval, text truncation or implicit media processing, preserving source provenance outside the unchanged canonical v1 contract.

#### Scenario: Email and phone ingestion
- **WHEN** an operator imports a supported email or an authenticated connector provides a transcript or recording
- **THEN** original source provenance is retained and validated content is eligible for case promotion
- **AND** recording storage is not reported as transcription or analysis

#### Scenario: Malformed content
- **WHEN** content exceeds limits, has malformed MIME or unsupported media
- **THEN** a bounded quarantine reason is retained and no canonical event or asset is partly committed

### Requirement: Trusted routing and durable idempotency
The system SHALL use configured conversation and participant mappings, durably deduplicate connector deliveries, and atomically append source events and assets with a final receipt.

#### Scenario: Missing mapping
- **WHEN** a conversation, case or contact is unknown
- **THEN** the delivery is quarantined without adding participants, creating a case or granting authority
- **AND** an explicit retry may promote it after trusted configuration is corrected

#### Scenario: Replay and conflict
- **WHEN** the same connector delivery identity and content is repeated
- **THEN** the existing receipt is returned with no duplicate events
- **WHEN** that identity is repeated with changed content
- **THEN** the delivery is rejected as a conflict

### Requirement: Local authenticated transport and truthful controls
The system SHALL provide an opt-in HMAC-authenticated loopback listener and trusted-local-operator imports, distinguish harness readiness from provider connectivity, and expose durable receipt states in English.

#### Scenario: Invalid signature
- **WHEN** a webhook signature is absent, incorrect or expired
- **THEN** it is rejected before parsing or inbox storage

#### Scenario: No implicit paid or business action
- **WHEN** inbound content is accepted
- **THEN** no LLM, ASR, outgoing communication, call or operational action is dispatched automatically
