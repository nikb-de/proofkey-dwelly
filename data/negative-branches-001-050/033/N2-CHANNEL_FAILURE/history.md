# Case 033-N2 history — Courier misses a booked return collection (Rebooking save times out)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 033; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-06 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Collections control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Collection for RT-033 was missed on the previous route day; parcel remains with customer. Approved return and packaging requirements are unchanged. Rebooking is at no charge.

<a id="event-002"></a>
## 2026-03-06 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Virin Lask, customer
- **To:** Iona Quill, Rivet Delivery Desk

Nobody collected my return. I can be home on 2026-03-07, 10:00–14:00. Please book another collection within that window.

<a id="event-003"></a>
## 2026-03-06 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Collections control, Plover Arc Logistics

Please rebook RT-033 within 2026-03-07, 10:00–14:00 UTC and provide the actual collection receipt after pickup, not just a booking status.

<a id="event-004"></a>
## 2026-03-06 09:40:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Collections control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Automated reply. The rebooking request for RT-033 timed out at 09:39 while saving to the collection plan. The plan may or may not hold a new slot. No booking reference was generated in this message.

<a id="event-005"></a>
## 2026-03-06 09:55:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Collections control, Plover Arc Logistics

Your 09:39 reply says the RT-033 rebooking timed out while saving. Please check what the collection plan shows for RT-033 now: one booking with its window, or none. Do not create a second booking meanwhile; we will not send another request until you confirm. The window is still 2026-03-07, 10:00–14:00 UTC.

<a id="event-006"></a>
## 2026-03-06 10:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Collections control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The collection plan holds one booking for RT-033: 2026-03-07, 11:00–13:00 UTC, no charge, saved before the timeout. No second job exists. The parcel has not been collected; a receipt follows only after pickup.
