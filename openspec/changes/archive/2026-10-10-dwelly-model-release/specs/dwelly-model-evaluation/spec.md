## ADDED Requirements

### Requirement: Visible-only model proposals
The system SHALL provide a model only the validated decision snapshot and SHALL persist unsent evidence-cited proposals without executing business actions.

#### Scenario: Future answer exists in source
- **WHEN** the source contains recorded next actions and later confirmations
- **THEN** proposal prompts contain none of those evaluator-only records

### Requirement: Three attributable API judges
The system SHALL support explicit OpenAI, Anthropic and Gemini judges with eight anchored rubrics, provider receipts, missing-output accounting and provisional aggregate scores.

#### Scenario: One judge is unavailable
- **WHEN** a provider key is missing or its request fails
- **THEN** the result records that seat as unavailable and does not substitute a provider or score zero

### Requirement: Bounded private execution
The system SHALL require explicit live mode and reserve spend against a maximum USD 25 provider/model experiment cap before external calls.

#### Scenario: No affordable reservation remains
- **WHEN** the next conservative reservation exceeds the configured cap
- **THEN** no request is dispatched and the report records budget exhaustion

### Requirement: Reproducible source release
The system SHALL expose CLI and Docker workflows, offline tests and team case intake guidance without embedding credentials or claiming human-validated quality.

#### Scenario: Release without API credentials
- **WHEN** the user builds and runs offline mode
- **THEN** the package works without credentials and reports no live model participation
