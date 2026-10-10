# Case 040 history — Cancelled order is packed but has not left the merchant warehouse

All identities, records and communications are fictional. Total events: 4.

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

