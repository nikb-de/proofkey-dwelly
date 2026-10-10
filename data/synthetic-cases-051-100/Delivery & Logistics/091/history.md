# Case 091 history — Recipient wants to refuse a parcel the day after it was handed over

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-05-03 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-091 from Harrowmint Supply has a handover record: handed to verified recipient Brisa Wendle at 2026-05-02 16:20 UTC, signature captured. Refusal is available only at the door before handover. After handover, a rejection is a return request: Returns desk registers it with the handover record and books a collection only after the merchant authorises the return.

<a id="event-002"></a>
## 2026-05-03 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Brisa Wendle, recipient
- **To:** Iona Quill, Rivet Delivery Desk

The coffee grinder delivered yesterday is not what I wanted, and the box is still sealed. I want to refuse it and have your driver take it back tomorrow.

<a id="event-003"></a>
## 2026-05-03 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Returns desk, Plover Arc Logistics

Please register a return request for DL-091: the driver's handover record shows it was handed to the verified recipient at 2026-05-02 16:20 UTC, so this is not a refusal. Stated reason: unwanted item, box still sealed. Please attach the handover record, ask Harrowmint Supply for return authorisation, and do not book a collection until the merchant authorises it.

<a id="event-004"></a>
## 2026-05-03 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Returns desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Return request RR-091 is registered against DL-091 with the 2026-05-02 16:20 UTC handover record attached. Our authorisation request went to Harrowmint Supply at 09:45 UTC. No collection is booked, and the parcel remains with the recipient.

<a id="event-005"></a>
## 2026-05-03 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Brisa Wendle, recipient

DL-091 was handed over on 2026-05-02, so it can no longer be refused; Returns desk has registered it as return request RR-091. Harrowmint Supply must authorise the return before any collection is booked. A registered request is not an authorised return, and no refund has been decided.
