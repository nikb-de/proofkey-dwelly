# Case 034-N3 history — Returned parcel has reached the carrier depot but not the merchant warehouse (Customer wants refund on depot scan)

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
## 2026-03-07 10:15:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Elrin Kove, customer
- **To:** Iona Quill, Rivet Delivery Desk

The carrier has had my parcel since this morning; that should be enough. Please tell Tallowmere to refund me today instead of waiting for their warehouse.

<a id="event-005"></a>
## 2026-03-07 10:30:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Elrin Kove, customer

We cannot ask Tallowmere Goods for a refund on the depot scan. That scan shows the carrier holds your return, not that the merchant has received it. Refund decisions belong to Tallowmere after its warehouse receives the return. Our trace continues until the warehouse confirms physical receipt.

<a id="event-006"></a>
## 2026-03-07 11:00:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Elrin Kove, customer
- **To:** Iona Quill, Rivet Delivery Desk

Understood. I will wait for the warehouse to confirm it has my return. I accept that no refund has been requested and that the parcel is still with the carrier.
