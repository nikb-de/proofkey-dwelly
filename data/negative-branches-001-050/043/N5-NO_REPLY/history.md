# Case 043-N5 history — Freight collection needs confirmed pallet dimensions and weight (Shipper silent before allocation cut-off)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 043; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-16 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Freight booking desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-043 has one pallet at Orris Span Fabrication, but its dimensions and weight fields are blank. We cannot allocate a collection vehicle from an unspecified pallet size.

<a id="event-002"></a>
## 2026-03-16 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Nessa Dray, Orris Span shipping coordinator
- **To:** Iona Quill, Rivet Delivery Desk

We have the pallet ready. Please tell me which measurements the carrier needs to finish the booking.

<a id="event-003"></a>
## 2026-03-16 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Business portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Nessa Dray, Orris Span shipping coordinator

Please provide measured length, width and total height including pallet, plus gross weight including packaging, for DL-043. We will pass those actual measurements to the carrier.

<a id="event-004"></a>
## 2026-03-16 13:00:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Freight booking desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-043 still has blank dimension and weight fields. Collection allocations for 2026-03-17 close at 15:00 UTC today. After that, the earliest allocation we can consider is 2026-03-18.

<a id="event-005"></a>
## 2026-03-16 13:15:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Business portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Nessa Dray, Orris Span shipping coordinator

Reminder for DL-043: we still need the measured length, width and total height including pallet, and the gross weight including packaging. Plover Arc closes collection allocations for 2026-03-17 at 15:00 UTC today. Without the measurements by then, the earliest allocation the carrier can consider is 2026-03-18.

<a id="event-006"></a>
## 2026-03-16 14:10:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Business portal
- **From:** Nessa Dray, Orris Span shipping coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Measured DL-043: 120 x 100 x 145 cm including pallet, gross weight 310 kg including packaging, from our calibrated warehouse scale. One non-stackable pallet. These are our measurements, sent before 15:00 UTC; the carrier has not yet accepted them or allocated a collection.
