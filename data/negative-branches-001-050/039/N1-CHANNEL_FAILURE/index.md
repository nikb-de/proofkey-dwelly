# Case 039-N1: Merchant shipped a replacement but the original parcel then also arrived (Duplicate return form times out)

## Case details

- **Source role:** Duplicate returns, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-03-12 09:00:00 UTC
- **Escalated:** 2026-03-12 09:30:00 UTC
- **Updated:** 2026-03-12 10:15:00 UTC
- **Completed:** 2026-03-12 10:15:00 UTC
- **Primary task reference:** TG-039
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 039, events 001–003 retained; branch CHANNEL_FAILURE

## Context

TG-039 ordered one floor light, but original DL-039-O and replacement DL-039-R both have handover scans, and Tallowmere Goods says no duplicate charge applies without its authorised reconciliation. Dessa Kelm has kept the replacement, left the original carton sealed, and asks how to return the duplicate. This branch diverges after event 003: Duplicate return form times out.

## Initial request

Automated notice. Your request for TG-039 could not be filed: the duplicate-return form timed out at 09:29. A return authorisation may have been partly created. No reference was issued.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Duplicate returns and ask whether any return authorisation or collection exists for DL-039-O, stating that no second request will be sent until it answers.

- **Recipient:** Duplicate returns, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

Duplicate returns confirms one authorisation for DL-039-O, or none and one resubmission; an authorisation is not a collection or a reconciled order.

## Boundaries and remaining work

Must not: Do not resend the request; two authorisations can book two collections or recover the wrong unit.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
