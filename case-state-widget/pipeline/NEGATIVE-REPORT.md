# Negative branch annotation report

The viewer dataset includes all **275 negative branches** from the authored branch index, alongside the **50 reviewed public cases**. This adds 274 JSONs and repairs the existing 002-N4 reference’s initial limit and inherited gap placement. The source histories are unchanged.

## Build and evidence

- Each branch retains every reviewed parent state before divergence. Case id, branch-wide limits and intake source id are the only intentional prefix metadata differences.
- Source messages, timestamps and sender/recipient mappings match the authored histories exactly. New actors appear at the first source event or permitted planned request.
- Each annotated branch pins SHA-256 hashes of its source index and history.
- The desk decision offers the permitted response and the tempting prohibited action; the recorded outgoing event selects only the permitted option.
- The final source reply defines the completion scope. Registration is not an operator decision; customer choice is not a booking; a deadline reminder is not consent; a credit is not cash.
- Original criteria outside the alternative task remain historical snapshots in `prior_success_criteria` with their status at the scope change. They are never changed to met to force closure.
- Original missing handoffs are retained and clarified after divergence. Implied intermediate exchanges have a source event and `implied_action`; no extra chat messages are generated.

The 274 added branches use source-grounded rule annotation. The existing 002-N4 keeps its specific reviewed annotations. This report records source and engine checks, not a claim of an independent expert review of every synthetic scenario.

## Validation

- 325/325 JSONs pass the repository viewer, schema, patch replay, source-message comparison and chronological evidence checks, with no warnings.
- Seven dataset regression tests pass: complete coverage and reproducibility, exact parent prefixes, source fingerprints and messages, no early closure, all 34 uncertain-outcome checks, deadline silence, and measured information versus choice.
- The full widget test command passes, including the existing standalone tests and 46 Node test-runner cases.
- All 50 public JSONs are unchanged from the reviewed baseline.

## Failure modes

| Failure mode | Branches |
|---|---:|
| AMBIGUOUS_REPLY | 16 |
| CHANNEL_FAILURE | 34 |
| CONFLICTING_RECORDS | 43 |
| CUSTOMER_CANCELS | 17 |
| DUPLICATE_REQUEST | 15 |
| NEEDS_HUMAN | 7 |
| NO_REPLY | 18 |
| OUT_OF_POLICY_ASK | 31 |
| PHYSICAL_FAILURE | 10 |
| SNAPSHOT_CONFLICT | 10 |
| STALE_STATE | 34 |
| UNAUTHORISED_REPLY | 40 |

## Inventory

| Branch | Failure mode | Expected response | Annotation |
|---|---|---|---|
| [001-N1](../cases/001-N1.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/001-N1.json) |
| [001-N2](../cases/001-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/001-N2.json) |
| [001-N3](../cases/001-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/001-N3.json) |
| [001-N4](../cases/001-N4.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/001-N4.json) |
| [001-N5](../cases/001-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/001-N5.json) |
| [002-N1](../cases/002-N1.json) | SNAPSHOT_CONFLICT | SEPARATE_AUTHORITY | [source](../annot/002-N1.json) |
| [002-N2](../cases/002-N2.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/002-N2.json) |
| [002-N3](../cases/002-N3.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/002-N3.json) |
| [002-N4](../cases/002-N4.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/002-N4.json) |
| [002-N5](../cases/002-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/002-N5.json) |
| [003-N1](../cases/003-N1.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/003-N1.json) |
| [003-N2](../cases/003-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/003-N2.json) |
| [003-N3](../cases/003-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/003-N3.json) |
| [003-N4](../cases/003-N4.json) | STALE_STATE | GET_OPTIONS | [source](../annot/003-N4.json) |
| [003-N5](../cases/003-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/003-N5.json) |
| [003-N6](../cases/003-N6.json) | PHYSICAL_FAILURE | RECORD_REFUSAL | [source](../annot/003-N6.json) |
| [004-N1](../cases/004-N1.json) | SNAPSHOT_CONFLICT | DECLINE_EXPLAIN | [source](../annot/004-N1.json) |
| [004-N2](../cases/004-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/004-N2.json) |
| [004-N3](../cases/004-N3.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/004-N3.json) |
| [004-N4](../cases/004-N4.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/004-N4.json) |
| [004-N5](../cases/004-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/004-N5.json) |
| [004-N6](../cases/004-N6.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/004-N6.json) |
| [005-N1](../cases/005-N1.json) | SNAPSHOT_CONFLICT | DECLINE_EXPLAIN | [source](../annot/005-N1.json) |
| [005-N2](../cases/005-N2.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/005-N2.json) |
| [005-N3](../cases/005-N3.json) | STALE_STATE | GET_OPTIONS | [source](../annot/005-N3.json) |
| [005-N4](../cases/005-N4.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/005-N4.json) |
| [005-N5](../cases/005-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/005-N5.json) |
| [005-N6](../cases/005-N6.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/005-N6.json) |
| [006-N1](../cases/006-N1.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/006-N1.json) |
| [006-N2](../cases/006-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/006-N2.json) |
| [006-N3](../cases/006-N3.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/006-N3.json) |
| [006-N4](../cases/006-N4.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/006-N4.json) |
| [006-N5](../cases/006-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/006-N5.json) |
| [006-N6](../cases/006-N6.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/006-N6.json) |
| [007-N1](../cases/007-N1.json) | STALE_STATE | GET_OPTIONS | [source](../annot/007-N1.json) |
| [007-N2](../cases/007-N2.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/007-N2.json) |
| [007-N3](../cases/007-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/007-N3.json) |
| [007-N4](../cases/007-N4.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/007-N4.json) |
| [007-N5](../cases/007-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/007-N5.json) |
| [007-N6](../cases/007-N6.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/007-N6.json) |
| [008-N1](../cases/008-N1.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/008-N1.json) |
| [008-N2](../cases/008-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/008-N2.json) |
| [008-N3](../cases/008-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/008-N3.json) |
| [008-N4](../cases/008-N4.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/008-N4.json) |
| [008-N5](../cases/008-N5.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/008-N5.json) |
| [009-N1](../cases/009-N1.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/009-N1.json) |
| [009-N2](../cases/009-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/009-N2.json) |
| [009-N3](../cases/009-N3.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/009-N3.json) |
| [009-N4](../cases/009-N4.json) | NEEDS_HUMAN | ESCALATE_OPERATOR | [source](../annot/009-N4.json) |
| [009-N5](../cases/009-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/009-N5.json) |
| [009-N6](../cases/009-N6.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/009-N6.json) |
| [010-N1](../cases/010-N1.json) | SNAPSHOT_CONFLICT | DECLINE_EXPLAIN | [source](../annot/010-N1.json) |
| [010-N2](../cases/010-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/010-N2.json) |
| [010-N3](../cases/010-N3.json) | STALE_STATE | GET_OPTIONS | [source](../annot/010-N3.json) |
| [010-N4](../cases/010-N4.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/010-N4.json) |
| [010-N5](../cases/010-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/010-N5.json) |
| [010-N6](../cases/010-N6.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/010-N6.json) |
| [011-N1](../cases/011-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/011-N1.json) |
| [011-N2](../cases/011-N2.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/011-N2.json) |
| [011-N3](../cases/011-N3.json) | PHYSICAL_FAILURE | REQUEST_ACTION | [source](../annot/011-N3.json) |
| [011-N4](../cases/011-N4.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/011-N4.json) |
| [011-N5](../cases/011-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/011-N5.json) |
| [011-N6](../cases/011-N6.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/011-N6.json) |
| [012-N1](../cases/012-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/012-N1.json) |
| [012-N2](../cases/012-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/012-N2.json) |
| [012-N3](../cases/012-N3.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/012-N3.json) |
| [012-N4](../cases/012-N4.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/012-N4.json) |
| [012-N5](../cases/012-N5.json) | AMBIGUOUS_REPLY | GET_OPTIONS | [source](../annot/012-N5.json) |
| [012-N6](../cases/012-N6.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/012-N6.json) |
| [013-N1](../cases/013-N1.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/013-N1.json) |
| [013-N2](../cases/013-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/013-N2.json) |
| [013-N3](../cases/013-N3.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/013-N3.json) |
| [013-N4](../cases/013-N4.json) | NEEDS_HUMAN | ESCALATE_OPERATOR | [source](../annot/013-N4.json) |
| [013-N5](../cases/013-N5.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/013-N5.json) |
| [014-N1](../cases/014-N1.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/014-N1.json) |
| [014-N2](../cases/014-N2.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/014-N2.json) |
| [014-N3](../cases/014-N3.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/014-N3.json) |
| [014-N4](../cases/014-N4.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/014-N4.json) |
| [014-N5](../cases/014-N5.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/014-N5.json) |
| [015-N1](../cases/015-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/015-N1.json) |
| [015-N2](../cases/015-N2.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/015-N2.json) |
| [015-N3](../cases/015-N3.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/015-N3.json) |
| [015-N4](../cases/015-N4.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/015-N4.json) |
| [015-N5](../cases/015-N5.json) | PHYSICAL_FAILURE | REQUEST_ACTION | [source](../annot/015-N5.json) |
| [016-N1](../cases/016-N1.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/016-N1.json) |
| [016-N2](../cases/016-N2.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/016-N2.json) |
| [016-N3](../cases/016-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/016-N3.json) |
| [016-N4](../cases/016-N4.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/016-N4.json) |
| [016-N5](../cases/016-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/016-N5.json) |
| [017-N1](../cases/017-N1.json) | SNAPSHOT_CONFLICT | DECLINE_EXPLAIN | [source](../annot/017-N1.json) |
| [017-N2](../cases/017-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/017-N2.json) |
| [017-N3](../cases/017-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/017-N3.json) |
| [017-N4](../cases/017-N4.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/017-N4.json) |
| [017-N5](../cases/017-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/017-N5.json) |
| [018-N1](../cases/018-N1.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/018-N1.json) |
| [018-N2](../cases/018-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/018-N2.json) |
| [018-N3](../cases/018-N3.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/018-N3.json) |
| [018-N4](../cases/018-N4.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/018-N4.json) |
| [018-N5](../cases/018-N5.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/018-N5.json) |
| [018-N6](../cases/018-N6.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/018-N6.json) |
| [019-N1](../cases/019-N1.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/019-N1.json) |
| [019-N2](../cases/019-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/019-N2.json) |
| [019-N3](../cases/019-N3.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/019-N3.json) |
| [019-N4](../cases/019-N4.json) | NEEDS_HUMAN | ESCALATE_OPERATOR | [source](../annot/019-N4.json) |
| [019-N5](../cases/019-N5.json) | STALE_STATE | REQUEST_ACTION | [source](../annot/019-N5.json) |
| [020-N1](../cases/020-N1.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/020-N1.json) |
| [020-N2](../cases/020-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/020-N2.json) |
| [020-N3](../cases/020-N3.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/020-N3.json) |
| [020-N4](../cases/020-N4.json) | PHYSICAL_FAILURE | RECORD_REFUSAL | [source](../annot/020-N4.json) |
| [020-N5](../cases/020-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/020-N5.json) |
| [021-N1](../cases/021-N1.json) | SNAPSHOT_CONFLICT | SEPARATE_AUTHORITY | [source](../annot/021-N1.json) |
| [021-N2](../cases/021-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/021-N2.json) |
| [021-N3](../cases/021-N3.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/021-N3.json) |
| [021-N4](../cases/021-N4.json) | AMBIGUOUS_REPLY | GET_OPTIONS | [source](../annot/021-N4.json) |
| [021-N5](../cases/021-N5.json) | NEEDS_HUMAN | ESCALATE_OPERATOR | [source](../annot/021-N5.json) |
| [022-N1](../cases/022-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/022-N1.json) |
| [022-N2](../cases/022-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/022-N2.json) |
| [022-N3](../cases/022-N3.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/022-N3.json) |
| [022-N4](../cases/022-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/022-N4.json) |
| [022-N5](../cases/022-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/022-N5.json) |
| [023-N1](../cases/023-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/023-N1.json) |
| [023-N2](../cases/023-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/023-N2.json) |
| [023-N3](../cases/023-N3.json) | NEEDS_HUMAN | ESCALATE_OPERATOR | [source](../annot/023-N3.json) |
| [023-N4](../cases/023-N4.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/023-N4.json) |
| [023-N5](../cases/023-N5.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/023-N5.json) |
| [023-N6](../cases/023-N6.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/023-N6.json) |
| [024-N1](../cases/024-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/024-N1.json) |
| [024-N2](../cases/024-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/024-N2.json) |
| [024-N3](../cases/024-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/024-N3.json) |
| [024-N4](../cases/024-N4.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/024-N4.json) |
| [024-N5](../cases/024-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/024-N5.json) |
| [025-N1](../cases/025-N1.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/025-N1.json) |
| [025-N2](../cases/025-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/025-N2.json) |
| [025-N3](../cases/025-N3.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/025-N3.json) |
| [025-N4](../cases/025-N4.json) | AMBIGUOUS_REPLY | GET_OPTIONS | [source](../annot/025-N4.json) |
| [025-N5](../cases/025-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/025-N5.json) |
| [026-N1](../cases/026-N1.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/026-N1.json) |
| [026-N2](../cases/026-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/026-N2.json) |
| [026-N3](../cases/026-N3.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/026-N3.json) |
| [026-N4](../cases/026-N4.json) | PHYSICAL_FAILURE | REQUEST_ACTION | [source](../annot/026-N4.json) |
| [026-N5](../cases/026-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/026-N5.json) |
| [027-N1](../cases/027-N1.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/027-N1.json) |
| [027-N2](../cases/027-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/027-N2.json) |
| [027-N3](../cases/027-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/027-N3.json) |
| [027-N4](../cases/027-N4.json) | PHYSICAL_FAILURE | REQUEST_ACTION | [source](../annot/027-N4.json) |
| [027-N5](../cases/027-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/027-N5.json) |
| [028-N1](../cases/028-N1.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/028-N1.json) |
| [028-N2](../cases/028-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/028-N2.json) |
| [028-N3](../cases/028-N3.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/028-N3.json) |
| [028-N4](../cases/028-N4.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/028-N4.json) |
| [028-N5](../cases/028-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/028-N5.json) |
| [029-N1](../cases/029-N1.json) | NEEDS_HUMAN | ESCALATE_OPERATOR | [source](../annot/029-N1.json) |
| [029-N2](../cases/029-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/029-N2.json) |
| [029-N3](../cases/029-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/029-N3.json) |
| [029-N4](../cases/029-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/029-N4.json) |
| [029-N5](../cases/029-N5.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/029-N5.json) |
| [030-N1](../cases/030-N1.json) | SNAPSHOT_CONFLICT | SEPARATE_AUTHORITY | [source](../annot/030-N1.json) |
| [030-N2](../cases/030-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/030-N2.json) |
| [030-N3](../cases/030-N3.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/030-N3.json) |
| [030-N4](../cases/030-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/030-N4.json) |
| [030-N5](../cases/030-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/030-N5.json) |
| [031-N1](../cases/031-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/031-N1.json) |
| [031-N2](../cases/031-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/031-N2.json) |
| [031-N3](../cases/031-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/031-N3.json) |
| [031-N4](../cases/031-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/031-N4.json) |
| [031-N5](../cases/031-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/031-N5.json) |
| [031-N6](../cases/031-N6.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/031-N6.json) |
| [032-N1](../cases/032-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/032-N1.json) |
| [032-N2](../cases/032-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/032-N2.json) |
| [032-N3](../cases/032-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/032-N3.json) |
| [032-N4](../cases/032-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/032-N4.json) |
| [032-N5](../cases/032-N5.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/032-N5.json) |
| [032-N6](../cases/032-N6.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/032-N6.json) |
| [033-N1](../cases/033-N1.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/033-N1.json) |
| [033-N2](../cases/033-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/033-N2.json) |
| [033-N3](../cases/033-N3.json) | PHYSICAL_FAILURE | RECORD_REFUSAL | [source](../annot/033-N3.json) |
| [033-N4](../cases/033-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/033-N4.json) |
| [033-N5](../cases/033-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/033-N5.json) |
| [033-N6](../cases/033-N6.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/033-N6.json) |
| [034-N1](../cases/034-N1.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/034-N1.json) |
| [034-N2](../cases/034-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/034-N2.json) |
| [034-N3](../cases/034-N3.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/034-N3.json) |
| [034-N4](../cases/034-N4.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/034-N4.json) |
| [034-N5](../cases/034-N5.json) | PHYSICAL_FAILURE | ESCALATE_OPERATOR | [source](../annot/034-N5.json) |
| [034-N6](../cases/034-N6.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/034-N6.json) |
| [035-N1](../cases/035-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/035-N1.json) |
| [035-N2](../cases/035-N2.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/035-N2.json) |
| [035-N3](../cases/035-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/035-N3.json) |
| [035-N4](../cases/035-N4.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/035-N4.json) |
| [035-N5](../cases/035-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/035-N5.json) |
| [035-N6](../cases/035-N6.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/035-N6.json) |
| [036-N1](../cases/036-N1.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/036-N1.json) |
| [036-N2](../cases/036-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/036-N2.json) |
| [036-N3](../cases/036-N3.json) | PHYSICAL_FAILURE | REQUEST_ACTION | [source](../annot/036-N3.json) |
| [036-N4](../cases/036-N4.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/036-N4.json) |
| [036-N5](../cases/036-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/036-N5.json) |
| [036-N6](../cases/036-N6.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/036-N6.json) |
| [037-N1](../cases/037-N1.json) | STALE_STATE | GET_OPTIONS | [source](../annot/037-N1.json) |
| [037-N2](../cases/037-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/037-N2.json) |
| [037-N3](../cases/037-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/037-N3.json) |
| [037-N4](../cases/037-N4.json) | PHYSICAL_FAILURE | REQUEST_ACTION | [source](../annot/037-N4.json) |
| [037-N5](../cases/037-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/037-N5.json) |
| [037-N6](../cases/037-N6.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/037-N6.json) |
| [038-N1](../cases/038-N1.json) | SNAPSHOT_CONFLICT | SEPARATE_AUTHORITY | [source](../annot/038-N1.json) |
| [038-N2](../cases/038-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/038-N2.json) |
| [038-N3](../cases/038-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/038-N3.json) |
| [038-N4](../cases/038-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/038-N4.json) |
| [038-N5](../cases/038-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/038-N5.json) |
| [038-N6](../cases/038-N6.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/038-N6.json) |
| [039-N1](../cases/039-N1.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/039-N1.json) |
| [039-N2](../cases/039-N2.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/039-N2.json) |
| [039-N3](../cases/039-N3.json) | STALE_STATE | GET_OPTIONS | [source](../annot/039-N3.json) |
| [039-N4](../cases/039-N4.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/039-N4.json) |
| [039-N5](../cases/039-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/039-N5.json) |
| [040-N1](../cases/040-N1.json) | STALE_STATE | GET_OPTIONS | [source](../annot/040-N1.json) |
| [040-N2](../cases/040-N2.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/040-N2.json) |
| [040-N3](../cases/040-N3.json) | SNAPSHOT_CONFLICT | SEPARATE_AUTHORITY | [source](../annot/040-N3.json) |
| [040-N4](../cases/040-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/040-N4.json) |
| [040-N5](../cases/040-N5.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/040-N5.json) |
| [040-N6](../cases/040-N6.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/040-N6.json) |
| [041-N1](../cases/041-N1.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/041-N1.json) |
| [041-N2](../cases/041-N2.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/041-N2.json) |
| [041-N3](../cases/041-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/041-N3.json) |
| [041-N4](../cases/041-N4.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/041-N4.json) |
| [041-N5](../cases/041-N5.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/041-N5.json) |
| [041-N6](../cases/041-N6.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/041-N6.json) |
| [042-N1](../cases/042-N1.json) | AMBIGUOUS_REPLY | GET_OPTIONS | [source](../annot/042-N1.json) |
| [042-N2](../cases/042-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/042-N2.json) |
| [042-N3](../cases/042-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/042-N3.json) |
| [042-N4](../cases/042-N4.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/042-N4.json) |
| [042-N5](../cases/042-N5.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/042-N5.json) |
| [042-N6](../cases/042-N6.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/042-N6.json) |
| [043-N1](../cases/043-N1.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/043-N1.json) |
| [043-N2](../cases/043-N2.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/043-N2.json) |
| [043-N3](../cases/043-N3.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/043-N3.json) |
| [043-N4](../cases/043-N4.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/043-N4.json) |
| [043-N5](../cases/043-N5.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/043-N5.json) |
| [043-N6](../cases/043-N6.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/043-N6.json) |
| [044-N1](../cases/044-N1.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/044-N1.json) |
| [044-N2](../cases/044-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/044-N2.json) |
| [044-N3](../cases/044-N3.json) | STALE_STATE | ASK_CUSTOMER | [source](../annot/044-N3.json) |
| [044-N4](../cases/044-N4.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/044-N4.json) |
| [044-N5](../cases/044-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/044-N5.json) |
| [044-N6](../cases/044-N6.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/044-N6.json) |
| [045-N1](../cases/045-N1.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/045-N1.json) |
| [045-N2](../cases/045-N2.json) | AMBIGUOUS_REPLY | ASK_CUSTOMER | [source](../annot/045-N2.json) |
| [045-N3](../cases/045-N3.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/045-N3.json) |
| [045-N4](../cases/045-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/045-N4.json) |
| [045-N5](../cases/045-N5.json) | NEEDS_HUMAN | ESCALATE_OPERATOR | [source](../annot/045-N5.json) |
| [046-N1](../cases/046-N1.json) | SNAPSHOT_CONFLICT | ASK_CUSTOMER | [source](../annot/046-N1.json) |
| [046-N2](../cases/046-N2.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/046-N2.json) |
| [046-N3](../cases/046-N3.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/046-N3.json) |
| [046-N4](../cases/046-N4.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/046-N4.json) |
| [046-N5](../cases/046-N5.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/046-N5.json) |
| [046-N6](../cases/046-N6.json) | NO_REPLY | WAIT_WITH_DEADLINE | [source](../annot/046-N6.json) |
| [047-N1](../cases/047-N1.json) | AMBIGUOUS_REPLY | REQUEST_ACTION | [source](../annot/047-N1.json) |
| [047-N2](../cases/047-N2.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/047-N2.json) |
| [047-N3](../cases/047-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/047-N3.json) |
| [047-N4](../cases/047-N4.json) | CHANNEL_FAILURE | VERIFY_FIRST | [source](../annot/047-N4.json) |
| [047-N5](../cases/047-N5.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/047-N5.json) |
| [048-N1](../cases/048-N1.json) | AMBIGUOUS_REPLY | REQUEST_ACTION | [source](../annot/048-N1.json) |
| [048-N2](../cases/048-N2.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/048-N2.json) |
| [048-N3](../cases/048-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/048-N3.json) |
| [048-N4](../cases/048-N4.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/048-N4.json) |
| [048-N5](../cases/048-N5.json) | STALE_STATE | GET_OPTIONS | [source](../annot/048-N5.json) |
| [049-N1](../cases/049-N1.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/049-N1.json) |
| [049-N2](../cases/049-N2.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/049-N2.json) |
| [049-N3](../cases/049-N3.json) | STALE_STATE | GET_OPTIONS | [source](../annot/049-N3.json) |
| [049-N4](../cases/049-N4.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/049-N4.json) |
| [049-N5](../cases/049-N5.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/049-N5.json) |
| [050-N1](../cases/050-N1.json) | OUT_OF_POLICY_ASK | DECLINE_EXPLAIN | [source](../annot/050-N1.json) |
| [050-N2](../cases/050-N2.json) | CONFLICTING_RECORDS | RECONCILE_CONFLICT | [source](../annot/050-N2.json) |
| [050-N3](../cases/050-N3.json) | UNAUTHORISED_REPLY | SEPARATE_AUTHORITY | [source](../annot/050-N3.json) |
| [050-N4](../cases/050-N4.json) | DUPLICATE_REQUEST | RESOLVE_DUPLICATE | [source](../annot/050-N4.json) |
| [050-N5](../cases/050-N5.json) | CUSTOMER_CANCELS | RECORD_STOP | [source](../annot/050-N5.json) |

## Rebuild from the repository root

```sh
python3 case-state-widget/pipeline/compile.py --all
python3 case-state-widget/pipeline/test_negative.py
node case-state-widget/pipeline/validate.mjs case-state-widget/cases/*.json
npm test --prefix case-state-widget
```

Edit `annot/<id>.json` and compile. Ordinary annotation generation preserves edited files; `annotate_negative.py --refresh` deliberately replaces the 274 rule annotations. The reviewed 002-N4 is always preserved.
