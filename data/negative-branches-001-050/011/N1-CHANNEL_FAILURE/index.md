# Case 011-N1: Shipment tracking has not updated after depot arrival (Locate task submission timed out)

## Case details

- **Source role:** Depot work queue, Plover Arc Logistics
- **Status:** Completed — specific coordination task only
- **Created:** 2026-02-12 09:00:00 UTC
- **Escalated:** 2026-02-12 09:27:00 UTC
- **Updated:** 2026-02-12 10:05:00 UTC
- **Completed:** 2026-02-12 10:05:00 UTC
- **Primary shipment:** DL-011
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC
- **Derived from:** Public case 011, events 001–003 retained; branch CHANNEL_FAILURE

## Context

Tracking support reports that DL-011's last public scan is the destination depot arrival at 06:15 UTC on 2026-02-12, with no sort or route scan and no confirmed storage position. Mera Olt, the recipient, asks whether the parcel is physically at the depot. This branch diverges after event 003: Locate task submission timed out.

## Initial request

Submission for DL-011 at 09:25 UTC timed out before a task reference was issued. The destination depot task list may or may not contain this request. Do not assume the locate task was created.

## Overview

The escalation snapshot comprises history events 001–004. Event 005 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

Ask the destination depot in Dispatch chat whether its task list holds a saved locate request for DL-011, and submit the request once only if it is absent.

- **Recipient:** Destination depot, Plover Arc Logistics
- **Channel:** Dispatch chat
- **Recorded action:** [History event 005](history.md#event-005)
- **Expected decision:** VERIFY_FIRST (workflow sheet R)

## Outcome

The depot confirms exactly one saved locate task with a reference; this proves the request exists, not that DL-011 has been found.

## Boundaries and remaining work

Must not: Do not resubmit the locate task straight away, which risks two open tasks for one parcel, and do not tell Mera that a depot check is under way.

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
