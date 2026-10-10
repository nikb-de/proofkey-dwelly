## ADDED Requirements

### Requirement: Preserve registered runtime source closure
The optional shadow resolver SHALL reside in the companion bridge package. It SHALL NOT expand or repin the runtime's registered implementation closure, and the runtime-free CLI SHALL NOT eagerly import runtime dependencies.

Companion-specific resolver tests SHALL NOT require the repository-root companion package when running the standalone runtime test suite from its documented directory.

#### Scenario: Companion installation
- **WHEN** the optional resolver is present in the source checkout
- **THEN** the unchanged runtime package passes its current closure preflight and the bridge CLI remains usable without runtime dependencies

#### Scenario: Read-only binding after relocation
- **WHEN** a trusted host imports the resolver from `tools.dwelly_bridge.runtime_binding`
- **THEN** its existing validation, source identity, scope checks and zero-mutation guarantees remain unchanged
