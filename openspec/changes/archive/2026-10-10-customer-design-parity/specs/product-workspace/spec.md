## ADDED Requirements

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
