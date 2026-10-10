# Case 022-N1: A delivered household item is confirmed broken (Mail gateway times out on request)

## Case details

- **Source role:** Mail system, Tallowmere Goods
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-23 09:00:00 UTC
- **Escalated:** 2026-02-23 09:27:00 UTC
- **Updated:** 2026-02-23 10:05:00 UTC
- **Completed:** 2026-02-23 10:05:00 UTC
- **Primary shipment:** DL-022
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 022, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Tallowmere Goods has accepted damage on TG-022, a ceramic table lamp with a separated base, for replacement assessment, but no replacement approval is recorded. Remi Dask prefers the same lamp to a refund and asks for the merchant to approve a replacement. This branch diverges after event 003: Mail gateway times out on request.

## Initial request

Delivery status unknown for your message to Replacement authorisations sent at 09:25 UTC. The mailbox gateway timed out after accepting part of the message. It may or may not have reached the team. No ticket reference was returned.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Email Damage assessor, Tallowmere Goods, which holds the TG-022 record, to ask whether a replacement request is now logged against it, and send no second request until it answers.

- **Recipient:** Damage assessor, Tallowmere Goods
- **Channel:** Email
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The merchant confirms whether one request is logged on TG-022; a logged request is not an approval.

## Boundaries and remaining work

Must not: Do not resend the replacement request blindly, which risks two replacement orders, and do not tell Remi that the request has been received.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
