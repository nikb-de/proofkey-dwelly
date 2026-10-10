# Case 040-N6 history — Cancelled order is packed but has not left the merchant warehouse (Warehouse silent as the sweep nears)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 040; events 004–006 are this branch.

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
## 2026-03-13 10:05:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Warehouse work queue
- **From:** Order control, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

No reply from warehouse dispatch on DL-040 yet. The next outbound sweep of cage O7 is at 10:30. Is the stop in place?

<a id="event-005"></a>
## 2026-03-13 10:20:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Warehouse work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Warehouse dispatch, Tallowmere Goods; Order control, Tallowmere Goods

Reminder for Warehouse dispatch: CAN-040 requires DL-040 to be removed from cage O7 before the 10:30 outbound sweep; if it stays in the cage, it leaves with the sweep. Please confirm physical removal and the shipment status. For Order control: no stop is confirmed yet.

<a id="event-006"></a>
## 2026-03-13 10:28:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Warehouse work queue
- **From:** Warehouse dispatch, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

At 10:26 UTC we removed DL-040 from cage O7 into cancellation stock, before the 10:30 sweep. Shipment status is dispatch stopped; no carrier handover occurred. Refund action is not performed by our team.
