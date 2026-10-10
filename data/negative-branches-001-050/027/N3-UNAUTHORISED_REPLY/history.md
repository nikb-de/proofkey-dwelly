# Case 027-N3 history — Customer receives another customer's parcel (Addressee asks for holder's address)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 027; events 004–006 are this branch.

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
## 2026-02-28 11:10:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Sender stating they are the addressee of WP-027
- **To:** Iona Quill, Rivet Delivery Desk

My parcel was left at the wrong house and the courier will not tell me where. I am the addressee. Give me that customer's address and I will fetch it myself today.

<a id="event-005"></a>
## 2026-02-28 11:25:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Sender stating they are the addressee of WP-027

We cannot share any address or contact details, and we cannot arrange a handover between customers. Plover Arc Logistics holds the verified addressee record for this parcel. Please contact the carrier through your own tracking account, and it will deal with you through that record.

<a id="event-006"></a>
## 2026-02-28 12:10:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Misdelivery desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The addressee of WP-027 contacted us through their verified tracking account at 11:50 UTC. We are dealing with them through our own record and shared no details of the reporting customer. This contact does not change the collection under MD-027, which is not yet done.
