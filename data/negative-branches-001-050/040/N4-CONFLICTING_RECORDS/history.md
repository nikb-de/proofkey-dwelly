# Case 040-N4 history — Cancelled order is packed but has not left the merchant warehouse (Carrier scan contradicts warehouse stop)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 040; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-03-13 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Order control, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Cancellation CAN-040 is authorised for TG-040 at 08:45 UTC today. DL-040 is packed in outbound cage O7 and has no carrier handover scan. Refund processing is a separate task.

<a id="event-002"></a>
## 2026-03-13 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Warehouse work queue
- **From:** Order control, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Please get the warehouse to stop DL-040 before the next outbound sweep. The cancellation is authorised, but the physical dispatch stop is not confirmed.

<a id="event-003"></a>
## 2026-03-13 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Warehouse work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Warehouse dispatch, Tallowmere Goods

Apply CAN-040 to stop DL-040 in cage O7 now. Please confirm physical removal from outbound dispatch and the resulting shipment status.

<a id="event-004"></a>
## 2026-03-13 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Warehouse work queue
- **From:** Warehouse dispatch, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

At 09:45 UTC we removed DL-040 from outbound cage O7 into cancellation stock. Shipment status is dispatch stopped; no carrier handover occurred. Refund action is not performed by our team.

<a id="event-005"></a>
## 2026-03-13 10:05:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-040 shows a collection scan at the Tallowmere outbound dock at 09:48 UTC today, on the trailer manifest for the 10:00 departure. No exception has been recorded against it.

<a id="event-006"></a>
## 2026-03-13 10:20:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Warehouse work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Warehouse dispatch, Tallowmere Goods

Two records disagree for DL-040. Your entry says it was removed from cage O7 into cancellation stock at 09:45 with no carrier handover. Plover Arc Tracking support reports a collection scan at your outbound dock at 09:48, on the manifest for the 10:00 departure. Please physically check cancellation stock for DL-040 and report where it is. Both records stay as they are meanwhile.

<a id="event-007"></a>
## 2026-03-13 10:45:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Warehouse work queue
- **From:** Warehouse dispatch, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Physical check at 10:35: DL-040 is in cancellation stock with its label intact. The carrier's 09:48 scan remains on its record; we cannot explain it from our side. Refund and customer communication are not handled by our team.
