## ADDED Requirements

### Requirement: Adaptation is one exact opt-in semantic delta
The system SHALL admit only trusted factory `fixed-synthetic-window-readiness-v3`, profile `flat-window-readiness-v1` in family `v1.3`, window process `reschedule-window-readiness-v2` version `v2-window-readiness`, and scheduling capability `synthetic-scheduling-dual-v1`, against baseline `flat-v1.3` hash `5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4`. It SHALL replace the direct readiness edge with the declared `window_readiness` phase, its `read_authority` continuation and existing stop/operator escapes, append exactly the S0 prerequisite, and change only the declared reschedule acknowledgement/readback contracts and derived identities/hashes. The complete semantic diff SHALL be exactly `capabilities` and `processes`; affected old identities SHALL be exactly `capability:reschedule:v1.1` and `process:reschedule_window:v1`. All other process definitions, policy, mapping, authority, permission, idempotency, conditional coverage, terminal basis, timeout and account limits SHALL remain unchanged.

#### Scenario: Exact candidate is proposed
- **WHEN** trusted material supplies the exact semantic delta and matching independently fixed source registration
- **THEN** the factory accepts that delta for subsequent bound regression checks
- **AND** review material identifies exact-slot as a consumer of the narrowed scheduling-read contract without inventing a changed exact-slot process identity.

#### Scenario: An unlisted semantic change is mixed in
- **WHEN** material changes another phase, edge, prerequisite, process, policy, permission, source account or capability field, omits a changed sibling, reuses old identity, or changes the S0 prerequisite
- **THEN** validation rejects it before qualification even when submitted source hashes match.

### Requirement: Readiness is four independently leased source operations
The candidate window engine SHALL save next gate `read_authority` and obtain readiness through `ActionGateway.read_window_readiness(case_id)`, with no caller-supplied fact set, value, authority or deadline. The helper SHALL require current engine authentication, owner-thread active execution/timing, exact candidate checkpoint and stored original window request, original bound versions/deadline, phase `window_readiness`, and no stop. It SHALL call `case.read_case` for four identity facts, `case.read_principal` for consent revision, `operator.read_owner` for four ownership facts, and `scheduling.list_permitted_slots` for slot, in that order, each with its own lease/debit and existing ACL/freshness/pace/reservation/settlement.

#### Scenario: Ready source is independently observed
- **WHEN** all nine identity/owner facts validate and the fourth read yields fresh scoped string `S0`
- **THEN** all four physical reads are visible with separate accounting
- **AND** the engine replaces returned qualified observations in the latest checkpoint and advances only after successful guarded save.

#### Scenario: Owner identity differs despite matching epoch
- **WHEN** the source owner ID differs from authenticated caller, is empty or has an invalid type while epoch/revision otherwise match
- **THEN** the wrapped owner validator rejects before settling that read as valid
- **AND** the helper does not grant packet access or advance to business dispatch.

#### Scenario: Readiness is unavailable or forged
- **WHEN** identity, request revision, consent revision or ownership validation fails, scheduling is unavailable, slot is missing/malformed/not S0, or request input merely asserts S0
- **THEN** source readiness is not satisfied and no business dispatch follows
- **AND** the workflow remains unavailable at readiness without manufactured operator reply or physical handoff.

### Requirement: Readiness retains original state and timing fences
The helper SHALL recheck binding, phase, next gate, profile/process/policy versions, owner state/revision/epoch, stop, original deadline and registered execution before scheduling and after the final read. Registered guards SHALL use ordinary execution entry, not control authority. Saving SHALL retain the latest debited budget and sticky stop. The full fresh pre-write material/policy check and provider CAS SHALL enforce S0 again for the exact candidate window process. No check SHALL require S0 on original-effect readback after rescheduling.

#### Scenario: State changes during readiness
- **WHEN** stop, deadline, owner or bound state changes between reads or before final save, or the journal save fails
- **THEN** the workflow does not advance or overwrite that newer state
- **AND** it neither restores the captured pre-read budget nor creates a fresh intent, generation or deadline.

#### Scenario: Slot races after readiness
- **WHEN** the source moves away from S0 after the readiness read, including an otherwise-current direct candidate intent
- **THEN** the fresh pre-write check or provider source/CAS gate prevents the reschedule
- **AND** subsequent original readback still uses original identity, not current readiness.

#### Scenario: Positive full path exceeds its original allowance
- **WHEN** admission, four readiness reads, later material checks, dispatch and readback do not fit the unchanged 24-call, 120-second active and 10-second tool bounds
- **THEN** qualification fails with an explicit fit blocker
- **AND** no limit is raised and no physical read is hidden to produce a pass.

### Requirement: Raw source bytes precede adapter normalization
The synthetic world SHALL expose private raw scheduling entrypoints returning UTF-8 JSON bytes assembled from private source transaction/read data before public normalization. Legacy typed results SHALL use the common source data through their original typed path. Public scheduling-port signatures SHALL remain unchanged. Every candidate scheduling read SHALL use raw decoding; only candidate window dispatch SHALL use raw dispatch, while candidate exact-slot dispatch remains typed.

#### Scenario: Legacy observation validation precedes commitment
- **WHEN** a legacy typed dispatch generates an observation with an invalid optional source revision, even if all required material revisions are valid
- **THEN** its original typed observation validation fails inside the source transaction before any effect is committed
- **AND** all transaction-owned source mutations roll back, with no acknowledged invalid original
- **AND** valid typed dispatches retain typed observation JSON serialization, while candidate raw scheduling bytes remain assembled from raw source data rather than a serialized public result.

#### Scenario: Distinct source response is exercised
- **WHEN** trusted fault `http200_business_failed` executes for candidate window dispatch
- **THEN** raw bytes contain HTTP 200 and business_failed while no effect or terminal row exists
- **AND** tests observe raw bytes, adapter output and independent final result separately, without serializing a pre-normalized public result to manufacture the raw test.

#### Scenario: Version or consent mode is swapped
- **WHEN** candidate window v2 is paired with exact-slot source consent or exact-slot v1 with window source consent, or v2 is requested for undeclared goods/service behavior
- **THEN** compatibility validation rejects the combination
- **AND** legacy dispatch semantics remain unchanged.

### Requirement: Raw envelopes have an exact finite decoding domain
The adapter SHALL validate the exact dispatch/read/nested schemas and source field meanings defined in the design before constructing public results. The discriminator SHALL be `synthetic-scheduling-envelope-v1`, outer operation SHALL match the invoked method, and nullable fields SHALL be explicitly present. It SHALL preserve source identity, timestamps and evidence without filling from expectations. Limits SHALL be inclusive: 262144 complete UTF-8 bytes, container depth 16 with root depth 1, 128 observations, identifier/revision/reason length 1024 Unicode code points, and 128 total evidence-reference occurrences including repeated body, observation and nonexecution references. All limits SHALL apply together. Duplicate/missing/unknown keys, invalid UTF-8/JSON, nonfinite numbers, coercions, wrong types, unknown discriminator and wrong operation SHALL be rejected.

#### Scenario: All fields are valid within bounds
- **WHEN** a complete HTTP 200 read envelope meets the raw schema and every bound
- **THEN** the adapter returns the exact validated body
- **AND** gateway scope, freshness, exact-fact-set and original verification still decide whether it is usable evidence.

#### Scenario: Boundary values differ by one
- **WHEN** tests compare bytes 262144/262145, depth 16/17, observations 128/129, evidence occurrences 128/129, and reference length 1024/1025
- **THEN** valid values at each limit are accepted only if all other requirements hold and values above any limit are rejected
- **AND** the 129-observation test explicitly reports its unavoidable simultaneous evidence-occurrence violation rather than claiming an isolated observation-limit test.

#### Scenario: An envelope attempts ambiguous decoding
- **WHEN** duplicate keys, omitted nullable keys, unknown nested keys, stringified numbers, boolean numeric values, malformed timestamps or a mismatched outer method occur
- **THEN** no partial body or fabricated readback escapes the bounded decoder.

### Requirement: Ambiguous dispatch and unreadable originals cannot imply success or resend
Only a valid HTTP 200 acknowledged dispatch with nonempty provider ID and evidence SHALL normalize to acknowledged, preserving source fields. Every other candidate raw dispatch result, including rejected, business_failed, outcome_unknown, non-200 acknowledgement, 429/503, malformed/over-bound bytes and exceptions, SHALL normalize to outcome_unknown with null provider ID, empty evidence and reason `synthetic_envelope_unresolved`. Acknowledgement SHALL require independent original readback. Candidate read errors SHALL raise one bounded adapter contract error, yielding authority unavailable/scope-denied or original `outcome_unknown/original_read_unavailable`.

#### Scenario: HTTP metadata disagrees with business content
- **WHEN** raw status is HTTP 200 business_failed or non-200 acknowledged
- **THEN** dispatch remains unknown and only independent matching original evidence can establish a final result.

#### Scenario: An already committed effect has unreadable readback
- **WHEN** original readback is malformed, out of domain, unavailable or throws after an effect may have committed
- **THEN** the original key, intent, effect and debt remain retained with unknown outcome
- **AND** there is zero resend, undo, truncation, deletion, migration or typed fallback.

### Requirement: Automatic terminal proof belongs only to a validated window original
Window raw dispatch SHALL mint the provider-owned `provider:window-envelope-v1:` full-digest request ID only after exact candidate and source validation. Its hash input SHALL contain domain `synthetic-window-original-v1`, provider account, provider key, case, object, operation, generation, action, argument fingerprint and full serialized-intent identity hash. Equal-intent repeat keys SHALL reuse their stored ID; conflicting intent identity, malformed stored namespace or a request-ID collision across either source table SHALL fail closed. The transaction SHALL preserve existing idempotency ordering and require no new DDL.

#### Scenario: Exact independent terminal row exists
- **WHEN** an ACL-authorized, timely raw original reschedule read joins account, case, object, operation, generation, action, provider key and fingerprint, finds zero effects and exactly one valid terminal row, recomputes its exact full window digest and validates supported terminal basis and aware nonfuture creation time
- **THEN** it can return independent terminal proof without the legacy terminal fault knob
- **AND** every raw bound and final tool-deadline check still applies.

#### Scenario: Original identity or storage is inconsistent
- **WHEN** any of the eight join fields mismatches, namespace/digest/identity hash/time is altered, only a prefix matches, rows are nonunique, or both effect and terminal rows exist
- **THEN** lookup returns unknown/unavailable without proof
- **AND** no lookup by latest business ID, current slot, consent mode or caller purpose substitutes for the full original join.

#### Scenario: Collision or replay is attempted
- **WHEN** a forced request-ID hash collision names another original or the same provider key carries a different complete intent
- **THEN** insertion is denied with no second row
- **AND** an equal-intent repeat retains its original stored ID and original effect count.

#### Scenario: Exact-slot rejection retains legacy gate
- **WHEN** in-domain baseline and candidate exact-slot originals use final_rejection_unknown
- **THEN** both remain unknown without terminal_not_executed and both can expose matching terminal proof with that knob
- **AND** candidate window proof does not require the knob, caller purpose changes none of these outcomes, and revoked ACL or early read faults prevent disclosure.

#### Scenario: Retained source validates the committed original
- **WHEN** an exact-candidate reschedule effect or terminal row uses the full window request-ID namespace
- **THEN** retained-source capture SHALL validate the same full explicit-field digest before admitting that row
- **AND** every other row/profile SHALL retain its legacy request-ID rule, while invalid rows remain rejected and unchanged rather than repaired or deleted.

### Requirement: Compatibility claims name the supported raw domain
Current-source candidate exact-slot comparisons SHALL claim equivalent corresponding results only for well-formed responses inside every raw bound. Legacy-valid out-of-domain responses SHALL explicitly fail unavailable/unknown in the candidate with no fallback. Unchanged process bytes SHALL NOT be described as universal input-domain compatibility. Legacy typed profiles and non-scheduling behavior SHALL retain their own regression obligations.

#### Scenario: Legacy accepts a longer reference
- **WHEN** a valid scheduling slot evidence reference has 1025 ASCII characters and all other fixture constraints hold
- **THEN** baseline typed authority read accepts it while candidate raw authority read is unavailable
- **AND** a fresh candidate workflow performs zero business dispatches, a valid 1024-character contrast is tested, and the denial is not labelled a parity pass.

### Requirement: Independent source closure never repins old state
The candidate SHALL use an independent sorted literal tuple of the 86 package Python/schema path names listed in the design, with independent final hashes; it SHALL NOT alias stop-v2's tuple or dynamically accept a glob. No package module SHALL be added. The existing stop-v2 tuple and all-package equality test SHALL remain unchanged. Preparation and revalidation SHALL reject missing, extra, substituted or stale implementation bytes, and separate profile resource commitments SHALL bind the exact mirror bytes. Historical pins, receipts and serialization vectors SHALL NOT be rewritten as current qualification.

#### Scenario: Current-source hashes differ under the same names
- **WHEN** J05 changes existing module bytes after stop-v2 freezes
- **THEN** J05 records a new independently frozen current-source inventory
- **AND** old registered roots remain paired with their original executable/resources without silent repinning or grant/marker replacement.

#### Scenario: Inventory closure is weakened
- **WHEN** a path is missing, added, aliased, duplicated, unsorted or supplied with stale bytes, or the tuple merely delegates to stop-v2's constant
- **THEN** candidate qualification fails rather than accepting an expanded executable surface.

### Requirement: Source qualification and historical pending preservation are separate outcomes
The finite leaf SHALL require completed current-source behavior evidence, bound inventories and independent review for its implementation outcome. Reports SHALL separately identify default v1/stop-v2 comparisons, in-domain candidate comparisons and out-of-domain denials. Historical pending preservation SHALL remain unqualified unless an independently identified already-pending original case is checked with its exact old executable/dependencies, original registered roots, authority, supported entrypoints, saved identities/versions/deadlines/debts and before/after effect/read accounting. Completion of current-source tasks SHALL NOT close that historical gate or parent J05.

#### Scenario: Only the discovered completed J06 pair exists
- **WHEN** the available historical case is complete with a verified reschedule and no waits, even if processing_status says pending
- **THEN** it can support only a labelled completed-history comparison
- **AND** pending preservation stays unqualified and the parent acceptance remains open.

#### Scenario: A substitute is offered as historical evidence
- **WHEN** a fresh fixture, relocated current package, repinned route, copied evidence root or recreated grant is offered instead of the original pending pair
- **THEN** it cannot pass historical pending preservation
- **AND** copied roots forbidden for runtime reuse remain unused.

#### Scenario: Local implementation checks pass
- **WHEN** source behavior and all finite child checks pass
- **THEN** reporting is limited to that observed synthetic source scope
- **AND** it does not claim a new installed artifact, native HTTP/live provider, actual human review, activation, migration, retained resolver or completed timed drill.

#### Scenario: Changed source no longer matches old qualification pins
- **WHEN** current-source comparisons run after the exact J05 package changes
- **THEN** they SHALL use an explicitly named independently frozen current lane, preserve old fixture/vector bytes and affirm the unchanged default legacy lane's rejection of changed source
- **AND** final full discovery SHALL pass without skipped incompatibilities, while exact inner behavioral test identities exclude outer or recursive qualification runners.
