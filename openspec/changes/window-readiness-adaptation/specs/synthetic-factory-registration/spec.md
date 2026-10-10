## MODIFIED Requirements

### Requirement: Only trusted host configuration selects explicit source pins
An optional legacy implementation registration SHALL remain an exact immutable synthetic host value with exactly six required paths, independently fixed SHA-256 pins, bounded identity and bytes. A separately named optional process-delta registration SHALL accept only exact frozen/slotted `WindowReadinessRegistrationV1`, its eight declared fields, fixed `synthetic-window-readiness-delta-v1` identity, `local_controlled_synthetic` provenance, exact new factory/profile/process/policy commitments and the independent literal 86-name inventory. Both modes SHALL remain host-owned and mutually exclusive; case packets and generated proposals SHALL NOT select them. The new mode SHALL accept nonempty immutable source bytes bounded by 1 MiB each and 8 MiB aggregate while retaining all existing total artifact/envelope and 2 MiB proposal-material limits.

#### Scenario: Malformed or drifting material
- **WHEN** registration types, names, hashes, bounds or submitted source differ from the selected explicit host contract
- **THEN** admission SHALL deny before executing behavioral regressions.

#### Scenario: Registration modes or materials are mixed
- **WHEN** both registration fields are non-None, or a J05 context contains historical/non-J05 materials, subclass/list/alias/extra-field/callable values or malformed inventory
- **THEN** the factory SHALL reject before interpreting candidate material under mixed authority
- **AND** separate legacy and J05 contexts SHALL remain independently usable.

### Requirement: Registration provenance binds all generated artifacts
Explicit registration identity, provenance and canonical inventory digest SHALL be bound into proposals and staged manifests and used consistently throughout preparation, resolution, regression checking and staging. The new process-delta mode SHALL detach and retain its exact registration and immutable material, explicitly pass it through constructor validation, resolution, proposal-hash lookup and preparation, and emit exactly the nine-field process_delta_registration commitment defined in its design. Its registration digest SHALL hash an explicit dictionary of the first eight fields excluding itself; its inventory digest SHALL hash the sorted path/hash entries. The verified reconstructed object SHALL be copied exactly into the staged manifest, and existing proposal, regression and release hashes SHALL bind it. Legacy mode SHALL emit no new key and preserve its literal proposal bytes; J05 mode SHALL emit no legacy registration key.

#### Scenario: Reuse across registration identity
- **WHEN** equal source bytes have different registration IDs
- **THEN** proposals SHALL have different hashes and cross-registration regression/review receipts SHALL not be accepted.

#### Scenario: Commitment is altered after construction
- **WHEN** a caller mutates submitted material or substitutes any registration hash, inventory/digest field, reconstruction result or staged commitment
- **THEN** detached context validation and artifact binding SHALL reject stale or mismatched evidence
- **AND** no caller packet SHALL replace the manifest's reconstructed commitment.

### Requirement: Current synthetic evidence matches observed execution
Current tests SHALL use fixed expected pins independently of submitted material and verify imported source identity before producing behavioral receipts. Evidence SHALL describe its actual observed source/dependency scope, not claim a complete runtime closure or production qualification. Exact process-delta registration SHALL additionally require the enumerated semantic match and bound executed regression evidence; source-pin equality alone SHALL NOT authorize a changed process.

#### Scenario: Execution preflight is not trustworthy
- **WHEN** Python assertions are disabled, selected tests are omitted or skipped, or executing project-local modules do not match the recorded source inventory
- **THEN** the lane SHALL NOT emit a successful current-source qualification
- **AND** the source inventory SHALL include new executing files regardless of their Git tracking state, while the closed J05 package contract rejects any new package module.

#### Scenario: Current synthetic control completes staging
- **WHEN** all existing control checks and explicit source binding pass
- **THEN** the result SHALL remain staged_simulation with unmet requirements
- **AND** activation, migration, actual review and timed-adaptation completion SHALL remain unavailable or unestablished
- **AND** changed-process dispatch SHALL remain unavailable except for the exact J05 semantic delta after its own bound execution evidence passes; retained-version resolution SHALL remain unavailable and nonempty pending inventory SHALL still be rejected.

#### Scenario: A receipt lacks matching execution
- **WHEN** a receipt omits or mismatches required cases, outputs, trusted runner/provenance, execution ID/time, proposal, baseline, candidate or test hash
- **THEN** neither J05 registration nor source equality SHALL promote it to qualification.

#### Scenario: Full test selection exceeds the existing receipt-case ceiling
- **WHEN** the exact J05 suite contains more than the unchanged 128 required-case limit
- **THEN** its receipt SHALL use the eight fixed module groups without truncating or excluding any selected test
- **AND** the proposal test hash SHALL bind the complete expected sorted test-ID list digest, each group output SHALL bind every ordered raw per-test record and output hash, and missing, extra, reordered, duplicate or failed execution SHALL deny qualification
- **AND** executed-test counts and receipt-group counts SHALL remain distinct and no existing schema, package limit or historical pin SHALL change.
