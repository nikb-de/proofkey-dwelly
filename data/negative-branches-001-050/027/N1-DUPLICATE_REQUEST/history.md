# Case 027-N1 history — Customer receives another customer's parcel (Two collection jobs for WP-027)

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
## 2026-02-28 09:50:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Misdelivery collections, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

We now have two collection jobs for WP-027 at the same address: one raised by our intake team from MD-027 at 09:05 UTC and one from your 09:25 email. Which one should we run?

<a id="event-005"></a>
## 2026-02-28 10:05:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Misdelivery collections, Plover Arc Logistics

Both jobs are the same collection: sealed parcel WP-027 from Tovin Esk under MD-027. Please keep the 09:05 UTC job raised by your intake team and link our 09:25 UTC request to it, so that only one driver attends. Please confirm which job stays live.

<a id="event-006"></a>
## 2026-02-28 10:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Misdelivery collections, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The 09:05 UTC job is the one live collection job for WP-027 under MD-027. Your 09:25 UTC request is linked to it and closed as a duplicate. One live job is not a collection; WP-027 has not been collected yet.
