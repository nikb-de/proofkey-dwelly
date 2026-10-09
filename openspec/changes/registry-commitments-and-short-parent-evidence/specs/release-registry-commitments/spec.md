## ADDED Requirements

### Requirement: Public inventory is detached and validated

The registry SHALL expose `commitments() -> tuple[tuple[str, str], ...]` as sorted exact built-in tuples and strings containing release IDs and artifact hashes only. It SHALL validate its actual current retained records: exact registry, container, pair, ID and bytes types; one through 32 unique sorted IDs; at most 8 MiB per release and 32 MiB total before parsing; valid canonical envelopes; and matching outer and embedded release IDs. It SHALL not return mutable aliases or a stale independent cache.

#### Scenario: Registry has multiple valid releases
- **WHEN** a caller obtains the inventory
- **THEN** it receives a detached sorted immutable projection without declarations, resources or authority handles
- **AND** later retained-record replacement cannot change the old projection or evade a new validation

#### Scenario: Retained records have been corrupted
- **WHEN** records are malformed, relabeled, duplicated, unsorted or exceed bounds
- **THEN** inventory acquisition SHALL fail closed before the malformed records can authorize admission

### Requirement: Admission consumes public commitments without widening authority

Composition SHALL accept exactly one release matching its binding. The admission owner SHALL compare a fresh inventory with its captured detached commitments before claims or business effects. Route-store construction SHALL resolve the public inventory, cross-check IDs and hashes, and preserve canonical release bytes and its existing registry digest recipe.

#### Scenario: Valid release substituted after owner creation
- **WHEN** a different valid envelope replaces a captured registry entry
- **THEN** the existing owner SHALL deny entry before new claims or business effects

#### Scenario: Inventory contains two releases
- **WHEN** a host composition attempts to use a multi-release inventory
- **THEN** it SHALL reject the composition even though each individual envelope is valid
