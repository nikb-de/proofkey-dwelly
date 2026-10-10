# Case 011-N3 history — Shipment tracking has not updated after depot arrival (Depot search does not find parcel)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 011; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-02-12 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-011 last public scan: destination depot arrival at 06:15 UTC on 2026-02-12. No sort or route scan is visible. Our system does not currently confirm the storage position.

<a id="event-002"></a>
## 2026-02-12 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Mera Olt, recipient
- **To:** Iona Quill, Rivet Delivery Desk

The tracker has not changed since early this morning. Could someone check whether the parcel is actually at the depot?

<a id="event-003"></a>
## 2026-02-12 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Depot work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Destination depot, Plover Arc Logistics

Please physically locate DL-011 and provide a new scan with its storage position. The existing arrival status alone does not answer Mera’s question.

<a id="event-004"></a>
## 2026-02-12 10:20:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Depot work queue
- **From:** Destination depot, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

We searched the inbound bay, the sort cages and the exceptions shelf for DL-011 between 09:40 and 10:15 UTC. The parcel was not found. The 06:15 arrival scan remains the last scan. We have not raised a trace.

<a id="event-005"></a>
## 2026-02-12 10:35:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Parcel trace team, Plover Arc Logistics

Please open a trace for DL-011. Its last scan is the destination depot arrival at 06:15 UTC on 2026-02-12, with no sort or route scan since. The destination depot searched the inbound bay, the sort cages and the exceptions shelf between 09:40 and 10:15 UTC and did not find it. Please reply with the trace reference.

<a id="event-006"></a>
## 2026-02-12 11:10:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Parcel trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Trace PT-011-04 is open for DL-011 from 11:05 UTC. It records the 06:15 UTC arrival scan and the depot's negative search as its starting points. This registers a search. It does not show where DL-011 is or that it is lost.
