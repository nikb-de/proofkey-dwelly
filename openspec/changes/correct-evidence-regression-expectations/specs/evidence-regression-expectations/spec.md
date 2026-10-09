## ADDED Requirements

### Requirement: Valid originals and unavailable processing remain distinct

Tests SHALL verify that a valid saved narrative or an authorized registered
original can be admitted and recovered with processing unavailable, without
calling the prepared consumer or producing a business effect.

#### Scenario: Valid input without a prepared processor
- **WHEN** a valid narrative or authorized registered original is submitted
- **THEN** initial execution and recovery SHALL retain authorized/unavailable
  behavior and SHALL have zero processing attempts and zero planner calls
- **AND** the original content SHALL remain bound to the saved request

### Requirement: Invalid artifact references fail closed

Tests SHALL distinguish a malformed artifact ID, a well-formed absent artifact
and a registered but unauthorized artifact. Each SHALL produce the canonical
generic denial before any prepared consumer, processing attempt or effect.

#### Scenario: Artifact access is invalid or unauthorized
- **WHEN** one of those invalid references is submitted or its saved case is
  recovered without repairing its original authority
- **THEN** the test SHALL verify denial without disclosing artifact contents
- **AND** the test SHALL not weaken runtime access or recovery checks to pass
