# Case 093 history — Recipient sent the same reschedule request by portal and email and dispatch opened two tickets

All identities, records and communications are fictional. Total events: 4.

<a id="event-001"></a>
## 2026-05-05 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Scheduling, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-093 is booked for 2026-05-06, 08:00–12:00 UTC. Verified recipient Ilsa Vantrow asked to move it to 2026-05-07, 13:00–17:00 UTC, which is open at no charge, in ticket RS-0931 (Customer portal, 08:12 UTC) and again in RS-0932 (email, 08:15 UTC). Rule: one request gives one booking change; a repeat ticket is linked to the first and closed without action.

<a id="event-002"></a>
## 2026-05-05 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Dispatch chat
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

We have two open reschedule tickets for DL-093, RS-0931 and RS-0932. Both ask for the same slot. Should we process both, or which one do we act on?

<a id="event-003"></a>
## 2026-05-05 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Dispatch chat
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

RS-0932 repeats RS-0931: same verified recipient, same shipment, same requested slot. Please link RS-0932 to RS-0931 and close it without action, then apply one change under RS-0931: move DL-093 from 2026-05-06, 08:00–12:00 UTC to 2026-05-07, 13:00–17:00 UTC.

<a id="event-004"></a>
## 2026-05-05 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Dispatch chat
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

RS-0932 is linked to RS-0931 and closed with no action. Under RS-0931, DL-093 is now booked for 2026-05-07, 13:00–17:00 UTC, and the 2026-05-06 slot is released. The booking history shows one change. This is a booking confirmation, not a delivery.
