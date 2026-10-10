# Case 043-N4 history — Freight collection needs confirmed pallet dimensions and weight (Booking update errors, save unknown)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 043; events 005–007 are this branch.

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
## 2026-03-16 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Business portal
- **From:** Nessa Dray, Orris Span shipping coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Measured DL-043: 120 × 100 × 145 cm including pallet, gross weight 310 kg including packaging. One non-stackable pallet; our calibrated warehouse scale supplied the weight.

<a id="event-005"></a>
## 2026-03-16 09:58:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Freight portal
- **From:** Freight portal, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Error on booking update DL-043 submitted 09:56 UTC: server error 500. Your changes to the dimension and weight fields may not have been saved. No confirmation number was issued.

<a id="event-006"></a>
## 2026-03-16 10:13:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Freight booking desk, Plover Arc Logistics

Our DL-043 booking update at 09:56 UTC returned server error 500 with no confirmation number. What do the DL-043 dimension and weight fields show now? We will not resubmit until you confirm, so that no second or part-saved update is created.

<a id="event-007"></a>
## 2026-03-16 10:35:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Freight booking desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-043 now shows 120 x 100 x 145 cm and 310 kg gross, one non-stackable pallet, saved at 09:56 UTC. One update is on file. These are saved booking values; the planner has not yet accepted them or allocated a collection.
