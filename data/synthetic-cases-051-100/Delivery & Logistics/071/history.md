# Case 071 history — Reschedule request timed out in the dispatch system and the recipient asks whether it is booked

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-04-13 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-071 is at the depot; route release for today is at 16:00 UTC. A reschedule to 2026-04-14, 13:00–16:00 UTC was submitted at 08:41 UTC and the booking tool timed out without returning a confirmation. Dispatch rule: a timed-out change is checked against the saved booking before any resubmission, because a second submission can create a duplicate booking.

<a id="event-002"></a>
## 2026-04-13 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Halvi Maddren, recipient
- **To:** Iona Quill, Rivet Delivery Desk

The order thread says my reschedule request timed out. Is DL-071 now booked for tomorrow afternoon or still for today? I do not want two deliveries or to lose the new slot.

<a id="event-003"></a>
## 2026-04-13 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Dispatch chat
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

Please check the saved booking for DL-071 and tell us which slot it holds after the 08:41 UTC request for 2026-04-14, 13:00–16:00 UTC. Do not submit a second change until the saved state is known. If the change is absent, we will send one resubmission.

<a id="event-004"></a>
## 2026-04-13 09:40:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Dispatch chat
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Saved booking checked at 09:36 UTC. The 08:41 UTC request was applied once: DL-071 is booked for 2026-04-14, 13:00–16:00 UTC and today’s slot is released. No second change exists and none has been made. This is a booking record, not a delivery.

<a id="event-005"></a>
## 2026-04-13 10:00:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Halvi Maddren, recipient

Dispatch has checked the saved booking. DL-071 is booked once, for 2026-04-14, 13:00–16:00 UTC; the timeout did not stop the change and no second booking was made. Delivery itself is still pending.
