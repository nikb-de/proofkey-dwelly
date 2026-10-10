# Case 010-N1 history — Recipient wants delivery held during a short absence (Return date exceeds the hold limit)

All identities, records and communications are fictional. Total events: 5. Events 001–002 are retained from public case 010; events 003–005 are this branch.

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
## 2026-02-11 09:16:00 UTC — event 003

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Daro Lusk, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Correction to my last message: my return has moved. I am now back on 2026-02-16. Please hold DL-010 until then and release it on 2026-02-16, not before.

<a id="event-004"></a>
## 2026-02-11 09:31:00 UTC — event 004

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Daro Lusk, recipient

This service allows a hold of up to three calendar days before routing, so a release on 2026-02-16 is outside it. We will not request any hold until you confirm a release date within that limit. Would you like the longest hold this service permits instead?

<a id="event-005"></a>
## 2026-02-11 10:30:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Following Daro's confirmation, DL-010 is marked HOLD in depot stock through 2026-02-13, with release to routing on 2026-02-14. That is the longest hold this service allows. A release date is not a delivery date.
