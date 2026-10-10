# Case 027-N4 history — Customer receives another customer's parcel (Collection attempt fails, card left)

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
## 2026-02-28 16:40:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Misdelivery collections, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Collection of WP-027 was attempted at 16:15 UTC at the verified address. No one answered and a card was left. The parcel was not collected and no new attempt is booked.

<a id="event-005"></a>
## 2026-02-28 16:55:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Misdelivery collections, Plover Arc Logistics

WP-027 was not collected at 16:15 UTC and no new attempt is booked. Please book the next collection attempt under MD-027 at the verified address and confirm the slot, so that we can pass it to Tovin Esk. The parcel stays sealed with him; we are not asking him to take it anywhere.

<a id="event-006"></a>
## 2026-02-28 17:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Misdelivery collections, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The next collection attempt for WP-027 is booked for 2026-03-01, 11:00 to 13:00 UTC, at the verified address under MD-027. A booked attempt is not a collection. Tovin's own delivery remains under separate trace.
