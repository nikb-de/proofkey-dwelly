# Case 030-N4 history — A high-value shipment lacks an accessible proof-of-delivery record (Two handover times disagree)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 030; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-03-03 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Secure shipment support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-030 belongs to authenticated recipient Iven Thoss. Its delivery flag is present but the customer-facing handover record has not populated. We may release the shipment-specific redacted record through this verified thread.

<a id="event-002"></a>
## 2026-03-03 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Iven Thoss, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I did receive the camera accessory. Please obtain the matching handover record so I can reconcile the delivery time in my order history.

<a id="event-003"></a>
## 2026-03-03 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Secure shipment support, Plover Arc Logistics

Please provide the permitted redacted handover record for DL-030 through Iven’s verified order thread. Do not expose driver or unrelated recipient personal details.

<a id="event-004"></a>
## 2026-03-03 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Secure shipment support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Inline handover record: reference POD-030; shipment DL-030; receiver Iven Thoss; 2026-03-03 08:20 UTC; status handed to named recipient; order destination matched. The redacted record is now visible in the customer thread.

<a id="event-005"></a>
## 2026-03-03 10:02:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Iven Thoss, recipient
- **To:** Iona Quill, Rivet Delivery Desk

POD-030 says 08:20 UTC, but I signed for the parcel before I left home at about 07:55 UTC, and my order history shows delivered at 07:58 UTC. Which time is right?

<a id="event-006"></a>
## 2026-03-03 10:17:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Secure shipment support, Plover Arc Logistics

DL-030: two handover times disagree. POD-030 records 08:20 UTC. Iven Thoss's order history shows delivered at 07:58 UTC, and he says he signed before leaving home at about 07:55 UTC. We are keeping both on record. Which source produced the 08:20 UTC handover time, and which produced the 07:58 UTC order-history time?

<a id="event-007"></a>
## 2026-03-03 10:50:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Secure shipment support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

For DL-030, the 07:58 UTC order-history time comes from the driver's device scan at the door. The 08:20 UTC time in POD-030 is when that handover record synced to our server. Both are logged. This explains the two sources for this handover only and is not proof for any other dispute.
