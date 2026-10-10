# coordination-review-ui Specification

## Purpose
Define source-bound, human-reviewed model context and Team/Customer controls for the durable local coordination workflow, including atomic simulated acceptance and honest separation of receipts from real-world effects.
## Requirements
### Requirement: Reviewed model context is advisory and source-bound
The system SHALL allow an explicit operator command to reference a succeeded model run only when its frozen source and validated candidate match the current case snapshot. It SHALL reject missing, pending, failed, cross-case or stale references. A model result SHALL NOT execute or authorize a coordination command. Exact idempotent replay SHALL return the saved result without resolving a model run again.

#### Scenario: Current proposal assists a human command
- **WHEN** an operator reviews a current succeeded proposal and submits a separately specified valid command with a review note
- **THEN** the normal policy/evidence checks apply and compact model provenance is persisted with the audit

#### Scenario: Source changes after inference
- **WHEN** a referenced run is bound to an older case snapshot
- **THEN** the command is rejected without changing case or coordination state

### Requirement: Local acceptance is atomic and honestly labelled
The system SHALL support a local-preview acceptance command bound to the exact offer, terms hash, case revision and workflow version. It SHALL require an explicit acknowledgement and atomically append a labelled simulated customer message and consent audit. It SHALL NOT claim authenticated customer consent, real carrier contact or physical delivery.

#### Scenario: Accept a current complete offer
- **WHEN** the local preview explicitly acknowledges an awaiting-consent offer
- **THEN** both evidence and consent persist atomically, the phase becomes ready_to_book, and external effects remain zero

#### Scenario: Offer or snapshot changed
- **WHEN** the submitted offer or snapshot no longer matches
- **THEN** no evidence or consent is appended and the draft remains available for review

### Requirement: Team and customer expose the workflow
The Team interface SHALL expose phase-appropriate reviewed commands, complete terms, source evidence, model context, pending requests and local receipts. The Customer interface SHALL display complete terms and allow only explicitly labelled local acceptance. Both SHALL show stale state and separate local booking confirmation from physical delivery. Rendering and refreshing SHALL be read-only. Existing cases without coordination SHALL retain their old flow.

#### Scenario: Small-screen customer preview
- **WHEN** a user opens a coordinated case on a 390-pixel viewport
- **THEN** the complete offer and local-only caveats are readable without horizontal overflow
