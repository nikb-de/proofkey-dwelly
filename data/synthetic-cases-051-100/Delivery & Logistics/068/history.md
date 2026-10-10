# Case 068 history — Business sender asks the price and earliest date for a next-day pallet collection

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-04-10 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Freight portal
- **From:** Freight account services, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Inline verified booking record DL-068: one 220 kg pallet, standard collection from Quarrystep Ceramics booked for 2026-04-15. Registered shipping coordinator Selka Hovrin has a verified business-portal channel and authority to accept service charges. Next-day collection is a surcharged upgrade on weekdays only; only the Freight planner can confirm the earliest date and the charge. The standard booking stays until the coordinator accepts a quote in the verified business thread.

<a id="event-002"></a>
## 2026-04-10 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Selka Hovrin, Quarrystep Ceramics shipping coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Our customer needs this pallet sooner. What is the earliest next-day collection you can offer, and what would it cost? Keep the current booking until we agree a price.

<a id="event-003"></a>
## 2026-04-10 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Freight planner, Plover Arc Logistics

Please quote the earliest next-day collection for DL-068, one 220 kg pallet at Quarrystep Ceramics, with the total surcharge. Verified coordinator Selka Hovrin asked at 09:10 UTC. Do not change the 2026-04-15 standard booking until the coordinator accepts in the verified business thread.

<a id="event-004"></a>
## 2026-04-10 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Business portal
- **From:** Selka Hovrin, Quarrystep Ceramics shipping coordinator
- **To:** Iona Quill, Rivet Delivery Desk

We have the Freight planner's quote in this thread: next-day collection on 2026-04-13, 08:00–12:00 UTC, GBP 42.00 total surcharge. We accept it. Please book it in place of the standard collection.

<a id="event-005"></a>
## 2026-04-10 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Freight planner, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Following the coordinator's acceptance in the verified business thread, DL-068 collection is booked for 2026-04-13, 08:00–12:00 UTC with a GBP 42.00 surcharge on the account. The 2026-04-15 standard collection is cancelled. This is a booking confirmation; the pallet has not been collected.
