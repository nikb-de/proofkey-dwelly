## ADDED Requirements

### Requirement: Pinned development sources
The system SHALL preserve the supplied source JSON, verify hashes and keep related branches in one development family. Author annotations SHALL remain unvalidated references.

#### Scenario: Shared positive and negative source
- **WHEN** case002 and its N4 branch are exported
- **THEN** both share one independence group and neither is represented as unseen test data

### Requirement: Evidence-only step input
The system SHALL isolate visible transcript evidence from authored state, future messages and evaluation references, with an exact step-bound input hash.

#### Scenario: Reference changes
- **WHEN** only the author's explanation or expected state changes
- **THEN** the earlier evidence projection and its inference result remain unchanged

### Requirement: Local bounded analysis
The system SHALL offer a loopback-only offline analysis interface, fixed source registry and immutable run artifacts, without exposing credentials, making model calls or granting operational authority.

#### Scenario: Ambiguous channel outcome
- **WHEN** visible evidence reports an unknown outcome of an attempted change
- **THEN** the supported baseline requests readback or abstains, never asserts non-execution or repeats the change

### Requirement: Honest separate UI
The UI SHALL distinguish source assertions, inference, references and actual execution; untrusted imports SHALL be bounded and a rejected import SHALL preserve the last valid view.

#### Scenario: Invalid or deep source
- **WHEN** an import fails validation or rendering bounds
- **THEN** the previous valid source stays selected and no completed operation is invented
