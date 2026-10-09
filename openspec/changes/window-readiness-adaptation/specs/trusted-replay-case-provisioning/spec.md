## MODIFIED Requirements

### Requirement: Preparation accepts only bounded fixed-family source data
The helper SHALL support the packaged flat-v1.3 profile, process-v1 fixed synthetic family and structured reschedule-window or whole-order goods-refusal requests under default `fixed-synthetic-v1` and the separately specified explicit trusted `fixed-synthetic-observed-stop-v2` selection. It SHALL additionally accept explicit trusted `fixed-synthetic-window-readiness-v3` only with packaged `flat-window-readiness-v1` family v1.3, its exact `reschedule-window-readiness-v2` / `v2-window-readiness` window process and structured reschedule-window input. Both initial input validation and prepared revalidation SHALL enforce the same closed factory-key/profile commitments. It SHALL derive the business fingerprint from the validated request and SHALL NOT describe that fingerprint as a complete request identity.

#### Scenario: Untrusted or malformed preparation input
- **WHEN** input contains a code/profile/factory override, unsupported request kind, narrative/media input, malformed or oversized fixture, duplicate JSON keys, nonfinite values, invalid UTF-8, excessive nesting or contradictory declared case scope
- **THEN** preparation is rejected before private child allocation
- **AND** existing package and caller files remain unchanged.

#### Scenario: Valid bounded preparation
- **WHEN** accepted fixture bytes are prepared
- **THEN** validation, hashing, private staging and source declaration use the same byte snapshot
- **AND** existing runtime source, capability, consent and principal checks remain mandatory.

#### Scenario: Finite fixture envelope validation
- **WHEN** the helper checks fixture bytes
- **THEN** it enforces at most 1 MiB and 64 container levels before recursive decoding, exact version/time/scopes/facts envelope keys, exactly one matching scope and matching outer fact identifiers
- **AND** it requires exact case-binding identity and the derived business fingerprint
- **AND** it leaves all other nested domain facts and positive eligibility to existing runtime validation.

#### Scenario: Encoded source exceeds its existing declaration limit
- **WHEN** raw fixture bytes fit the input ceiling but their exact JSON-embedded source declaration exceeds the existing registered-release limit
- **THEN** preparation rejects the input before private child allocation
- **AND** no registered-release limit or executable pin is changed.

#### Scenario: Fixture line endings cannot be represented exactly
- **WHEN** decoded fixture text contains an actual CR character (U+000D), including CRLF or bare-CR whitespace
- **THEN** preparation rejects it as `invalid_input` before any child allocation
- **AND** JSON-escaped `\r` string content remains accepted and accepted bytes are never normalized
- **AND** this restriction preserves exact comparison with the unchanged admission consumer that normalizes actual CR in text reads.

#### Scenario: Candidate selection changes across validation
- **WHEN** trusted v3 selection has the wrong profile, kind, process, source inventory or key initially or during prepared revalidation
- **THEN** it is rejected before entry
- **AND** a default or v2 selection is not silently upgraded to v3 and no historical resource root is adopted.

### Requirement: Registered compatibility and denial contracts remain intact
The integration helper SHALL preserve one-release composition, exact executable versions, original writer/route/claim enforcement and unsupported-command boundaries. Only explicitly selected v2 same-owner stop is added by its separate contract; default v1 remains run-only. Explicit v3 SHALL also be run-only and SHALL NOT inherit v2 stop or any registered recovery/reply/transfer authority. Adapter-level candidate exact-slot comparisons SHALL NOT expand v3 preparation beyond reschedule-window.

#### Scenario: Unsupported or retained work
- **WHEN** a caller supplies a different executable family, multiple registered releases, source/pin/resource mismatch, occupied root, ambiguous claim, registered recovery/reply/transfer, v1 or v3 stop, or v2 stop outside its current-owner contract
- **THEN** the existing denial, unavailability or writer-conflict semantics are retained
- **AND** no existing debt, effect, original identity, deadline or claim is cleared or rebound.

#### Scenario: Transport proof does not match source authority
- **WHEN** the structured case and review grant are valid but transport proof or source ACL does not authorize the actor
- **THEN** the operation is denied with no unauthorized business effect
- **AND** any legitimately created audit/admission records remain visible and preserved.

#### Scenario: Existing v2 stop remains selected explicitly
- **WHEN** an exact completed stop-v2 composition performs its supported same-owner stop
- **THEN** its separate stop contract remains in force unchanged
- **AND** neither v3 implementation nor default selection removes, broadens or silently substitutes that contract.
