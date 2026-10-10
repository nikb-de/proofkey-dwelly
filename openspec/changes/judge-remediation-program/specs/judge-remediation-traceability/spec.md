## ADDED Requirements

### Requirement: Every assessed recommendation remains traceable

The remediation program SHALL preserve all original findings, recommendations, next actions, rubric context and declined-scope entries from exactly five completed judge seats with stable work-item mappings and observed identity limits.

#### Scenario: A finding appears in only one review
- **WHEN** a finding or recommendation lacks consensus
- **THEN** it SHALL still map to at least one retained work item
- **AND** optional or deferred status SHALL NOT remove its source text or completion criterion

### Requirement: Closure requires evidence for the stated scope

Every work item SHALL record its current state, action, responsible role or external dependency, and completion evidence. Documentation, planned tests and source existence SHALL NOT be relabeled executed behavior.

#### Scenario: Focused checks pass while the complete suite fails
- **WHEN** a focused fix has passing evidence but the full candidate suite remains failing
- **THEN** the narrow fix MAY be closed
- **AND** full-suite qualification SHALL remain partial or open

### Requirement: External gates cannot be replaced with synthetic evidence

Actual provider participation, human review, rights, independent custody, protected holdout, unfamiliar-user observation and event facts SHALL require their respective observed evidence and authority.

#### Scenario: A model-generated review or label pack exists
- **WHEN** only simulated approval or development labels are available
- **THEN** the program SHALL retain actual human-review and protected-assessment gaps
- **AND** no publishing, provider spending or event submission SHALL be inferred

### Requirement: Behavioral changes are individually reviewed and archived

Runtime changes SHALL use bounded child specifications, reviewed implementation plans, regression evidence and independent review. Only genuinely completed changes SHALL be archived.

#### Scenario: A leaf completes while the program has unresolved items
- **WHEN** one child change meets its own requirements
- **THEN** that leaf MAY be archived into living specs
- **AND** the umbrella and other unfinished parent requirements SHALL remain open

### Requirement: Historical assessment artifacts remain immutable

New remediation evidence SHALL be stored separately from the frozen original panel and SHALL NOT overwrite historical ratings, source pins, failed attempts or qualification receipts.

#### Scenario: New tests pass
- **WHEN** remediation produces additional evidence
- **THEN** it SHALL identify its own source and environment
- **AND** original judge scores SHALL NOT be presented as updated scores without a real new assessment
