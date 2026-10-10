# Case 040-N1 history — Cancelled order is packed but has not left the merchant warehouse (Parcel handed over before the stop)

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
## 2026-03-13 09:41:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Warehouse work queue
- **From:** Warehouse dispatch, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Cage O7 was swept at 09:30, before the stop task was picked up. DL-040 was loaded onto the Plover Arc trailer and has a carrier handover scan at 09:32. We can no longer stop it in the warehouse.

<a id="event-005"></a>
## 2026-03-13 09:56:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

DL-040 for TG-040 was loaded onto your trailer with a handover scan at 09:32, after Tallowmere Goods authorised cancellation CAN-040. Please send the options to stop or return it, such as an intercept, and any charge for each. We are changing nothing until Tallowmere's Order control chooses one, and will pass your reply to them.

<a id="event-006"></a>
## 2026-03-13 10:40:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Warehouse work queue
- **From:** Order control, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Your desk passed on Plover Arc's options for DL-040: depot intercept with return to our warehouse at GBP 6.50, or delivery as addressed. We choose the depot intercept. The parcel is not back with us until our warehouse scans it in, and refund remains a separate task.
