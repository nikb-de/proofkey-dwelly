# Case 011-N4 history — Shipment tracking has not updated after depot arrival (Second locate task opened by phone)

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
## 2026-02-12 09:40:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Mera Olt also called us at 09:30 UTC about DL-011. We raised a second locate task for the destination depot at 09:34 UTC. Both tasks are now open in the Depot work queue.

<a id="event-005"></a>
## 2026-02-12 09:55:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Depot work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Destination depot, Plover Arc Logistics

Two locate tasks are open for DL-011: ours at 09:25 UTC and one from Tracking support at 09:34 UTC after Mera Olt's call. Please link the 09:34 task to the 09:25 task, work DL-011 once and report one scan with one storage position on the 09:25 task. Please do not run a second search.

<a id="event-006"></a>
## 2026-02-12 10:15:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Depot work queue
- **From:** Destination depot, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The 09:34 UTC task is now linked to the 09:25 UTC task and closed as a duplicate. One locate task for DL-011 remains open, and any scan will be posted there. This settles the duplicate. It does not yet give DL-011's location.
