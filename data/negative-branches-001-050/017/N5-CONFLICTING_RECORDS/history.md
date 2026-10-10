# Case 017-N5 history — Delivery notification contains an unusable tracking link (Portal shows delivered, recipient has nothing)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 017; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-02-18 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Notification support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-017 notification path was truncated by our template. The account-linked notification belongs to this recipient; the shipment reference itself is intact in our order record.

<a id="event-002"></a>
## 2026-02-18 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Vela Morn, recipient
- **To:** Iona Quill, Rivet Delivery Desk

The tracking link in my notification does not open. Please give me the correct way to find this parcel in the order portal.

<a id="event-003"></a>
## 2026-02-18 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Notification support, Plover Arc Logistics

Please send Vela the correct DL-017 tracking reference and portal navigation through the verified order thread. Do not send a payment request or ask for credentials.

<a id="event-004"></a>
## 2026-02-18 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Notification support, Plover Arc Logistics
- **To:** Vela Morn, recipient; Iona Quill, Rivet Delivery Desk

In your existing order portal choose Shipments, then enter DL-017. The corrected notification uses https://tracking.ploverarc.example/shipments/DL-017. This exercise URL is inert; the fictional portal record is the source.

<a id="event-005"></a>
## 2026-02-18 10:00:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Vela Morn, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I entered DL-017 under Shipments. The page shows the parcel as delivered yesterday at 17:20 UTC. I have not received any parcel.

<a id="event-006"></a>
## 2026-02-18 10:15:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Tracking support, Plover Arc Logistics

Vela Morn reports that the portal shows DL-017 delivered at 17:20 UTC yesterday, but she has received no parcel. We are keeping both the portal status and her statement. Please send the scan record behind that delivered status, with any handover detail such as location, signature or photo.

<a id="event-007"></a>
## 2026-02-18 11:00:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The delivered status for DL-017 comes from a handset scan at 17:20 UTC on 2026-02-17, recorded as left in a safe place, with no signature or photo attached. This shows what the handset recorded. It does not show where the parcel is now or who has it.
