# Case 011-N2 history — Shipment tracking has not updated after depot arrival (Depot leaves locate task unstarted)

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
## 2026-02-12 13:30:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Depot work queue
- **From:** Depot work queue, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-011 locate task, opened 09:25 UTC: status open, not started. No comment from the destination depot. Tasks not started by the 14:00 UTC shift change are carried to the next shift.

<a id="event-005"></a>
## 2026-02-12 13:45:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Depot work queue
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Destination depot, Plover Arc Logistics

Reminder on this task: please physically locate DL-011 and post a new scan with its storage position before the 14:00 UTC shift change. If the task is not started by then, it passes to the next shift and Mera Olt waits longer for an answer. The 06:15 UTC arrival scan alone does not answer her question.

<a id="event-006"></a>
## 2026-02-12 13:58:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Depot work queue
- **From:** Destination depot, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

At 13:52 UTC we found DL-011 on inbound shelf B-04 and scanned the label. The new location scan is now visible. It has not been sorted or allocated to a van. This confirms its position at the depot, not dispatch or delivery.
