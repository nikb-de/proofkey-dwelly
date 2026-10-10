# trusted-replay-case-provisioning Specification

## Purpose
Define bounded trusted preparation of structured synthetic cases and their separately authorized execution through the existing library and trusted CLI composition, preserving exact input, resource identity, admission and owner-lifecycle boundaries.
## Requirements
### Requirement: Trusted preparation remains separate from authority
The system SHALL prepare one finite synthetic release from a structured case and immutable fixture bytes without granting execution authority, starting a runtime, or manufacturing review or transport credentials.

#### Scenario: Preparation without a reviewer
- **WHEN** an engineer supplies valid preparation inputs and a fresh private parent
- **THEN** the helper returns an inspectable prepared artifact with identities and hashes
- **AND** no journal/world/control database, admission attempt, claim, route or business effect is created
- **AND** review, authorship, executed regression and complete dependency closure are not claimed

#### Scenario: Missing or mismatched authority
- **WHEN** configuration lacks the required exact review resolver or its selected grant is unknown, expired, future-issued or bound to another artifact
- **THEN** configuration or launch fails closed
- **AND** no grant is generated, extended or silently substituted

#### Scenario: Review and launch have separate bounded lifecycles
- **WHEN** review occurs after the original preparation context expires
- **THEN** configuration requires a fresh bounded validation context on the same exact synthetic replay clock
- **AND** launch captures its existing independent execution context and rechecks authority at use time
- **AND** an expired validation context, nonexact clock type or grant that expired after configuration is rejected without extending any grant or already-started case deadline

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

#### Scenario: Configured CLI validates the same closed selection
- **WHEN** a trusted configured CLI validates an exact v3 composition
- **THEN** its structural bootstrap SHALL apply the same bound factory-key/profile/request-kind selection as preparation and host composition
- **AND** independent registry, executable-pin, source-snapshot, resource identity and directory checks SHALL remain mandatory with no arbitrary profile override.

### Requirement: Provisioning has a private exclusive filesystem boundary
Preparation SHALL allocate only a fresh opaque private child beneath an explicit validated parent using no-follow traversal, exclusive creation and pinned identities. It SHALL NOT overwrite/adopt existing state, derive paths from request IDs, place state under site-packages or automatically remove/repair partial preparations.

#### Scenario: Alias or invalid target
- **WHEN** a parent or staged target is an alias, replaced identity, unsafe private object, filesystem root, home, current working directory or package location
- **THEN** preparation fails closed
- **AND** sentinels outside any newly allocated private child are unchanged

#### Scenario: Failure during preparation
- **WHEN** bounded I/O or execution time fails after an exclusive child was created
- **THEN** no usable prepared release is returned
- **AND** the partial child remains private diagnostic evidence without any runtime admission state
- **AND** a typed code-only public failure exposes any retained path only to the trusted caller and retains no open descriptor
- **AND** later revalidation rejects changed parent identities rather than rebinding them

### Requirement: The existing CLI consumes an explicit registered composition
The system SHALL permit an exact optional registered composition in trusted `CliConfiguration` and SHALL forward it unchanged to the existing dispatcher. It SHALL preserve default CLI construction and SHALL NOT add business-input or command-line authority/import/path overrides.

#### Scenario: Trusted application bootstrap
- **WHEN** an application supplies a consistent prepared release, explicit valid review resolver, transport resolver and execution configuration
- **THEN** installed `cli.main` executes through the existing registered host path
- **AND** complete original request, authenticated identity, debt, deadlines and effect verification retain their existing enforcement

#### Scenario: Host and registered release selection disagree
- **WHEN** the requested host release is absent or differs from the prepared binding, including an omitted custom release option selecting the unchanged builtin default
- **THEN** execution fails closed without implicitly selecting another release
- **AND** the prepared host registry and registered registry each contain exactly their corresponding bound release

#### Scenario: Fixture changes during configuration validation
- **WHEN** a fixture name, private regular-file metadata or ancestor changes across host-release validation or the subsequent snapshot
- **THEN** configuration rejects the changed input without following aliases or blocking on a FIFO
- **AND** its descriptor read remains nonblocking and bounded to the existing 1 MiB limit, with single-link private metadata, named/ancestry identity and committed fixture hash checked across the snapshot

#### Scenario: Authority injected through public input
- **WHEN** run JSON or command-line arguments attempt to select a module, profile path, factory, clock, grant, executable pins or admission composition
- **THEN** the existing closed parser/input contract rejects the unsupported value
- **AND** no supplied authority or code is used

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

#### Scenario: Ordinary v3 execution outlasts its admission phase
- **WHEN** an exact v3 ordinary business execution remains within its original bound UTC and monotonic parent window but its initial five-second admission phase has elapsed
- **THEN** the ordinary execution guard SHALL enforce the original parent and association checks without treating business execution as another admission or control operation
- **AND** initial preparation, admission sealing, route/claim/control-store operations and final observation SHALL retain their existing phase bounds
- **AND** expired UTC or monotonic parents SHALL remain denied, 24-call/120-active-second/10-second-per-tool allowances SHALL remain unchanged, and no v1/v2 or registered-control authority SHALL be extended.

### Requirement: New-case integration claims require installed outcome evidence
Completion SHALL require two genuinely new business cases through installed library and trusted CLI bootstrap, with four independently checked positive positions, retained negative results and a frozen regression run. Existing fixed examples and package contents SHALL remain intact.

#### Scenario: New window and goods cases
- **WHEN** independent examples use changed identities and changed window/slots or goods inventory/destination
- **THEN** each business fingerprint differs from the corresponding builtin example
- **AND** all four fresh-state positions produce the expected verified effects, original claim/route joins, exports and successful owner closure
- **AND** imported runtime modules resolve inside the installed environment and installed files remain unchanged

#### Scenario: Bounded readiness claim
- **WHEN** the integration evidence passes
- **THEN** documentation describes a trusted Python integration hook and exact synthetic target
- **AND** it does not claim a standalone manifest launcher, native service, human approval, general release verification, unfamiliar-user usability or a completed timed adaptation drill
