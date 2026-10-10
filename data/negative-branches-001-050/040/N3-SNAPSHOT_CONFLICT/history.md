# Case 040-N3 history — Cancelled order is packed but has not left the merchant warehouse (Customer reverses the cancellation)

All identities, records and communications are fictional. Total events: 5. Events 001–002 are retained from public case 040; events 003–005 are this branch.

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
## 2026-03-13 09:15:00 UTC — event 003

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Customer for order TG-040
- **To:** Iona Quill, Rivet Delivery Desk

I cancelled TG-040 this morning but I have changed my mind. Please do not stop the parcel. Send it as planned to my address.

<a id="event-004"></a>
## 2026-03-13 09:30:00 UTC — event 004

- **Stage:** Agent action
- **Channel:** Warehouse work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Order control, Tallowmere Goods

At 09:15 a Customer portal message for TG-040 asked us not to stop the parcel and to send it as planned. You own CAN-040. Does CAN-040 still stand? We will act on the stop only as you instruct and have told the customer nothing about reinstatement.

<a id="event-005"></a>
## 2026-03-13 09:50:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Warehouse work queue
- **From:** Order control, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

CAN-040 stands. A reinstatement would need a new order through our order account, and none has been placed. Continue with the warehouse stop for DL-040. The stop is not yet confirmed by warehouse dispatch, and refund remains a separate task.
