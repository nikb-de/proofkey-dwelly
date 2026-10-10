## ADDED Requirements

### Requirement: Portable and actionable local validation
The workbench SHALL accept contract-valid plain data records across JavaScript realms while rejecting arrays, class instances, unknown fields, invalid IDs, and invalid participant relationships. Declaration errors SHALL identify a failed field or rule without disclosing submitted values, and the UI SHALL retain the unsaved draft.

#### Scenario: Foreign-realm case declaration
- **WHEN** a valid declaration or nested links record originates in another JavaScript realm
- **THEN** validation succeeds without relaxing the closed field set or participant rules

#### Scenario: Recoverable declaration error
- **WHEN** an identifier or participant rule fails
- **THEN** the error identifies that field or rule rather than only reporting an invalid payload and the draft remains available
