## MODIFIED Requirements

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
