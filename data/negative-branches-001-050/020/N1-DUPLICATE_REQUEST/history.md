# Case 020-N1 history — A multi-parcel order arrives with one parcel still outstanding (Order-level trace duplicates carton trace)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 020; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-02-21 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Parcel support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Order TG-020 has parcels DL-020-A, DL-020-B and DL-020-C. A and B have delivery scans; C has an inbound depot scan only. All three are required to complete the order.

<a id="event-002"></a>
## 2026-02-21 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Eris Kael, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I received two of the three cartons for TG-020. The missing carton is DL-020-C. Please locate it; I am available tomorrow.

<a id="event-003"></a>
## 2026-02-21 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Parcel trace team, Plover Arc Logistics

Please trace DL-020-C specifically and arrange its remaining delivery. Do not mark TG-020 complete using only the A and B scans.

<a id="event-004"></a>
## 2026-02-21 09:40:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Parcel trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

We now have two open traces: yours for DL-020-C and one opened by Parcel support at 09:15 UTC for the whole order TG-020. Each trace can arrange a delivery.

<a id="event-005"></a>
## 2026-02-21 09:55:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Parcel trace team, Plover Arc Logistics

Please link Parcel support's 09:15 UTC order-level trace for TG-020 to our trace for DL-020-C and run one trace with one delivery arrangement for DL-020-C. Please do not create a second delivery. TG-020 must not be closed on the A and B delivery scans.

<a id="event-006"></a>
## 2026-02-21 10:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Parcel trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The 09:15 UTC order-level trace is now linked to the DL-020-C trace and closed. One trace remains open, for DL-020-C only, and TG-020 stays open. This settles the duplicate; we have not yet located the carton.
