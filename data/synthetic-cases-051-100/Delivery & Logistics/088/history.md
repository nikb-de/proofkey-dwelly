# Case 088 history — Recipient withdraws a hold request after returning earlier than planned

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-04-30 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Depot operations, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-088 has been on hold at Brackenmoor depot since 2026-04-27 at the recipient's request, with release set for 2026-05-06. A hold is removed only by Depot operations on the verified recipient's withdrawal. Removal returns the parcel to normal routing; Scheduling then assigns a delivery date and notifies the recipient in the order thread.

<a id="event-002"></a>
## 2026-04-30 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Yanne Selvar, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I came back from my trip early and I am home now. Please cancel the hold on DL-088 so it can be delivered.

<a id="event-003"></a>
## 2026-04-30 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Depot operations, Plover Arc Logistics

Please record the withdrawal of the hold on DL-088 from verified recipient Yanne Selvar and remove the hold; make no other change, such as a redirect or a fixed slot. Please confirm what has already been executed on DL-088 since the hold was applied.

<a id="event-004"></a>
## 2026-04-30 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Depot operations, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Hold on DL-088 removed at 09:44 UTC. Nothing else was applied during the hold; the parcel stayed in the hold bay. DL-088 is back in normal routing at Brackenmoor depot. No delivery date is set; Scheduling assigns one in its next planning run.

<a id="event-005"></a>
## 2026-04-30 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Yanne Selvar, recipient

Depot operations removed the hold on DL-088 at 09:44 UTC, and the parcel is back in normal routing. No delivery date is set yet; Scheduling will assign one and notify you in this order thread. The parcel has not been delivered.
