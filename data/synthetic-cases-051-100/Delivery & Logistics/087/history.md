# Case 087 history — Merchant cancels the order while a pickup-point redirect is in progress

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-04-29 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Routing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-087 is at Kestwater depot under redirect RD-087 to Thimble Counter, due on the 11:00 UTC transfer today. A shipper's stop halts new movement from the time Routing records it; steps already executed are not reversed automatically. A stopped parcel is held where it is, and return to sender needs a separate return instruction from the shipper.

<a id="event-002"></a>
## 2026-04-29 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Quen Tarvik, Brackfen Goods shipping coordinator
- **To:** Iona Quill, Rivet Delivery Desk

We cancelled the customer's order for DL-087 this morning. Please stop it going to Thimble Counter; we will decide later today whether it comes back to us.

<a id="event-003"></a>
## 2026-04-29 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing, Plover Arc Logistics

Please record a stop on redirect RD-087 for DL-087 from verified shipper Brackfen Goods, and start no new movement, including the 11:00 UTC transfer to Thimble Counter. Please report what has already been executed and where the parcel is now. Return instructions will come separately from Brackfen Goods.

<a id="event-004"></a>
## 2026-04-29 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Stop recorded on RD-087 at 09:41 UTC. DL-087 was still at Kestwater depot and is removed from the 11:00 UTC transfer; it never reached Thimble Counter. The redirect label applied yesterday stays on the parcel record. DL-087 is held at the depot pending the shipper's return instruction; no return has been started.

<a id="event-005"></a>
## 2026-04-29 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Business portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Quen Tarvik, Brackfen Goods shipping coordinator

Routing stopped redirect RD-087 at 09:41 UTC; DL-087 is held at Kestwater depot and did not reach Thimble Counter. No return has been started. Return to sender needs your separate return instruction to the carrier, and any refund to your customer is outside this record.
