# Complete retained journal state — adaptation prerequisite

9 October2026. Internal Task13B1 boundary of the already approved adaptation plan. Capture is the smallest prerequisite, not release activation or migration. Own exactly NEW runtime/src/proofkey/retained_state.py, existing runtime/src/proofkey/journal.py and NEW runtime/tests/test_retained_state.py. Root coordinates the shared journal hold before implementation GO. No schema/core contracts/host/source/registry/profiles/old tests/fixtures/package/CLI/API/lock edits.

## Public interface and private immutable payload

RetainedStateClock has now()->aware datetime and monotonic()->finite float. Frozen/slotted RetainedStateLimitsV1 fields/default/hard ceilings: max_rows4096, max_row_bytes262144, max_payload_bytes4194304, max_capture_seconds5.0, max_sqlite_steps1000000. Exact positive types, no bool/nonfinite/zero/negative; trusted limits may only lower ceilings.

max_row_bytes counts the exact complete canonical encoded row array including brackets, commas and scalar escaping; necessary raw-length or conservative expansion estimates cannot replace exact-limit acceptance.

Frozen/slotted RetainedStateSnapshotV1 contains exact kind="case-store-retained-state-v1", schema_version=1, schema_hash, complete payload bytes, content_hash=SHA256(payload), table_counts tuple of(table-name,int), total_rows, captured_at, finished_at, elapsed_seconds. Validate detached immutable exact types, canonical complete bytes and count/hash/timing consistency. Complete payload is private original content, never automatic command/export material, authority proof, compatibility or approval. No arbitrary paths/SQL/filters/case lists/release hashes/pending-intent shortcuts. Pure companion encoding has no DB/source/registry access.

captured_at preserves supplied execution.captured_at; finished_at is the actual final UTC sample; elapsed_seconds is the actual monotonic difference from original captured_monotonic, including setup. UTC values must be aware/nondecreasing and elapsed finite/nonnegative within the original bounded duration, without assuming wall-clock and monotonic deltas are identical.

CaseStore.capture_retained_state(*,execution:ExecutionContext,clock:RetainedStateClock,limits:RetainedStateLimitsV1=RetainedStateLimitsV1())->RetainedStateSnapshotV1 is creator-thread-only, open, no active transaction/execution_scope. It requires the exact supplied original UTC/monotonic context, original duration at most max_capture_seconds and unexpired current window; no fresh/recaptured anchor, timing renewal or budget funding.

## Complete deterministic image

Include ALL16 fixed schema tables including empty tables and EVERY exact checked-in column/scalar: admission_accounts/admission_attempts/admission_audit/admission_entries/audit/campaigns/cases/entries/intents/invocations/original_requests/requests/results/schema_meta/transfers/waits. Tables lexical order, columns schema order, rows explicit primary-key order: claimed_case_id/attempt_id/sequence/entry_id/sequence/permit_hash/case_id/entry_id/action_id/invocation_id/(case_id,generation)/(case_id,generation)/(case_id,generation)/singleton/transfer_id/question_id respectively.

Canonical UTF-8 JSON payload contains fixed domain, schema_version, exact actual checked schema DDL inventory(type,name,sql) and tables[{name,columns,rows}], sorted object keys/compact separators/UTF-8/noNaN. Every row's SQL TEXT/INTEGER/NULL permitted by fixed schema is retained; stored JSON stays exact original TEXT, not model projection/reserialization. Full schema participates in content_hash; timing does not, so unchanged logical state is stable across reopening/capture times. Derive counts from actual complete rows, not supplied assertions. Schema equality/version, unknown/missing/extra objects/columns and invalid scalar types fail closed.

schema_meta's "singleton" order means its single validated version row, not a nonexistent singleton column or schema change.

## One bounded read transaction

Inside existing execution_scope preserve/restore original connection busy-timeout/deadline behavior; install temporary SQLite progress handler every at-most1000 VM steps enforcing original deadline/max_sqlite_steps, clear on EVERY exit. Validate UTC and monotonic window between schema/rows/validation/encoding. No durability setting changes or hard OS cancellation guarantee.

Use read BEGIN, not write _transaction(), first schema query pins one SQLite snapshot. Bound schema inventory rows and each scalar BEFORE existing schema validation. Stream fixed-table preflight keys and SQL scalar byte lengths globally at most max_rows+1, bound row/aggregate materialization before fetching unchecked huge TEXT or calling _validate_all(). Account encoding/escaping overhead and actual incremental payload bytes. No caller SQL/column names or unbounded fetch-first workaround.

After bounded preflight require existing complete data/schema validation INSIDE SAME read snapshot under step/time guard, then copy every scalar, encode/hash/count. Corrupt/deep/malformed JSON, broken joins/orphans/identities or validation/storage failures deny; no empty/partial success. A concurrent WAL writer may commit, but returned data is entirely the original snapshot. Commit read transaction, final deadline check, return only complete object. Any failure rolls back read transaction, clears handler/restores busy timeout and leaves ordinary store operations usable even after expiry.

Raise JournalFailure with finite safe reason only: retained_state_scope|retained_state_limit|retained_state_timeout|retained_state_invalid|retained_state_storage. Never leak captured contents/raw SQL/error path. No rows/stops/budgets/quota/debt/source/receipts/release selection mutate. Snapshot is as-of, NOT current-state lease; no misleading assert_current helper. Future atomic selection must recapture/revalidate in its separate serialized multi-resource protocol.

## Behavioral TDD and bounded gate

Genuine RED then minimal implementation: empty valid16-table complete image, two cases/older stopped successor/history/unknown effect/wait/ownership/invocation/campaign and admission debt WITHOUTcase, actual original/scalar/debt preservation, immutable count/hash checks, reopen stable logical hash and public mutation changed hash. Deterministic second WAL writer between table reads must yield wholly-before image then wholly-after recapture, not mixed joins.

Exact/one-over rows/scalars/encoded payload/SQL steps/deadline and backwards/exhausted/foreign-thread/nested/corrupt schema/JSON/joins fail without success/mutation; subsequent normal operation proves transaction/handler restoration. New test-owned forwarding barriers only, no production capture hook/oldtest invocation/real DB modifications. Reserve/settled/overrun/unknown accounting unchanged, no budgets refunded/debited/renewed.

Focused author TDD then frozen actual named source/test/schema/profile closure, ONE final amended cohort including selected existing journal controls only after root coordinated hold/GO. Root proportionate verification/exact3 commit/DIFFERENT NONAUTHOR separate Spec+Quality gate. Larger no-writer whole-suite remains final obligation.

## Explicit unimplemented downstream gates

This does not provide complete multi-resource registry/source-world/host-queue capture, durable complete release recipes/authenticated coding+human review, exact generation/resource routing/shared debt, compatible executable changed Process, owner admin lane/atomic durable selection/restart/crash migration or four600-second drills. Immutable current ProfileRegistry/fixed HostDispatcher are real foundations, not activation; do not implement registry/activation pointer-only shortcut or repin old recipes as new evidence. Native/actual human/provider/model/media/rights/install/publication remain unqualified. No network/install/service/server/spend/authority changes.
