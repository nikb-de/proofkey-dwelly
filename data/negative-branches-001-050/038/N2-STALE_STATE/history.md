# Case 038-N2 history — Failed delivery has returned to sender and the customer still wants the order (Returned unit reallocated before approval)

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
## 2026-03-11 09:44:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

The returned unit for TG-038 was released to general stock at 09:30 and has been allocated to another order. We can approve dispatch of a new unit when stock arrives on 2026-03-14, or cancel TG-038. We will not choose for the customer.

<a id="event-005"></a>
## 2026-03-11 09:59:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Sella Nove, customer

Tallowmere Goods reports that the returned unit for TG-038 has been allocated to another order. It can approve dispatch of a new unit when stock arrives on 2026-03-14, or cancel TG-038. Which would you like?

<a id="event-006"></a>
## 2026-03-11 10:40:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Reshipment authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

On the customer's choice, we have approved dispatch of a new unit for TG-038 to Apartment 2, 31 Rillstone Walk once stock arrives on 2026-03-14. No shipment record exists yet, and nothing is dispatched before then.
