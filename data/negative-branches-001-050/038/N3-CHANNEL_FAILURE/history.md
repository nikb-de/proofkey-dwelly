# Case 038-N3 history — Failed delivery has returned to sender and the customer still wants the order (Approval form errors mid-creation)

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
## 2026-03-11 09:39:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

System notice. The approval form for TG-038 errored at 09:38 while creating the shipment record. The notice cannot show whether a new shipment was created. No shipment reference was returned.

<a id="event-005"></a>
## 2026-03-11 09:54:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Reshipment authorisations, Tallowmere Goods

Your 09:38 notice says the approval form for TG-038 errored while creating the shipment record. Please check whether a new shipment record exists for TG-038 and send its reference if so. We will not send a second approval request until you confirm.

<a id="event-006"></a>
## 2026-03-11 10:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

One shipment record exists for TG-038: DL-038-R, created before the error, to Apartment 2, 31 Rillstone Walk. No second record exists. The parcel has not been handed to the carrier; the reference is not dispatch or receipt.
