# Case 010-N2 history — Recipient wants delivery held during a short absence (Hold request transfer timed out)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 010; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-02-11 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-010 is in depot stock. This service allows a hold up to three calendar days before routing. A confirmed release date is required.

<a id="event-002"></a>
## 2026-02-11 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Daro Lusk, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I am away and return on 2026-02-14. Please hold the parcel and release it on 2026-02-14, not earlier.

<a id="event-003"></a>
## 2026-02-11 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

Please apply the eligible three-day hold to DL-010, with release on 2026-02-14 as requested in Daro’s verified order thread. Confirm the stock and routing status.

<a id="event-004"></a>
## 2026-02-11 09:27:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Dispatch auto-acknowledgement, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Automatic acknowledgement. Your email about DL-010 was received at 09:25. Its transfer to the depot hold queue failed with a timeout at 09:26. The stock record may or may not show a hold. No reference has been issued.

<a id="event-005"></a>
## 2026-02-11 09:42:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Dispatch chat
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

Our 09:25 email asking for a hold on DL-010 reached you, but its transfer to the depot hold queue timed out and no reference was issued. What do DL-010's saved stock status and release date show now? Please do not create a second change. We will not resend the hold request until we know.

<a id="event-006"></a>
## 2026-02-11 10:05:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Dispatch chat
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-010's stock record shows HOLD through 2026-02-13, with release to routing on 2026-02-14, saved at 09:31 after the queue retried. There is one hold entry. That is a release date, not a delivery date.
