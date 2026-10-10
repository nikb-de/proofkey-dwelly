# dwelly-model-evaluation Specification

## Purpose
Define an isolated, auditable proposal and three-provider evaluation workflow that preserves evidence boundaries, limits experiment spend, and never grants operational authority or claims unvalidated model quality.
## Requirements
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

### Requirement: JSON-mode prompt fidelity
Proposal and judge inputs SHALL explicitly identify JSON output format before
budget reservation and persistence. Persisted inputs SHALL equal transport inputs.

#### Scenario: Visible evidence contains no JSON reference
- **WHEN** an ordinary case contains no JSON-related wording
- **THEN** proposal and judge requests still explicitly name JSON in their input
- **AND** no future evidence or producer identity is added

### Requirement: Explicit Anthropic workspace selection
An Anthropic seat SHALL optionally select a workspace through a named environment
variable. This option SHALL be rejected for other providers. Missing or malformed
configured values SHALL prevent dispatch without exposing credential values.

#### Scenario: Organizational key requires a workspace
- **WHEN** an Anthropic seat specifies a valid workspace variable and it is set
- **THEN** only the Anthropic request carries its value in `anthropic-workspace-id`
- **AND** neither the request body nor persisted config includes that value

#### Scenario: Configured workspace is missing
- **WHEN** the named workspace variable is absent
- **THEN** offline preflight reports its name as missing and is not ready
- **AND** the transport refuses the request before network dispatch

#### Scenario: Legacy workspace-scoped key
- **WHEN** the Anthropic seat omits workspace configuration
- **THEN** no workspace header is added and legacy behavior is retained

### Requirement: Strict model reply envelope normalization
The model reply parser SHALL accept a bare JSON value or one complete outer JSON
Markdown fence, then apply the existing strict JSON decoder and output schema.
Raw provider receipts SHALL remain unchanged. Source/config JSON parsing SHALL
not be relaxed.

#### Scenario: Claude returns one fenced JSON judgment
- **WHEN** the entire model reply is a single JSON Markdown block
- **THEN** its contents are decoded and schema-validated
- **AND** the original fenced reply remains in the provider receipt

#### Scenario: Reply contains extra prose or invalid JSON
- **WHEN** prose, multiple blocks, duplicate keys, nonfinite numbers or trailing data occur
- **THEN** the reply is rejected, never repaired or silently extracted
