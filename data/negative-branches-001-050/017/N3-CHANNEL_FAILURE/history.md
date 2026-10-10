# Case 017-N3 history — Delivery notification contains an unusable tracking link (Corrected reference send status unknown)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 017; events 004–006 are this branch.

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
## 2026-02-18 09:45:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Notification support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

We sent the corrected DL-017 reference to Vela's verified order thread at 09:38 UTC. The template service timed out and the send status shows 'unknown'. We cannot confirm whether the message reached the thread.

<a id="event-005"></a>
## 2026-02-18 10:00:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Notification support, Plover Arc Logistics

Please check the saved message log of Vela's verified order thread for the 09:38 UTC send of the DL-017 reference before any resend. If one complete message is there, send nothing more. If none is there, resend once. Please do not create a second message otherwise.

<a id="event-006"></a>
## 2026-02-18 10:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Notification support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The message log for Vela's verified order thread shows the 09:38 UTC message delivered once, with the full DL-017 reference and portal steps. We have not resent it. This proves the reference was sent, not that the parcel is delivered.
