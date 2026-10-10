# safe-evidence-trace Specification

## Purpose
TBD - created by archiving change safe-evidence-trace. Update Purpose after archive.
## Requirements
### Requirement: Bounded detached receipt projection
The system SHALL accept an exact `CliReceiptV1` or parse bounded JSON bytes into that contract, revalidate declared fields without hiding invalid denied-result data, and produce an immutable detached `ExecutionTraceV1`. It MUST reject subclasses, malformed input, cycles, nonfinite numbers, duplicate JSON keys and bounds violations with a closed safe failure. Input bytes MUST be at most 1,048,576, depth at most 64, nodes at most 50,000, batch positions at most 128, effects per position at most 256 and total effects at most 4,096. Output MUST be at most 262,144 UTF-8 bytes; it MUST NOT silently drop positions or effects.

#### Scenario: Malformed or excessive input
- **WHEN** input violates any declared bound or includes malformed/duplicate/nonfinite/forged data
- **THEN** no partial trace is returned and the error contains no input content.

#### Scenario: Typed detached input
- **WHEN** a valid exact receipt is projected and source containers are later changed by an illicit bypass
- **THEN** the returned trace stays unchanged and contains only validated allowed output types.

### Requirement: Honest correlated stage evidence
The trace SHALL retain all command/batch ordinals, invalid/unstarted/denied/pending outcomes, result-access status, reported effect verification, publication/export status and independent shutdown facts. It SHALL validate command/run release, mode and clock correspondence and duplicate command IDs before correlating rows. It MUST always label provenance `unverified_receipt_projection`, transport dispatch `unknown`, original readback observation `not_observed` and publication files checked `false`. Host start MUST NOT imply authorization; `verified` MUST describe only reported effect verification, not global success.

#### Scenario: Started but denied or pending
- **WHEN** a receipt contains host start with a denied result or unresolved/pending command
- **THEN** the start, returned access status, unresolved position and shutdown are displayed independently without a successful authorization or dispatch claim.

#### Scenario: Reported verified effect
- **WHEN** an authorized result contains a verified effect and committed export
- **THEN** the trace reports those statuses while still marking actual dispatch and original readback unobserved and current publication files unchecked.

### Requirement: Content-free local correlation
The trace SHALL emit only fixed schema keys, closed status enums, finite nonnegative durations, counts, ordinals, booleans and trace-local alias tokens. It MUST NOT emit raw arbitrary identifiers, operation names, input/output hashes, paths, timestamps, request arguments, rationale, policy/evidence references, postconditions or free-text failures. Identical identities within a namespace SHALL receive the same deterministic first-occurrence token; tokens SHALL NOT claim cross-trace identity or anonymization.

#### Scenario: Content in every identifier
- **WHEN** otherwise valid receipt fields contain secret-shaped text or hostile Markdown
- **THEN** neither JSON nor Markdown output includes that text, any derived raw hash or an input-derived link, and correlation remains possible with local aliases.

### Requirement: Explicit offline renderer and short guide
The system SHALL expose `python -m proofkey.trace --format json|markdown`, reading stdin with a limit-plus-one read and writing no runtime files. Invalid usage/input SHALL return a nonzero exit and safe closed error without traceback/input echoes. It MUST NOT change the existing `proofkey` CLI wire. Documentation SHALL show exact fresh supported-path capture/render commands, a small diagram, outcome interpretation, safe pending/unknown handling and links to the existing second case/new-case routes. Verification MUST execute the guide commands on fresh synthetic state and preserve actual output/exit evidence; this is not a human onboarding study.

#### Scenario: Fresh documented run
- **WHEN** the guide is executed with its stated installed/source prerequisites in a new working directory
- **THEN** it produces a captured existing CLI receipt and bounded JSON/Markdown trace without live providers or new authority.

#### Scenario: Invalid renderer input
- **WHEN** stdin is oversized or the renderer receives unsupported arguments
- **THEN** it exits nonzero, emits only a closed safe error and creates no runtime state.

