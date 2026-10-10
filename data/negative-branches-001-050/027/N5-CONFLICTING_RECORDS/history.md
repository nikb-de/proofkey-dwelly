# Case 027-N5 history — Customer receives another customer's parcel (Receipt recorded, parcel still there)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 027; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-02-28 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Misdelivery desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Inline minimised carrier intake record MD-027: wrong parcel matched to internal label reference WP-027; reporting customer Tovin Esk and collection address verified in the carrier intake process. Do not copy the other recipient’s address into this thread. Collection is allowed from the reporting customer.

<a id="event-002"></a>
## 2026-02-28 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Tovin Esk, reporting customer
- **To:** Iona Quill, Rivet Delivery Desk

The courier left someone else’s parcel. It is unopened. Can you arrange collection? My own order has not arrived.

<a id="event-003"></a>
## 2026-02-28 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Misdelivery collections, Plover Arc Logistics

Please collect sealed parcel WP-027 from Tovin using MD-027’s verified address and saved contact. Do not ask Tovin to open or forward it. Track their own outstanding order separately.

<a id="event-004"></a>
## 2026-03-01 11:45:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Misdelivery collections, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

WP-027 was collected from Tovin at 11:35 UTC on 2026-03-01; receipt COL-027 is recorded in MD-027. It is back in carrier custody. Tovin’s own delivery remains under separate trace.

<a id="event-005"></a>
## 2026-03-01 12:05:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Tovin Esk, reporting customer
- **To:** Iona Quill, Rivet Delivery Desk

I got a notice that the parcel was collected from me at 11:35 UTC. Nobody collected anything from me today. The other parcel is still sealed in my hallway.

<a id="event-006"></a>
## 2026-03-01 12:20:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Misdelivery collections, Plover Arc Logistics

MD-027: receipt COL-027 records WP-027 collected from Tovin Esk at 11:35 UTC today. At 12:05 UTC Tovin reported that nobody collected anything from him and the parcel is still sealed in his hallway. We are keeping both accounts. What evidence supports the 11:35 UTC collection, and which parcel did the driver take?

<a id="event-007"></a>
## 2026-03-01 13:15:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Misdelivery collections, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Both accounts are logged in MD-027. The driver confirms he did not reach the address; the 11:35 UTC entry was scanned from the job list, not from a parcel. WP-027 is not in carrier custody and remains with Tovin. A new collection will be booked. This decides no fault, and Tovin's own order stays under separate trace.
