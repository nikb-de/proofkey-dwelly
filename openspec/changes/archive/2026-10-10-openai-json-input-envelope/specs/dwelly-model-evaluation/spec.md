## MODIFIED Requirements

### Requirement: JSON-mode prompt fidelity
Proposal and judge evidence inputs SHALL explicitly identify JSON output format before budget reservation and persistence. The shared OpenAI transport SHALL prefix its input with exactly `Return a JSON object.\n`, preserving the entire supplied prompt unchanged as the suffix. This deterministic format envelope SHALL NOT mutate persisted evidence. Other provider input envelopes SHALL remain unchanged.

#### Scenario: Visible evidence contains no JSON reference
- **WHEN** an ordinary case contains no JSON-related wording
- **THEN** proposal and judge evidence inputs still explicitly name JSON
- **AND** no future evidence or producer identity is added

#### Scenario: Shared adapter receives a JSON-free prompt
- **WHEN** an OpenAI request enables JSON-object mode but only its instructions mention JSON
- **THEN** its input starts with the fixed JSON request and ends with the exact supplied prompt
- **AND** the adapter dispatches once without retry
