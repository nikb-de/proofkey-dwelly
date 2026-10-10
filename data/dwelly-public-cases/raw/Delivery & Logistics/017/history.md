# Case 017 history — Delivery notification contains an unusable tracking link

All identities, records and communications are fictional. Total events: 5.

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
## 2026-02-18 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Vela Morn, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Using Shipments and reference DL-017, I can now see the right parcel and its depot status.

