# Case 031-N2 history — Return approved but the customer has no return label (Approval re-saved with two return methods)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 031; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-04 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Returns support, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Return RT-031 for TG-031 / DL-031 is approved. The label field is empty. Our authorised label team needs to issue the label against RT-031 before the customer can prepare the return.

<a id="event-002"></a>
## 2026-03-04 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Kessa Ulm, customer
- **To:** Iona Quill, Rivet Delivery Desk

The return is approved but there is nothing to print in my order. Please obtain my return label.

<a id="event-003"></a>
## 2026-03-04 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Return label team, Tallowmere Goods

Please issue the missing printable return label for RT-031, matching TG-031 and original shipment DL-031. Send it in the verified returns thread.

<a id="event-004"></a>
## 2026-03-04 09:48:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Return label team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Returns support re-saved RT-031 at 09:35. The label type now depends on the return method, and the record offers two: drop-off at a staffed counter, or doorstep collection booked separately. We generate one label for the method the customer chooses. Nothing has been issued yet.

<a id="event-005"></a>
## 2026-03-04 10:03:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Kessa Ulm, customer

Tallowmere Goods has updated return RT-031, and the label now depends on how you send the parcel back. Which do you want: drop-off at a staffed counter, or a doorstep collection? A collection would still need its own booking after the label is issued.

<a id="event-006"></a>
## 2026-03-04 10:45:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Return label team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

On the customer's choice of staffed counter drop-off, we have issued one label, RL-031, for RT-031. No collection label was created. This is a label, not a drop-off: the parcel is still with the customer, and receipt and refund are not affected.
