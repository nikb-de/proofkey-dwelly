# Case 038-N5 history — Failed delivery has returned to sender and the customer still wants the order (Customer cancels the approved reshipment)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 038; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-03-11 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Warehouse returns, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

DL-038 for TG-038 is physically back in our stock after failed delivery and return-to-sender. Item accepted as reshippable. Our account team has authenticated Sella’s order-portal session; stored destination is Apartment 2, 31 Rillstone Walk, Merrow Quay. A new dispatch requires merchant approval.

<a id="event-002"></a>
## 2026-03-11 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Sella Nove, customer
- **To:** Iona Quill, Rivet Delivery Desk

I still want the order. I checked my authenticated order details: Apartment 2, 31 Rillstone Walk, Merrow Quay is correct. Please ask for reshipment there.

<a id="event-003"></a>
## 2026-03-11 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Reshipment authorisations, Tallowmere Goods

Please approve reshipment of TG-038 to Sella’s unchanged verified order destination, Apartment 2, 31 Rillstone Walk. Warehouse confirms the original item is back and reshippable.

<a id="event-004"></a>
## 2026-03-11 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Reshipment approved at no additional charge. New shipment DL-038-R is created for TG-038 with the confirmed destination. The new parcel has not been handed to the carrier yet.

<a id="event-005"></a>
## 2026-03-11 10:30:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Sella Nove, customer
- **To:** Iona Quill, Rivet Delivery Desk

I bought the same item elsewhere this morning. Please cancel the reshipment of TG-038 and refund me for the order.

<a id="event-006"></a>
## 2026-03-11 10:45:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Reshipment authorisations, Tallowmere Goods

At 10:30 the customer asked to cancel the reshipment of TG-038, having bought the same item elsewhere. Please record the stop on DL-038-R, do not hand it to the carrier, and tell us what state it is in now. The customer also asks for a refund; that is your decision, and we have promised nothing.

<a id="event-007"></a>
## 2026-03-11 11:15:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Stop recorded on DL-038-R at 11:00. The parcel had not left our warehouse and will not be handed to the carrier. The customer's refund request is with our refunds team; nothing is approved or paid.
