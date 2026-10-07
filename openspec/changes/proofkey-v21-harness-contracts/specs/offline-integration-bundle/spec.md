## ADDED Requirements

### Requirement: Six scoped offline adapter surfaces

The implementation SHALL provide separate typed interfaces for case records, delivery operations, scheduling, returns, customer messaging and operator inbox. Their offline providers SHALL retain operational state independently of the runtime journal. All effects SHALL pass the shared policy, journal, budget and verification boundary. Adapters SHALL NOT introduce additional autonomous workflow classes or bypass that boundary.

#### Scenario: Combined goods workflow crosses providers
- **WHEN** an authorized goods refusal and permitted return are processed
- **THEN** delivery registration and return initiation use separate adapter operations, logical IDs and authoritative readbacks, with partial outcomes retained independently

#### Scenario: Adapter attempts a hidden compensating action
- **WHEN** a provider reports a failed or unknown effect
- **THEN** its adapter does not privately call another effect adapter or issue an unjournaled compensating write

### Requirement: Connection capability manifests fail closed

Each enabled operation SHALL have an evidence-bound versioned manifest covering authority, effect permission, acknowledgement meaning, readback, idempotency scope, conditional-write guarantees, timeout and terminal non-execution evidence. Unknown mandatory guarantees SHALL disable the affected operation without inventing provider behavior. Offline contract evidence SHALL NOT be presented as a live provider guarantee.

#### Scenario: Returns connection lacks authoritative readback
- **WHEN** return creation is advertised but its authoritative postcondition cannot be verified
- **THEN** creation remains disabled and only separately permitted registration, clarification or handoff can occur

#### Scenario: Structured profile has no media access
- **WHEN** input contains an image or audio reference without an enabled content capability
- **THEN** content remains unavailable and neither a transcript nor visual observation is fabricated

### Requirement: Cross-adapter authority and conditional effects

The runtime SHALL bind every material fact to its designated authority and current revision, including case/object identity, consent, risk and operation policy. An enabled write SHALL require a provider-side conditional guarantee covering all material preconditions or an evidenced equivalent. Local locking, a fresh read or model confidence SHALL NOT substitute for that external guarantee.

#### Scenario: Consent changes between discovery and dispatch
- **WHEN** consent is revoked after a preflight read but before the conditional effect
- **THEN** the offline provider rejects the stale authority revision and no business effect is verified

#### Scenario: Native API protects only one material record
- **WHEN** a future provider versions the schedule but cannot protect a material consent or stage precondition and no equivalent guarantee is evidenced
- **THEN** the affected business write stays disabled rather than assuming cross-provider atomicity

### Requirement: Structured input profiles preserve semantics

The integration bundle SHALL support explicit versioned mappings for flat JSON and nested envelopes into one strict canonical request contract. Mapping SHALL preserve request/case/object/principal binding, evidence, authority revisions and unavailable content. Missing mandatory intent or authority SHALL route to permitted clarification/handoff rather than guessed business effects. Runtime SHALL NOT modify mappings or policy from incoming content.

#### Scenario: Same request arrives without text
- **WHEN** equivalent authenticated structured intent and authority arrive in flat and nested no-text profiles
- **THEN** both yield the same canonical intent and permitted operation without requiring a model or transcript

#### Scenario: Nested envelope contains policy-changing instructions
- **WHEN** an untrusted message attempts to redefine operation permissions or authoritative facts
- **THEN** mapping retains it as untrusted content and does not change manifest or policy

### Requirement: Message and operator outcomes remain distinct

Customer messages SHALL use constrained kinds, authorized recipients and wording grounded in observed per-effect state. Message acceptance SHALL NOT imply delivery. Operator receipt SHALL verify case, packet identity, owner and receipt evidence independently of any decision. Resume SHALL require authenticated, scoped, fresh case/version-bound decisions with expiry and replay checks.

#### Scenario: Return request is only acknowledged
- **WHEN** return initiation is acknowledged but unverified
- **THEN** a customer status message does not claim return completion, physical receipt or refund

#### Scenario: Queue acknowledges without durable owner receipt
- **WHEN** transport accepts a handoff but authoritative receipt is missing
- **THEN** handoff remains pending or unknown and does not authorize resume or final completion

### Requirement: Public patterns do not establish native capability

Offline profiles MAY resemble first-party public task/order, inventory, time-window, response and return-state documentation. They SHALL identify source/version and simulated guarantees. They SHALL NOT claim a native Dwelly/event contract, live vendor connection, conditional atomicity or exactly-once guarantee merely from resemblance or public documentation.

#### Scenario: Public lifecycle prevents a scheduling write
- **WHEN** a source-inspired profile restricts active-task updates while a customer requests rescheduling
- **THEN** the profile does not infer scheduling capability from the customer request and the unsupported business effect is disabled

### Requirement: Reviewed process versions govern adaptation

The integration bundle SHALL provide a finite versioned ProcessSpec covering allowed operations, prerequisites, approval/wait states, acknowledgement interpretation, authoritative readback and completion. Adapter/process/policy activation SHALL require a source-grounded proposal, changed tests, regression, migration impact and human approval. Pending intents SHALL retain original process/policy versions, fingerprints, keys and postconditions until authoritative reconciliation or explicit compatible migration. Runtime content SHALL NOT activate changes.

#### Scenario: Business rejection uses successful HTTP transport
- **WHEN** a changed profile acknowledges transport successfully but rejects the requested operation in its business envelope
- **THEN** the adapter preserves rejection, the process does not proceed as if its prerequisite succeeded and no verified business completion is emitted

#### Scenario: Release changes readback meaning with an unfinished intent
- **WHEN** a new adapter/process release changes completion interpretation while an older effect remains unknown
- **THEN** recovery retains the old contract and cannot reinterpret the unfinished effect under the new meaning or resend with a fresh key
