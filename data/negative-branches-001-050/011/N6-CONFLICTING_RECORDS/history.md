# Case 011-N6 history — Shipment tracking has not updated after depot arrival (Tracker says out for delivery)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 011; events 005–007 are this branch.

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
## 2026-02-12 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Depot work queue
- **From:** Destination depot, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

At 09:45 UTC we found DL-011 in sort cage C-17 and scanned the label. The new location scan is now visible. It has not been allocated to a van yet.

<a id="event-005"></a>
## 2026-02-12 10:10:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Public tracking for DL-011 now shows 'Out for delivery' timestamped 09:48 UTC. The depot's 09:45 scan places it in sort cage C-17, not allocated to a van. We have not checked which entry is correct.

<a id="event-006"></a>
## 2026-02-12 10:25:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Depot work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Destination depot, Plover Arc Logistics

Public tracking for DL-011 shows 'Out for delivery' at 09:48 UTC, while your 09:45 UTC scan places it in sort cage C-17, not allocated to a van. We are keeping both records. Please physically check cage C-17, rescan DL-011 and send any van allocation record for it.

<a id="event-007"></a>
## 2026-02-12 10:50:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Depot work queue
- **From:** Destination depot, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

At 10:42 UTC DL-011 was still in sort cage C-17 and we rescanned it. No van allocation record exists for DL-011, so the 'Out for delivery' entry has no matching scan. This fixes its current location, not a delivery time.
