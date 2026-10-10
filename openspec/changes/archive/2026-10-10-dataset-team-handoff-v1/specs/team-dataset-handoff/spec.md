## ADDED Requirements

### Requirement: Canonical and private evaluation records
The dataset kit SHALL keep model inputs in the unchanged canonical v1 schema and SHALL keep labels, detailed criteria, manifests and episodes evaluator-only.

#### Scenario: Model input has an injected label
- **WHEN** a model-visible input includes evaluator fields
- **THEN** structural validation fails

### Requirement: Reproducible offline validation
The kit SHALL include a standalone offline validator for schemas, source/hash identity, immutable revision history, references, split isolation, safe file paths and annotation status.

#### Scenario: Related source moves into another split
- **WHEN** the same family, case or source is declared in both development and test
- **THEN** validation fails even when individual rows conform to JSON Schema

### Requirement: Honest synthetic examples and collection instructions
The kit SHALL identify synthetic examples as unreviewed development material and SHALL explain collection of independent evaluation cases and authorized redacted real-case snapshots without treating them as live operations.

#### Scenario: Unreviewed seed is supplied
- **WHEN** a colleague validates the bundled seeds
- **THEN** the report distinguishes structural validity from human review, training eligibility and model quality

### Requirement: Portable integrity-checked handoff
The distribution SHALL contain the required schemas, examples, documentation and validator and SHALL exclude secrets, private source conversations and unrelated user drafts.

#### Scenario: ZIP is extracted away from the repository
- **WHEN** the recipient runs the documented validation command with dependencies installed
- **THEN** the packaged examples validate without importing the service repository or contacting providers
