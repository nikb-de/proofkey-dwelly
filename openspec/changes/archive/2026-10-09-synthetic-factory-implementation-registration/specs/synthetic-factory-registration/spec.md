## ADDED Requirements

### Requirement: Historical identity remains immutable

The factory SHALL retain its historical default source pins and canonical
proposal/staging recipes when no explicit implementation registration is given.

#### Scenario: Existing caller supplies current source bytes without opt-in
- **WHEN** current bytes differ from the historical pins and registration is None
- **THEN** the factory SHALL deny unsupported_adapter_implementation
- **AND** no historical receipt SHALL be relabeled as current qualification

### Requirement: Only trusted host configuration selects explicit source pins

An optional registration SHALL be an exact immutable synthetic host value with
exactly six required paths, independently fixed SHA-256 pins, bounded identity
and bytes. Case packets and generated proposals SHALL not select it.

#### Scenario: Malformed or drifting material
- **WHEN** registration types, names, hashes, bounds or submitted source differ
  from the explicit host contract
- **THEN** admission SHALL deny before executing behavioral regressions

### Requirement: Registration provenance binds all generated artifacts

Explicit registration identity, provenance and canonical inventory digest SHALL
be bound into proposals and staged manifests and used consistently throughout
preparation, resolution, regression checking and staging.

#### Scenario: Reuse across registration identity
- **WHEN** equal source bytes have different registration IDs
- **THEN** proposals SHALL have different hashes and cross-registration
  regression/review receipts SHALL not be accepted

### Requirement: Current synthetic evidence matches observed execution

Current tests SHALL use fixed expected pins independently of submitted material
and verify imported source identity before producing behavioral receipts.
Evidence SHALL describe its actual observed source/dependency scope, not claim
a complete runtime closure or production qualification.

#### Scenario: Execution preflight is not trustworthy
- **WHEN** Python assertions are disabled, selected tests are omitted or skipped,
  or executing project-local modules do not match the recorded source inventory
- **THEN** the lane SHALL NOT emit a successful current-source qualification
- **AND** the source inventory SHALL include new executing files regardless of
  their Git tracking state

#### Scenario: Current synthetic control completes staging
- **WHEN** all existing control checks and explicit source binding pass
- **THEN** the result SHALL remain staged_simulation with unmet requirements
- **AND** activation, migration, actual review, changed-process dispatch and
  timed-adaptation completion SHALL remain unavailable or unestablished
