# Case 086 history — Recipient cancels the reschedule request before dispatch has booked anything

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-04-28 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Dispatch chat
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-086 is booked for 2026-04-29, 09:00–12:00 UTC. Reschedule request RQ-086 to 2026-04-30 was logged at 08:40 UTC today and sits in our booking queue, which is processed in order through the morning. A withdrawal stops a request only once Dispatch records it; a change already applied stays until a new request replaces it.

<a id="event-002"></a>
## 2026-04-28 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Nira Sabeth, recipient
- **To:** Iona Quill, Rivet Delivery Desk

My plans changed and I will be home on the morning of 2026-04-29 after all. Please cancel my request to move DL-086 and keep the original slot.

<a id="event-003"></a>
## 2026-04-28 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Dispatch chat
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

Please record the withdrawal of reschedule request RQ-086 for DL-086 from verified recipient Nira Sabeth, and apply no new booking change. Please report what was already executed: is DL-086 still booked for 2026-04-29, 09:00–12:00 UTC, or has a move to 2026-04-30 been applied?

<a id="event-004"></a>
## 2026-04-28 09:40:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Dispatch chat
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

RQ-086 withdrawn at 09:31 UTC, before the queue reached it. No change was applied: DL-086 remains booked for 2026-04-29, 09:00–12:00 UTC, and no 2026-04-30 slot was reserved. This is a booking confirmation, not a completed delivery.

<a id="event-005"></a>
## 2026-04-28 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Nira Sabeth, recipient

Dispatch recorded the withdrawal of your reschedule request before it was processed. DL-086 stays booked for 2026-04-29, 09:00–12:00 UTC; nothing was moved. Delivery itself is still pending.
