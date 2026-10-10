# v4 original-map coverage

All 38frames (including 6workspace overview nodes) and 24drawn edges were assessed. The six selected scenarios and their mapped negative paths are represented in the offline scope. Real identity, carrier channels, external storage and receipt remain explicitly simulated or unavailable. This is not an all 50case claim.

| Frame | View | Evidence |
|---|---|---|
| W1 | Case workspace | Case list with search, empty/error recovery, owner, next step and status filters; team desktop/mobile rendered. |
| W2 | Case detail workspace | Summary, addressed immutable requests, correlated responses, initial Sources, task/physical-state separation; evidence inspected. |
| W3 | Operator queue workspace | Requested, queued, owned, awaiting answer and resolved operator states; filters and due time visible. |
| W4 | Operator decision workspace | Current revision/stage, required rationale/review, rejection, clarification answer and bounded continuation exercised. |
| W5 | Customer task workspace | Selected delivery, quote, approved return, investigation and refusal flows exercised with scoped consent and recovery. |
| W6 | Simulation preparation workspace | Configure, local rehearsal failure/pass, enable, registered run and editing a new draft without changing active run exercised. |
| W1.list | Case list | Case open and search/filters; real owner and next-step labels. Local load failure has retry rather than empty-list success. |
| W2.processing | Draft case | 001 invitation draft, edit/source boundaries, send acknowledgement and pre-send permission denial; denied quote retains original kind. |
| W2.result | Team task result | 001 second slot preserved on team/customer result, with current-run confirmation and physical delivery pending. |
| W2.waiting | Customer invitation wait | Invitation acknowledgement before customer choice; owner/next check/deadline/budget/fallback in team UI. |
| W5.choose | Choose delivery window | Slot required, date/time/price visible, alternative date and help retained; back focus returns to slot. |
| W5.review | Review exact terms | Exact chosen object/time/price consent stored before booking; changes invalidate selection/consent. |
| W5.result | Customer result | Exact confirmed chosen result; close and reopen operate locally without creating another command. |
| W5.sending | Sending and dispatch wait | Sending/wait/UNKNOWN distinct; interruption preserved and same-intent recovery remains bounded. |
| W5.refuse | Record refusal | Explicit refusal, optional reason, cancel; interruption and late response after stop reach refusal_saved. |
| W5.refusal_saved | Refusal recorded | Saved refusal separate from collection. Already-authorized SIM permits terms; unknown authority blocks collection and retains owner. |
| W5.collection_review | Review collection terms | Scenario-relative date limits, required address/agreement; exact object/date/time/address/price/revision consent saved. |
| W5.collection_pending | Collection pending/result | Collection confirmation and reference separate from physical receipt; exact agreed address/date retained. 033 reuses source consent. |
| W3.queue | Operator queue | Help acknowledgement/ownership, reason, time, due time, saved stage, filters and customer answer retained. |
| W4.review | Review operator decision | Version and stage captured, required note/review confirmation; owner decides clarification/continue/stop without booking. |
| W4.invalid | Rejected or stale operator decision | Visible case-version change causes rejected decision; form retained; current facts must be reviewed again. |
| W4.accepted | Accepted decision and resumption | Clarify→customer answer→queue→explicit one-search allowance→usable form, without resetting command/check budget or fabricating consent. |
| W2.reconciling | Unknown-outcome reconciliation | Unknown waits retain original kind/ID; wrong/stale evidence rejected, acknowledgement not outcome, bounded checks escalate. |
| W2.stop_overlay | Stop explanation dialog | Explicit no-new-action consequences; native dialog, Escape and invoking-control return. |
| W2.stopped | Durable stop result | Stop remains set; late confirmed effect visible; no collection after stopped refusal. No rollback claim. |
| W2.stop_wait | Stop requested and acknowledgement | Requested acknowledgement visibly separate; simulated acknowledgement failure remains blocked; verification recovers registration. |
| W6.draft | Prepare simulation | Snapshot hash, workflow/simulator version, virtual clock, finite limits and permission configured; enable disabled until checks. |
| W6.failed | Simulation check failure | Injected incorrect outcome gives expected/actual trace, failed status and disabled enable; correction/recheck reachable. |
| W6.running | Version-bound run | Registered unique run with frozen launched config; editing next draft leaves active run and limits unchanged. |
| W6.ready | Checked version and explicit enablement | Metadata and bounded shared-transition rehearsal pass; explicit enable before run registration, with launching state. |
| W2.quote_draft | Quote request draft | Current requested date/object/full surcharge preserved in outgoing body; dispatch recipient and permitted channel retained. |
| W2.quote_wait | Team quote waiting | Acknowledgement distinct from valid quote; current pending owner/deadline/check budget/fallback visible. |
| W5.quote_available | Quoted customer options | New reply provides GBP 8/10 options; second selection reviewed and confirmed; changed offer changes actual times/prices. |
| W5.quote_wait | Customer quote waiting | Customer-safe next update/status and current-booking caveat; internal team budget/contact omitted. |
| W2.return_draft | Approved return label request | 031 RT/TG/DL source link and existing approval; no repeated refusal; request addressed to label team. |
| W2.return_wait | Team label wait | Pending label separated from receipt; stale/wrong evidence rejects through shared response route. |
| W5.return_ready | Customer label ready | Mock label opens with IDs and not-valid-for-shipping warning; link-expiry/read recovery creates no new business request. |
| W5.return_wait | Customer label wait | Existing return approval retained, unavailable label remains pending; customer can return and request help. |

## Drawn edges

The corresponding action/event routes are present; team/customer handoffs are shared local state projections, not access grants.

| Sheet | Source | Target |
|---|---|---|
| 01 | W1.list-b0 | W2.processing |
| 01 | W2.processing-b0 | W2.waiting |
| 01 | W2.waiting-status | W2.result |
| 02 | W5.choose-b0 | W5.review |
| 02 | W5.review-b0 | W5.sending |
| 02 | W5.sending-status | W5.result |
| 03 | W5.refuse-b0 | W5.refusal_saved |
| 03 | W5.refusal_saved-b0 | W5.collection_review |
| 03 | W5.collection_review-b0 | W5.collection_pending |
| 04 | W3.queue-b0 | W4.review |
| 04 | W4.review-b0 | W4.accepted |
| 04 | W4.review-b0 | W4.invalid |
| 05 | W2.reconciling-b0 | W2.stop_overlay |
| 05 | W2.stop_overlay-b0 | W2.stop_wait |
| 05 | W2.stop_wait-status | W2.stopped |
| 06 | W6.draft-b0 | W6.failed |
| 06 | W6.draft-b0 | W6.ready |
| 06 | W6.ready-b0 | W6.running |
| 07 | W2.quote_draft-b0 | W2.quote_wait |
| 07 | W2.quote_wait-status | W5.quote_wait |
| 07 | W5.quote_wait-status | W5.quote_available |
| 08 | W2.return_draft-b0 | W2.return_wait |
| 08 | W2.return_wait-status | W5.return_wait |
| 08 | W5.return_wait-status | W5.return_ready |
