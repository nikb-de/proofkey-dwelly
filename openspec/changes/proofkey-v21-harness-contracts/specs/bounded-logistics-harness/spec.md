## ADDED Requirements

### Requirement: Route and authority precede effects

The runtime SHALL determine a typed route and verify authoritative case, object, principal, policy and allowed operations before every external effect, including clarification and operator delivery. An existing record or model confidence SHALL NOT bypass current risk checks.

#### Scenario: Conflicting object classification
- **WHEN** extracted text conflicts with the designated authoritative object record
- **THEN** no business write occurs and only separately authorized clarification or operator delivery is permitted

### Requirement: Slot choice remains within authenticated scope

The runtime MAY autonomously select a feasible permitted slot within an authenticated customer's window, timezone and constraints. It SHALL require current lifecycle/capacity eligibility, business policy and conditional-write guarantees. Listing SHALL NOT imply reservation. It SHALL NOT infer an address change, select outside consent or treat a local API caller as the customer principal. Unresolved mandatory preferences SHALL route to permitted clarification or handoff.

#### Scenario: Earliest visible slot is outside consent
- **WHEN** the first listed slot is outside the authenticated permitted window
- **THEN** that slot is not selected and the runtime considers only eligible authorized alternatives or permitted clarification/handoff

### Requirement: Whole-order refusal binds all inventory

Goods refusal/return SHALL initially operate on the whole authoritative order with every item and quantity bound to current eligible policy and destination. Partial-item requests SHALL NOT silently expand into whole-order effects. Refusal registration and return initiation SHALL retain independent outcomes.

#### Scenario: One item is refused from a multi-item order
- **WHEN** a request explicitly concerns only one item and the profile supports whole-order return only
- **THEN** no whole-order return is dispatched and the request is routed to separately authorized clarification or operator review

### Requirement: Clarification and human decisions preserve boundaries

The runtime SHALL support scripted rehearsal and interactive authenticated clarification with persisted owner, recipient/request binding, awaited fields, expiry and budget. Scripted responses SHALL be labeled simulated. Operator packets SHALL contain all permitted relevant original artifacts, source-linked extracts, conflicts, unknowns, policy and per-effect history. Human refund/coverage/internal-case dispositions SHALL NOT enable autonomous financial adjudication or execution. Internal-case creation, if enabled, SHALL require a separately scoped effect and verified receipt; resumed logistics effects SHALL be freshly gated.

#### Scenario: Operator records a refund disposition
- **WHEN** an authenticated operator requests refund review after inspecting case evidence
- **THEN** the record is retained without a refund/payment dispatch, and any resumed logistics action still requires its own current authority and allowed process

#### Scenario: Interactive reply is missing at expiry
- **WHEN** no authenticated reply arrives within the persisted clarification deadline
- **THEN** waiting expires without a fabricated response, budgets remain persisted and only separately permitted bounded handoff may be attempted

### Requirement: Partial outcomes remain independent

The runtime SHALL independently verify goods refusal registration, return initiation, service refusal registration and operator receipt. Each effect SHALL have a distinct stable logical action ID and postcondition. Return initiation SHALL NOT imply physical receipt or financial approval.

#### Scenario: Refusal succeeds and return times out
- **WHEN** refusal is verified but the return result is unknown
- **THEN** refusal remains verified, return remains unknown, no success for the whole return is claimed and recovery reconciles only the unfinished return

#### Scenario: Service refusal succeeds and operator delivery fails
- **WHEN** the work refusal is verified but the queue does not confirm receipt
- **THEN** the runtime reports registration with pending or blocked handoff and does not adjudicate the dispute

### Requirement: Durable intent precedes send

The runtime SHALL durably commit immutable intent metadata and dispatch state before transport, serialize execution per case and reconcile interrupted writes after restart. Reusing an ID with a changed fingerprint SHALL be rejected. Unknown non-idempotent effects SHALL NOT be retried automatically.

A resend SHALL require verified provider idempotency or authoritative terminal evidence that the original request did not execute and cannot execute later. A negative or eventually consistent readback SHALL NOT establish safe retry by itself.

#### Scenario: Crash after external write
- **WHEN** the external effect exists but the runtime crashes before persisting its verification
- **THEN** restart performs authoritative reconciliation before any resend and preserves the original logical key

#### Scenario: Local commit failure
- **WHEN** the journal cannot durably persist intent or dispatch state
- **THEN** transport is not called

#### Scenario: Terminal request already executed
- **WHEN** a non-idempotent original request is terminal because it already executed
- **THEN** the runtime does not treat inability to execute later as permission to resend it

### Requirement: Logical identity distinguishes duplicates and supersession

The runtime SHALL persist authorized request generations and derive distinct operation/stage logical IDs independently of transport event IDs. It SHALL retain an immutable argument fingerprint, original provider key and explicit supersession relation. A duplicate semantic request SHALL reuse its existing generation; unresolved original effects SHALL block conflicting replacement writes. An unknown request identity SHALL NOT authorize a new generation merely to repeat a business effect.

#### Scenario: Duplicate arrives with another event ID
- **WHEN** a second authenticated input has the same request identity, consent revision and canonical business intent
- **THEN** it binds to the existing request generation and does not create a duplicate effect

#### Scenario: New slot requested during an unknown reschedule
- **WHEN** an authorized changed request supersedes a generation whose reschedule outcome is unknown
- **THEN** the replacement is retained but not dispatched until reconciliation or a separately authorized decision establishes a safe next action

### Requirement: Budgets survive recovery

The runtime SHALL enforce finite shared limits for time, calls, effects and retries. Counters and deadlines SHALL survive restart. Exhaustion SHALL retain partial and unknown outcomes and SHALL NOT fabricate operator receipt or completion.

#### Scenario: Retry loop restarts
- **WHEN** the runtime restarts during a bounded reconciliation loop
- **THEN** previously consumed budget is retained and the loop does not acquire a new budget

### Requirement: Generated official output preserves every case

The system SHALL generate `ANSWERS/<case>/ANSWER.md` and `REASONING.md` for every supplied case, retaining verified, partial, pending, unknown, blocked, failed and no-output states. Output SHALL include concise auditable facts and evidence references, not hidden chain-of-thought or human-corrected replacement answers. Case IDs SHALL NOT escape the output root or silently collide. Batch execution SHALL persist progress and respect a shared deadline and measured export reserve.

#### Scenario: Case ends with an unknown return and a pending handoff
- **WHEN** the global deadline stops execution with refusal verified, return unknown and operator receipt unconfirmed
- **THEN** generated output retains each state and the case remains in the batch denominator without fabricated completion

#### Scenario: Case identifier contains a path escape
- **WHEN** a supplied case identifier would escape the export root or collide with another case path
- **THEN** the exporter refuses the unsafe path and records a visible export failure without overwriting another case
