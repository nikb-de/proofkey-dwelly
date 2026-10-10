## ADDED Requirements

### Requirement: Create and extend local cases
The workbench SHALL create backend-shaped case declarations and append participant-scoped events with immutable zero-based revisions in a separate versioned browser database. It SHALL preserve the supplied simulator, brand assets and original state.

#### Scenario: Case survives reload
- **WHEN** a valid local case and event are committed and the page reloads
- **THEN** the same declaration, revision and event remain available without a claimed model result or operational effect

### Requirement: Real bounded attachment intake
The workbench SHALL read actual selected bytes, validate allowed type/size, compute a content hash, display image preview and persist committed attachment Blobs. Invalid or unavailable bytes SHALL NOT be marked ready or analysed.

#### Scenario: Invalid photo
- **WHEN** an empty, oversized, unsupported or undecodable image is selected
- **THEN** a specific recoverable error is displayed and it cannot become committed photo evidence

#### Scenario: Stored attachment
- **WHEN** an allowed photo is committed and the page reloads
- **THEN** the preview and verified local hash are recoverable while processing remains not_started

### Requirement: Clear local-only authority
Every workbench view SHALL disclose local storage and pending analysis. Upload, parsing, acknowledgement and operational success SHALL NOT be conflated.

#### Scenario: New evidence is saved
- **WHEN** the operator saves evidence
- **THEN** the UI says it is saved locally, with unverified authority and no operational effects
