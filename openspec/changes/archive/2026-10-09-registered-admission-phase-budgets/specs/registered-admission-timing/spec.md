## ADDED Requirements

### Requirement: Original parent execution authority is immutable

The registered runtime SHALL keep the caller's original execution context and
durable timing record unchanged. Engine execution and final observation SHALL
both remain bounded by its original UTC and monotonic deadlines.

#### Scenario: Execution exceeds ingress ceiling but remains parent-bounded
- **WHEN** a real admitted engine operation finishes after five seconds but
  before both original parent deadlines
- **THEN** the runtime SHALL be able to return its real result and persist an
  observed route and claim within a separate bounded observation phase
- **AND** it SHALL not execute the operation a second time or rewrite original
  timing in the claim

#### Scenario: Parent has already expired
- **WHEN** engine completion is observed after either original parent deadline
- **THEN** final observation SHALL fail closed without granting a new parent
- **AND** actual effects, debt and pending state SHALL remain retained

### Requirement: One shared final-observation phase has a finite budget

The registered runtime SHALL derive at most one final-observation context per
run after validating its original context and resource associations. Its budget
SHALL be no greater than five seconds or either remaining parent bound. Every
capture, route join and final claim operation SHALL share that same context;
no sub-operation SHALL renew its budget.

#### Scenario: Combined final work exhausts phase budget
- **WHEN** final capture, join and persistence together consume the phase budget
- **THEN** the runtime SHALL reject completion even if each individual operation
  took less than five seconds and the parent still has time
- **AND** it SHALL preserve any already committed effects or uncertain records

#### Scenario: Invalid clock or original identity
- **WHEN** the trusted clock moves behind required anchors or the original
  context or registered resource associations have changed
- **THEN** the runtime SHALL reject the operation rather than derive new authority

### Requirement: Initial admission guarantees remain in force

Preparation and sealing SHALL retain the original-start five-second control
ceiling and seal-before-import ordering. The timing fix SHALL not enable new
profiles, live providers, registered recovery, reply, stop, or actual approval.

#### Scenario: Initial control phase has expired
- **WHEN** preparation or sealing attempts to proceed after its control cutoff
- **THEN** it SHALL be rejected with existing fail-closed retention semantics
