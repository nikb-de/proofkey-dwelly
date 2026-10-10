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

### Requirement: Task-oriented team hierarchy
The Team screen SHALL prioritize case context and the current persisted proposal, while keeping analysis available without implying it has already run. Case rows SHALL present readable order/task context, keep raw IDs available and searchable, and preserve keyboard access. Secondary task and activity text SHALL remain readable at desktop and mobile sizes.

#### Scenario: Current proposal is displayed
- **WHEN** the selected case has a current persisted proposal
- **THEN** Summary displays its action and recorded review status with a route to Requests
- **AND** neither external sending nor a booking is implied

#### Scenario: No current proposal exists
- **WHEN** no usable current proposal exists
- **THEN** Summary explicitly says so and offers existing analysis or proposal controls
- **AND** stale history is not presented as the current action

### Requirement: Customer design fidelity
The customer experience SHALL preserve the approved final Right onTime layout: compact centered shell, branded order header, human-readable delivery context, one primary card and in-card progress. Internal evidence selection and raw case identifiers SHALL NOT dominate the customer task.

#### Scenario: No current delivery options
- **WHEN** the current case contains no usable delivery proposal
- **THEN** the customer sees an explicit unavailable-options state and safe status/help actions
- **AND** no invented time, price or booking is displayed

#### Scenario: Review a recorded proposal
- **WHEN** a current proposal supplies a valid future delivery window and evidence references
- **THEN** the customer can review those exact terms without selecting internal evidence identifiers
- **AND** submission preserves snapshot checks and creates only a proposal for operator review

#### Scenario: Unsupported cancellation
- **WHEN** the customer uses the stop control
- **THEN** the UI may abandon an unsent local draft or explain that an operator is required
- **AND** it SHALL NOT claim that backend work or an external booking was cancelled

#### Scenario: Selected offer is replaced
- **WHEN** a selected offer is absent, superseded or differently bound in the latest preflight read
- **THEN** a new submission is blocked and the customer must select a current offer
- **AND** retained old terms are not silently rebound to a new snapshot
- **AND** an unchanged already-dispatched request may use its original idempotency key to recover an uncertain response

#### Scenario: Rendered verification
- **WHEN** a customer layout change is verified
- **THEN** desktop and mobile screenshots and browser layout checks are retained
- **AND** functional test success alone is not reported as design fidelity
