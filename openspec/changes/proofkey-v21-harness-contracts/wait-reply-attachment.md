# Wait reply source attachment — atomic current-token refinement

Implementation correction inside approved Task7 one-use/current-control requirements, not a new workflow/grant. Original complete consumer2a0ddea independently reviewed; ImportantI1 reproduced lawful competing public stop between post-consume compare and ordinary save_checkpoint. Sticky stop/counters held and zero business dispatch occurred, but newer stopped phase/nextgate were overwritten. Root read full report and inspected the exact consumer/store boundary. This refinement fixes that write, not generic journal CAS or source custody.

## Closed host-only seam

Add CaseStore.attach_wait_reply_sources_atomic(question_id, expected_consumed, observations) -> PhaseCheckpoint. It is a trusted internal host API, never a body/tool/model transport. Existing consume_wait_reply_atomic signature/one-use semantics and WaitRecord/wire/schema remain unchanged; saved private acceptedreply is never authority data.

Inside ONE existing creator-thread SQLite transaction:

1. Strictly revalidate expected PhaseCheckpoint and bounded immutable/typed AuthorityObservation sequence (max64, unique authority.fact, exact bound object, nonempty evidence and existing timestamp validation). Copy detached observations, never a caller-provided replacement checkpoint/control object.
2. Load exact tagged wait. Require lifecycleanswered, exact binding/frozenversions/acceptedreply linkage, successor_hash equal fingerprint(expected_consumed), expected observations empty, no question/awaitedfields, declared accept successor/nextoperation, retained predecessor ownershiptuple and no stop.
3. Read actual current checkpoint INSIDE that same transaction and require complete equality to expected_consumed, currentgenerationstop false and the same current binding/version/owner/phase/deadline/accounting token. Any changed control OR budget invalidates attachment conservatively; never merge stale control into new state.
4. Construct new checkpoint by changing ONLY observations on that exact current value; all other fields/counters/stop/ownership/deadlines/phase/nextgate remain exact. Write through existing audited checkpoint writer within the same transaction. Do not update immutable consumed successor receipt to claim a new accept, reconsume reply or mint sourceproof. No source/transport/read/debit occurs in this local write.

On mismatch/invalid payload/commit failure raise generic JournalFailure and preserve newer checkpoint, durable answered reply and existing debt. No automatic reread, retry, resend, budgetreset or conversion to nonexecution. A new host public entry still uses its current authorization gate; this local already-consumed evidence attachment does not create a fresh physical lease or extend an expired deadline.

WaitService.accept uses the public atomic method directly with the saved consumed successor and just-read source observations, removing the separate check plus ordinarysave window. It does NOT access store SQL/_transaction/privatehelpers or copy reply.fields into observations. Source validation remains the same four leased gateway reads and current configured reply/scope checks. Engine currentcreator guard remains; different lawful owner-thread journal connections remain supported rather than globally pretending no concurrency.

## Exact staged ownership and evidence

Four files: waits.py, minimaljournal.py new method, existingtest_waits.py NEWmethods only, NEWtest_wait_reply_attachment.py. Engine/gateway/othercontracts/storehelpers/source/profile/fixtures/schema/process/support/oldtests are readonly. Scope expansion from the original C2 consumer-only ownership is explicitly root-owned because the missing atomic storage seam cannot be repaired with another nontransactional check; no privateSQL fallback.

Behavioral TDD: actual public customerreply+real secondcreator-thread public stop at the post-consume attachment boundary; baseline must lose stopped phase/nextgate, fixed path must preserve the exact newer checkpoint and one-use answered state. Hook actual oldsave boundary for RED and newatomic entry for GREEN without counting missingattribute scaffolding as productRED. No source receipt fabrication/SQLstate edits. Validuncontended customer and trueoperator source-only positives remain; malformed/foreign/duplicate observationpayload and changed expected token failclosed; reopened answer/control/debt preserved and no secondreply/communication/business effect. Existing genuine consume-before-attachment crash boundary remains distinct and unchanged.

One focused named covering cohort includes newstorage tests, waits/stop/operator, reviewed storagecontrol/profile/replay and executionstorage contracts; root coordinates actual frozen bytes. Exactdiff/report plus DIFFERENT NONAUTHOR scoped I1 re-review required. No C2/M1/native/model/timedreadiness claim until gate closes.
