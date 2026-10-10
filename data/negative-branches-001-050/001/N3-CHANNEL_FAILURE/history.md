# Case 001-N3 history — Recipient cannot attend the scheduled delivery window (Booking request email unacknowledged by Dispatch)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 001; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-02-02 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-001 is booked for 2026-02-03, 09:00–12:00 UTC. Our rescheduling inventory currently has 2026-02-03 15:00–18:00 or 2026-02-04 10:00–13:00. There is no rescheduling charge.

<a id="event-002"></a>
## 2026-02-02 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Vessa Lorne, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I have a work meeting during the morning delivery. Could you help move my lamp delivery? Please use this order-linked message thread.

<a id="event-003"></a>
## 2026-02-02 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Vessa Lorne, recipient

Dispatch has offered 2026-02-03 15:00–18:00 or 2026-02-04 10:00–13:00, both at no charge. Which should I ask them to book?

<a id="event-004"></a>
## 2026-02-02 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Vessa Lorne, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Please choose 2026-02-03 15:00–18:00. I will be home then.

<a id="event-005"></a>
## 2026-02-02 10:30:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Email
- **From:** Mail delivery system, Rivet Delivery Desk
- **To:** Iona Quill, Rivet Delivery Desk

Delivery status notification. Your message to Dispatch, Plover Arc Logistics, subject 'DL-001 booking request: 2026-02-03 15:00–18:00', sent at 09:55, has not been accepted by the receiving server after 35 minutes. The server reported a temporary error. Retries continue automatically. Delivery status: unknown.

<a id="event-006"></a>
## 2026-02-02 10:45:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Dispatch chat
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

Our 09:55 email asking you to book DL-001 for 2026-02-03 15:00–18:00 shows delivery status unknown after a temporary server error. What does DL-001's saved booking show now? Please do not create a second change. We will send no further booking request until we know.

<a id="event-007"></a>
## 2026-02-02 11:05:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Dispatch chat
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-001's saved booking shows 2026-02-03 15:00–18:00. Your 09:55 email reached us at 10:38 and was applied once at 10:41; the morning slot is removed. There is no second change. This is a booking, not a completed delivery.
