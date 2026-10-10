# Case 038-N6 history — Failed delivery has returned to sender and the customer still wants the order (Customer's own reshipment request approved first)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 038; events 004–006 are this branch.

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
## 2026-03-11 09:42:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

We already approved a reshipment for TG-038 at 09:20 from the customer's own portal request to the same address. Your email would create a second shipment record. Should we proceed?

<a id="event-005"></a>
## 2026-03-11 09:57:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Reshipment authorisations, Tallowmere Goods

Please link our 09:25 request to your 09:20 approval for TG-038 and create no second shipment record. Both concern the same order and the same destination, Apartment 2, 31 Rillstone Walk.

<a id="event-006"></a>
## 2026-03-11 10:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Your request is linked to the 09:20 approval and no second record was created. One shipment record, DL-038-R, remains for TG-038 to Apartment 2, 31 Rillstone Walk. The parcel has not been handed to the carrier yet.
