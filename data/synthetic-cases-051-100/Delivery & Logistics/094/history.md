# Case 094 history — Pickup-point operator sees two extension requests for the same parcel

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-05-06 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Recipient services, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-094 is at Gullmere Counter with a collection deadline of 2026-05-07, 18:00 UTC. Rule: one three-day extension per parcel, requested by the verified recipient and recorded by the counter supervisor. Two requests are logged: EXT-0941 from the order portal at 07:40 UTC and EXT-0942 from the recipient's call to the counter at 08:05 UTC, both from the same verified recipient.

<a id="event-002"></a>
## 2026-05-06 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Pickup-point portal
- **From:** Gullmere Counter supervisor
- **To:** Iona Quill, Rivet Delivery Desk

Our portal shows two extension requests for DL-094. If both are applied, the parcel would stay until 2026-05-13. Which one do we keep?

<a id="event-003"></a>
## 2026-05-06 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Gullmere Counter supervisor

EXT-0942 repeats EXT-0941: same verified recipient, same parcel, same three-day extension. Please confirm EXT-0941, which moves the DL-094 deadline to 2026-05-10, 18:00 UTC, and withdraw EXT-0942 as a duplicate linked to it. Only one extension is permitted for this parcel.

<a id="event-004"></a>
## 2026-05-06 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Gullmere Counter supervisor
- **To:** Iona Quill, Rivet Delivery Desk

EXT-0941 is confirmed; the DL-094 collection deadline is now 2026-05-10, 18:00 UTC. EXT-0942 is withdrawn and linked to EXT-0941. DL-094 is on our shelf and has not been collected.

<a id="event-005"></a>
## 2026-05-06 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Notification services, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

One extension notice for DL-094, showing the 2026-05-10, 18:00 UTC deadline, was sent to the verified recipient. No notice was sent for EXT-0942. A notice is not a collection.
