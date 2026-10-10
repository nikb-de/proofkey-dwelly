# installed-offline-resources Specification

## Purpose
TBD - created by archiving change installed-offline-resources. Update Purpose after archive.
## Requirements
### Requirement: The distribution contains the existing supported offline resources
The distribution SHALL include the ten previously supported built-in profile JSON files, both fixed host fixture JSON files and the existing SQL schema with their byte-identical historical content, plus the explicit `flat-window-readiness-v1.json` candidate profile. The candidate package resource SHALL be byte-identical to its source mirror and have its own newly derived expected hash. Package-data and source-distribution manifests SHALL list it explicitly. The distribution SHALL NOT depend on checkout-relative resource locations.

#### Scenario: Installed built-in loading
- **WHEN** the ordinary filesystem-installed package is imported outside the checkout with user site disabled and PYTHONPATH cleared
- **THEN** every supported built-in profile loads from package-owned data and a new journal initializes using the packaged schema
- **AND** both fixed synthetic host registrations resolve their existing profile and fixture bytes.

#### Scenario: Unplanned distribution content
- **WHEN** wheel and source-distribution members are inspected
- **THEN** the resource inventory matches the explicit approved list
- **AND** private outputs, environments, databases and unrelated media are absent.

#### Scenario: Source-only candidate resource checks pass
- **WHEN** the new candidate resource, mirror, package lists and exact expected inventory pass source checks without a fresh installation
- **THEN** those checks establish only source/resource consistency
- **AND** they do not claim a new installed-artifact execution or replace the existing installed-evidence requirement.

### Requirement: Installation preserves trust and identity boundaries
Built-in resource relocation SHALL preserve existing host pinned-byte validation and separate writable-state provisioning. The repair SHALL NOT add a request-, CWD- or environment-controlled built-in resource fallback, new release authority or new process semantics.

#### Scenario: Missing, changed or shadowed resource
- **WHEN** required installed host data is missing or fails its existing validation, or an unrelated CWD contains a same-named resource
- **THEN** invalid required data fails closed
- **AND** CWD data cannot replace package-owned built-ins

#### Scenario: Current implementation bytes change
- **WHEN** relocation changes the hash of a registered current implementation file
- **THEN** the current implementation registration receives a new identity and correct source hashes
- **AND** historical registrations and serialization vectors remain unchanged

### Requirement: Installed execution evidence is distinct from source tests
An installation success claim SHALL require fresh isolated installation and outside-checkout console, module, library and explicitly composed API execution for the two fixed synthetic cases. It SHALL record artifact identities, target environment, import origins, raw outcomes and persisted effect/readback evidence.

#### Scenario: Dependency artifacts are unavailable
- **WHEN** exact compatible build or runtime artifacts are unavailable locally and acquisition is not approved or does not succeed
- **THEN** source tests and structural checks may be reported only as such
- **AND** installed verification and J13 completion remain open

#### Scenario: Scoped installation succeeds
- **WHEN** the exact target installation and both fixed cases pass independent readback
- **THEN** the evidence describes only the observed target and synthetic surface
- **AND** Linux, live providers, full release reproduction and assessment qualification are not inferred
