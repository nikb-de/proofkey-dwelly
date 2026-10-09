## MODIFIED Requirements

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

#### Scenario: Two seconds remain on either parent clock
- **WHEN** a real engine operation finishes with two seconds remaining on UTC and four on monotonic, or four on UTC and two on monotonic
- **THEN** capture, route join and final persistence SHALL share a two-second phase and complete if no time is consumed
- **AND** the original parent and durable execution timing SHALL remain unchanged with exactly one business effect

#### Scenario: Short phase expires before final claim write
- **WHEN** the same two-second phase expires after route observation and before final persistence
- **THEN** completion SHALL time out while preserving the effect, imported account and sealed claim
