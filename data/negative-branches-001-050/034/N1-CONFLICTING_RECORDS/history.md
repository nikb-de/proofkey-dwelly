# Case 034-N1 history — Returned parcel has reached the carrier depot but not the merchant warehouse (Carrier delivery scan, no merchant receipt)

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
## 2026-03-08 08:30:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Warehouse receiving, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

We have no RT-034 carton at our returns bay and no receiving record for TG-034. We are told the carrier portal shows RT-034 delivered to us at 16:20 UTC yesterday. Nothing here matches that scan.

<a id="event-005"></a>
## 2026-03-08 08:45:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Returns trace team, Plover Arc Logistics

Two records disagree for RT-034. Your portal shows it delivered to Tallowmere Goods at 16:20 UTC on 2026-03-07. Tallowmere's Warehouse receiving reports no RT-034 carton at its returns bay and no receiving record for TG-034. Please send the proof of delivery: the delivery location, time and who signed. We are treating neither record as final.

<a id="event-006"></a>
## 2026-03-08 11:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Returns trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Proof of delivery for RT-034: handed over at 16:20 on 2026-03-07 at Tallowmere's goods-in dock, not the returns bay, signed for with initials only. This shows carrier handover only. It is not a merchant receipt, and inspection and refund are untouched.
