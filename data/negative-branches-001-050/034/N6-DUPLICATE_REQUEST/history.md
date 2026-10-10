# Case 034-N6 history — Returned parcel has reached the carrier depot but not the merchant warehouse (Customer opens a parallel trace)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 034; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-07 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Returns depot, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

RT-034 last scan: return depot, 2026-03-07 07:40 UTC. No merchant receiving scan is visible. The carrier still holds the return.

<a id="event-002"></a>
## 2026-03-07 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Elrin Kove, customer
- **To:** Iona Quill, Rivet Delivery Desk

My return has been sitting at the depot. Could you trace it to the merchant? I need to know when they actually have it.

<a id="event-003"></a>
## 2026-03-07 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Returns trace team, Plover Arc Logistics

Please trace RT-034 through to merchant receipt. Ask the merchant receiving team to confirm physical acceptance rather than use a departure scan as proof.

<a id="event-004"></a>
## 2026-03-07 10:00:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Returns trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The customer also opened a trace for RT-034 from the tracking page at 09:40. We now have two open traces for one parcel. Should both stay open?

<a id="event-005"></a>
## 2026-03-07 10:15:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Returns trace team, Plover Arc Logistics

Both traces concern RT-034. Please link the customer's 09:40 trace to our 09:25 request and keep one trace, the one that ends with Tallowmere's warehouse confirming physical receipt. Please open no further traces for this parcel.

<a id="event-006"></a>
## 2026-03-07 10:45:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Returns trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The 09:40 trace is closed and linked to your 09:25 request. One trace remains for RT-034, ending in merchant receiving confirmation. The last scan is still the return depot at 07:40; merchant receipt is unconfirmed.
