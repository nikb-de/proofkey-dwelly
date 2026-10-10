# Case 020-N2 history — A multi-parcel order arrives with one parcel still outstanding (Next-day route full after locating carton)

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
## 2026-02-21 10:30:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Parcel trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-020-C has been located in depot stock. Capacity on the 2026-02-22 route for this area filled at 10:15 UTC. Available: delivery on 2026-02-23, 09:00–13:00 UTC, or depot collection from 2026-02-22, 10:00 UTC. Nothing is booked.

<a id="event-005"></a>
## 2026-02-21 10:45:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Eris Kael, recipient

DL-020-C has been located in depot stock, but the 2026-02-22 delivery route is now full. The carrier offers delivery on 2026-02-23, 09:00–13:00 UTC, or depot collection from 2026-02-22, 10:00 UTC. Nothing is booked. Which would you like?

<a id="event-006"></a>
## 2026-02-21 11:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Parcel trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Eris's choice, relayed by you at 11:05 UTC, is recorded: DL-020-C is set for depot collection from 2026-02-22, 10:00 UTC. It has not been collected. TG-020 remains at two of three cartons received.
