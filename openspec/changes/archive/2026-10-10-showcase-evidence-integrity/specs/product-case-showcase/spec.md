## ADDED Requirements

### Requirement: Replay evidence integrity
The replay builder SHALL validate each snapshot's canonical content hash and each recorded model input's complete equality with the platform's evidence projection at that snapshot, including the canonical input hash. Coordination SHALL reference an existing captured snapshot at or before the scene cutoff with a matching revision and hash. Nested coordination records and their evidence SHALL not exceed that historical cutoff, and an offer's recorded terms hash SHALL match its complete terms. Valid older coordination SHALL remain usable when a scene contains newer messages.

#### Scenario: Model input content changes without changing event IDs
- **WHEN** a recorded model input changes a message body, actor, timestamp, order or other projected field, with either a stale or recomputed input hash
- **THEN** the builder rejects the capture instead of presenting the model as bound to the original source cutoff

#### Scenario: Coordination comes from a later or mismatched snapshot
- **WHEN** an early scene contains future coordination, a mismatched coordination snapshot hash, a future nested record or evidence outside the coordination cutoff
- **THEN** the builder rejects the capture

#### Scenario: An offer changes while its recorded hash remains unchanged
- **WHEN** recorded offer terms do not match their canonical terms hash
- **THEN** the builder rejects the capture

#### Scenario: Valid historical captures are rebuilt
- **WHEN** a scene contains valid older coordination and the unchanged original source/model records
- **THEN** the builder preserves that history and produces the same replay bundle bytes
