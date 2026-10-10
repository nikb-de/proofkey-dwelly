## ADDED Requirements

### Requirement: Source cases become bounded provenance-preserving snapshots
The importer SHALL read the Delivery & Logistics track, validate event structure and chronology, preserve exact raw source bytes and hashes, and identify cases by track plus number. It SHALL reject symlinks, traversal, duplicate or missing event numbers, malformed timestamps and unknown stages. It SHALL never fetch remote resources or overwrite output.

#### Scenario: An intact public case is imported
- **WHEN** a valid case folder contains an index, history and optional attachments
- **THEN** exact raw bytes and source hashes are retained separately from the agent snapshot
- **AND** source event references identify every visible message.

#### Scenario: An unsafe or malformed source is supplied
- **WHEN** a local link escapes the case, a source is a symlink, event metadata is invalid or output exists
- **THEN** import fails without publishing a partial bundle or changing source/existing output.

### Requirement: Future information cannot enter the decision input
The snapshot SHALL contain only Context/Escalation events preceding the unique Agent action and attachments linked in those visible events. Index prose, action references, later events, future attachment names and future source hashes SHALL be evaluator-only.

#### Scenario: A future answer changes
- **WHEN** only index prose, the reference action or later evidence changes
- **THEN** serialized agent input and its hash remain unchanged.

### Requirement: Offline proposals confer no execution authority
The pilot SHALL consume only normalized snapshots and emit source-cited communication proposals with an explicit unsent/no-effects status. It SHALL use no case-specific lookup, live model, operational adapter or evaluator reference. Unsupported input SHALL produce an explicit operator-review proposal rather than inventing a completed operation or business authority.

#### Scenario: Recipient has not selected a offered slot
- **WHEN** visible context offers multiple slots and the recipient requests rescheduling without selecting one
- **THEN** the baseline proposes asking the recipient to choose, not booking a slot.

### Requirement: Assessment separates routing proxy from semantic correctness
The evaluator SHALL compare recipient/channel as a routing proxy only, retain every case/error, mark semantic correctness unassessed, and distinguish missing output from mismatch. It SHALL expose reference provenance, development-only status, repeatability and sensitivity controls without claiming held-out or production qualification.

#### Scenario: A proposal follows a different defensible route
- **WHEN** its recipient/channel differs from the recorded action
- **THEN** routing agreement is false and semantic correctness remains unassessed, not incorrect.

#### Scenario: A routing match asserts completed payment
- **WHEN** an otherwise matching proposal violates the no-effects schema
- **THEN** the contract check fails despite routing agreement.
