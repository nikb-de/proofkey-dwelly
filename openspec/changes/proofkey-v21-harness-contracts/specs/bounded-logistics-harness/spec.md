## ADDED Requirements

### Requirement: Route and authority precede effects

The runtime SHALL determine a typed route and verify authoritative case, object, principal, policy and allowed operations before every external effect, including clarification and operator delivery. An existing record or model confidence SHALL NOT bypass current risk checks.

#### Scenario: Conflicting object classification
- **WHEN** extracted text conflicts with the designated authoritative object record
- **THEN** no business write occurs and only separately authorized clarification or operator delivery is permitted

### Requirement: Slot choice remains within authenticated scope

The runtime SHALL support explicit `authorized_window` and `exact_slot` consent profiles and persist the selected mode/version. The main demo SHALL use authorized-window selection; the second profile SHALL require current authenticated confirmation bound to the specific slot and consent revision. Autonomous selection SHALL remain within the authenticated window, timezone and constraints. Both modes SHALL require current lifecycle/capacity eligibility, business policy and conditional-write guarantees. Listing SHALL NOT imply reservation. The runtime SHALL NOT broaden consent mode, infer an address change, select outside consent or treat a local API caller as the customer principal. Unresolved mandatory preferences SHALL route to permitted clarification or handoff.

#### Scenario: Earliest visible slot is outside consent
- **WHEN** the first listed slot is outside the authenticated permitted window
- **THEN** that slot is not selected and the runtime considers only eligible authorized alternatives or permitted clarification/handoff

#### Scenario: Exact confirmed slot becomes unavailable
- **WHEN** the exact-slot profile's confirmed slot or material constraints change before dispatch
- **THEN** the runtime requests applicable fresh authenticated confirmation or hands off without switching to window-selection consent

### Requirement: Whole-order refusal binds all inventory

Goods refusal/return SHALL initially operate on the whole authoritative order with every item and quantity bound to current eligible policy and destination. Partial-item requests SHALL NOT silently expand into whole-order effects. Refusal registration and return initiation SHALL retain independent outcomes.

#### Scenario: One item is refused from a multi-item order
- **WHEN** a request explicitly concerns only one item and the profile supports whole-order return only
- **THEN** no whole-order return is dispatched and the request is routed to separately authorized clarification or operator review

### Requirement: Clarification and human decisions preserve boundaries

The runtime SHALL support scripted rehearsal and interactive authenticated clarification with persisted question identity, owner/epoch, recipient/request binding, origin phase, next gate, awaited fields, expiry and budget. Scripted responses SHALL be labeled simulated. Operator-supplied facts SHALL return through completeness and fresh authority checks, not directly to execution; operator identity or notes SHALL NOT manufacture customer consent. Operator packets SHALL contain all permitted relevant original artifacts, source-linked extracts, conflicts, unknowns, policy and per-effect history. Human refund/coverage/internal-case dispositions SHALL NOT enable autonomous financial adjudication or execution. Internal-case disposition SHALL be record-only in the initial profile; actual creation SHALL remain disabled. Resumed logistics effects SHALL be freshly gated.

#### Scenario: Operator records a refund disposition
- **WHEN** an authenticated operator requests refund review after inspecting case evidence
- **THEN** the record is retained without a refund/payment dispatch, and any resumed logistics action still requires its own current authority and allowed process

#### Scenario: Interactive reply is missing at expiry
- **WHEN** no authenticated reply arrives within the persisted clarification deadline
- **THEN** waiting expires without a fabricated response, budgets remain persisted and only separately permitted bounded handoff may be attempted

#### Scenario: Operator fills missing data without customer authority
- **WHEN** an early operator reply supplies the missing order facts but current customer scope or consent is absent
- **THEN** the runtime re-enters completeness/authority checks without dispatching a business effect or treating the reply as customer consent

#### Scenario: Repeated invalid clarification replies
- **WHEN** stale, mismatched or unauthenticated replies repeatedly arrive
- **THEN** they do not reset question/call/deadline budgets and a bounded expiry or permitted handoff remains visible

### Requirement: All workflow phases recover without bypassing gates

The runtime SHALL persist pre-confirmation and effect phases with next gate, profile/process/policy versions, evidence/processing status, case/request/consent revisions, question/awaited fields, human ownership state/revision, stop disposition and budgets. Each external extraction/transcription/planner role SHALL have finite profile-defined invocation/usage caps under shared limits. Before provider entry it SHALL durably reserve/debit invocation and capped usage allowance with identity/status; journal failure SHALL prevent the call. Interrupted invocations SHALL remain consumed/unknown, not free retries or completed processing. Restart SHALL restore the saved phase, invalidate stale observations and revalidate material authority before effects; execution/reconciliation checkpoints SHALL NOT restart intake/extraction. Missing or incompatible checkpoints SHALL fail closed. Resume SHALL NOT automatically repeat messages, model-processing calls or business effects, or fabricate processing/verification receipts. Any necessary repeated processing SHALL be a recorded attempt within remaining authorized budget.

#### Scenario: Crash while awaiting exact-slot confirmation
- **WHEN** the runtime restarts with an outstanding confirmation question
- **THEN** it restores the same question, mode, phase and budgets without resending a message or entering execution without current confirmation

#### Scenario: Crash during extraction or authority checks
- **WHEN** a pre-confirmation checkpoint is restored after interrupted processing or authentication
- **THEN** interrupted processing remains unverified, current authority is checked and no checkpoint grants permission to skip the missing gate

#### Scenario: Crash after transcription dispatch before result save
- **WHEN** external transcription was entered after its durable invocation debit and the runtime crashed before retaining the result
- **THEN** the original attempt remains consumed/unknown and any necessary new attempt is separately recorded within the remaining authorized budget, without a fabricated transcript or a free retry

### Requirement: Stop persists independently of effect outcome

An authenticated stop SHALL durably mark the request generation non-dispatchable independently of original effect status. An accepted stop before dispatch SHALL prevent prepared/undispatched business intents from being sent. Already-started transport SHALL retain possible execution and bounded authoritative reconciliation with the original key. Reconciliation, duplicate input, operator resume or migration SHALL NOT clear stop or authorize resend, even with idempotency or terminal non-execution evidence. Stop SHALL NOT imply order/delivery cancellation, compensation or goods/service refusal. Separately scoped reads/status/handoff MAY remain permitted without inheriting business permission from the stopped generation. Local serialization SHALL NOT be presented as cancellation of an in-flight native write.

#### Scenario: Stopped unknown request is proven not executed
- **WHEN** authoritative reconciliation proves a stopped scheduling request did not execute and cannot execute later
- **THEN** the original generation remains stopped and no resend occurs

#### Scenario: Original operation executes after stop
- **WHEN** readback shows an already-started scheduling operation executed after stop was recorded
- **THEN** execution is reported independently of the retained stop, without automatic undo, retry or fabricated cancellation

#### Scenario: Crash after stop commit before transport
- **WHEN** a prepared business intent is restored after its stop disposition was durably committed
- **THEN** it remains non-dispatchable and saved counters/deadlines are retained

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

A resend SHALL require verified provider idempotency or authoritative terminal evidence that the original request did not execute and cannot execute later, plus an active non-stopped authorized generation and fresh gates. A negative or eventually consistent readback SHALL NOT establish safe retry by itself.

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

The runtime SHALL persist authorized request generations and derive distinct operation/stage logical IDs independently of transport event IDs. It SHALL retain an immutable argument fingerprint, original provider key and explicit supersession relation. A duplicate semantic request SHALL reuse its existing generation; unresolved original effects SHALL block conflicting replacement writes. An unknown request identity SHALL NOT authorize a new generation merely to repeat a business effect. A human decision SHALL NOT create non-execution proof or idempotency, erase uncertainty or bypass a material dependency. A consent change SHALL NOT turn a duplicate into a new business request without separately authenticated new intent.

#### Scenario: Duplicate arrives with another event ID
- **WHEN** a second authenticated input has the same request identity, consent revision and canonical business intent
- **THEN** it binds to the existing request generation and does not create a duplicate effect

#### Scenario: New slot requested during an unknown reschedule
- **WHEN** an authorized changed request supersedes a generation whose reschedule outcome is unknown
- **THEN** the replacement is retained but not dispatched until authoritative evidence establishes a safe next action; human authorization alone does not erase the original uncertainty

#### Scenario: Explicit refusal follows a stopped reschedule
- **WHEN** the authenticated customer separately requests goods/service refusal after stopping scheduling
- **THEN** the runtime creates a distinct authorized generation, checks current object/stage/inventory/policy/consent, preserves the original stop/outcome and blocks any dependent effect whose prerequisites remain uncertain

#### Scenario: Duplicate old request arrives after a subsequent refusal
- **WHEN** the stopped original reschedule input is repeated after a separate refusal request
- **THEN** it binds to the stopped generation without resuming scheduling or resetting case budgets

### Requirement: Completed duplicates replay historical results without actions

A duplicate matching a completed case/object/request generation and immutable intent fingerprint SHALL return the saved result only after current scoped disclosure authorization. Historical request/consent identity SHALL identify the stored generation without requiring current business-action consent for pure disclosure. Missing/revoked access SHALL withhold case details; bounded access-authority reads MAY occur without business-status refresh. Replay SHALL retain result/version, as-of time, independent verified/partial/pending/unknown outcomes and stop, and SHALL be labeled historical. It SHALL NOT invoke models, business effects, customer messages, handoff, automatic business readback/reconciliation, a new request generation or reset execution budgets/deadlines. Recovery of unfinished effects SHALL remain separately scoped, not triggered by the duplicate replay. Automatic status refresh SHALL be excluded.

#### Scenario: Duplicate completed request after a later business change
- **WHEN** an authorized duplicate matches the saved completed request and external business state has since changed
- **THEN** the saved as-of result is replayed as historical without reading current business status, creating a new generation or repeating actions/messages

#### Scenario: Original caller loses access before replay
- **WHEN** a matching duplicate arrives but current scoped disclosure permission is revoked or cannot be established
- **THEN** case details are withheld without relying on historical access permission

#### Scenario: Final saved output retains an unknown effect
- **WHEN** a completed response/output retains an unknown original effect and a matching authorized duplicate arrives
- **THEN** replay preserves that as-of unknown state without inventing verification or automatically reconciling/resending the original effect

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
