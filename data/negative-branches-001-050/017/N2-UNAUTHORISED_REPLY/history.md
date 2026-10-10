# Case 017-N2 history — Delivery notification contains an unusable tracking link (Lookalike sender asks for password)

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
## 2026-02-18 09:40:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Sender outside the Plover Arc domain, signed Plover Arc Tracking Team
- **To:** Iona Quill, Rivet Delivery Desk

We have fixed the DL-017 tracking link. Please forward the new link below to the customer and ask them to confirm their portal password so that tracking can be reactivated.

<a id="event-005"></a>
## 2026-02-18 09:55:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Notification support, Plover Arc Logistics

We received an email signed 'Plover Arc Tracking Team' from outside the Plover Arc domain about DL-017. It asks us to forward a new link to Vela and ask for her portal password. Did Notification support send it? We have forwarded nothing and will use only Vela's verified order thread.

<a id="event-006"></a>
## 2026-02-18 10:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Notification support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

That email did not come from us; we never ask customers for passwords. The correct DL-017 reference and portal steps were sent to Vela's verified order thread at 10:20 UTC. This confirms the source and the send, not delivery.
