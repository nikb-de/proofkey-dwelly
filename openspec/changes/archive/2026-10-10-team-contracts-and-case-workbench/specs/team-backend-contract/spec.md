## ADDED Requirements

### Requirement: Shared versioned data and transition contract
The contract pack SHALL freeze zero-based source revisions, existing source identifiers, immutable case snapshots and separate media, analysis and operational lifecycles. It SHALL identify each interface as implemented or target, and SHALL NOT report a target route as available.

#### Scenario: Parallel consumers
- **WHEN** UI, E2E and evaluation authors use contract v1
- **THEN** they use the same source case ID/revision/hash and distinguish stored media, analysis completion, dispatch acknowledgement and verified operational outcome

### Requirement: Evaluation isolation
Model-visible input SHALL exclude labels, future events and evaluator-only transitions. Training labels SHALL retain human-review status and SHALL NOT grant operational authority.

#### Scenario: Decision at an earlier revision
- **WHEN** later evidence or a label is present in the episode
- **THEN** it is absent from the earlier model-visible decision input and cannot make that decision appear grounded

### Requirement: Honest storage and browser boundary
The contract SHALL distinguish browser-local storage from backend SQLite and target private object storage. The existing service Origin and authentication boundary SHALL remain unchanged by contract publication.

#### Scenario: Browser integration is not installed
- **WHEN** the local workbench stores a file
- **THEN** neither a server upload nor a provider inspection is claimed
