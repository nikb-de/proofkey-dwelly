## ADDED Requirements

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
