# product-workspace Specification

## Purpose
Provide the Right onTime Team, operator-assisted Customer and Preparation product screens on the existing canonical case backend, preserving explicit authority, provenance and local-sandbox boundaries.
## Requirements
### Requirement: Product team workspace
The platform SHALL provide searchable cases, status filters and counters, a readable selected-case summary, and Summary / Requests / Sources navigation while retaining existing evidence, model, review and execution controls.

#### Scenario: Case selection survives role navigation
- **WHEN** an operator opens the customer view from a selected case
- **THEN** the same case identifier is passed explicitly and can be used to return to the team workspace

### Requirement: Honest customer journey
The platform SHALL distinguish an operator-recorded delivery preference, a saved proposal, human approval and verified local sandbox execution. It SHALL NOT present unverified customer identity, carrier availability, price or physical delivery as confirmed.

#### Scenario: Preference is submitted
- **WHEN** a valid window is submitted using the current snapshot
- **THEN** the platform saves an operator proposal without approving or executing it

#### Scenario: Stale or failed submission
- **WHEN** submission fails or conflicts with a newer snapshot
- **THEN** the draft remains visible and no success or confirmation is shown

### Requirement: Integration preparation
The platform SHALL show current backend capabilities, allow saving and exporting an explicitly local integration profile draft, and run read-only preflight checks. Unavailable integrations SHALL remain visibly unavailable.

#### Scenario: A profile draft is saved
- **WHEN** the operator saves or exports configuration
- **THEN** the UI labels it as a local draft and does not claim runtime activation

### Requirement: Responsive and accessible screens
All product screens SHALL use English UI, keyboard-operable controls, safe text rendering and layouts without horizontal overflow at a 390-pixel viewport.

#### Scenario: Long identifiers and source text
- **WHEN** a case contains long identifiers or untrusted markup
- **THEN** content wraps within the viewport and is displayed as text, not executable HTML
