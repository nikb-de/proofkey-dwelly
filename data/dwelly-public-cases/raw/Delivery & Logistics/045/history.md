# Case 045 history — Import shipment is waiting for the shipper's commercial invoice

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-03-18 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Ossmere Trade Desk, appointed customs broker
- **To:** Iona Quill, Rivet Delivery Desk

For DL-045 / order OS-045 we need the shipper’s commercial invoice showing seller, buyer, invoice date and reference, goods description, quantity, unit value, currency, total and origin declaration. These are the missing fields in this file; no clearance decision has been made.

<a id="event-002"></a>
## 2026-03-18 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Broker portal
- **From:** Ossmere Trade Desk, appointed customs broker
- **To:** Iona Quill, Rivet Delivery Desk

Please request the complete invoice from authorised shipper Mavelle Export Studio. Do not fill in values or origin on their behalf.

<a id="event-003"></a>
## 2026-03-18 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Fera Noll, Mavelle Export Studio shipping lead

Please supply your commercial invoice for DL-045 / OS-045 with the fields the appointed broker listed: seller, buyer, date/reference, description, quantity, unit value/currency/total and origin declaration. The broker must review it.

<a id="event-004"></a>
## 2026-03-18 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Fera Noll, Mavelle Export Studio shipping lead
- **To:** Ossmere Trade Desk, appointed customs broker; Iona Quill, Rivet Delivery Desk

Our issued synthetic [commercial invoice CI-045](attachments/commercial-invoice.pdf) is supplied for DL-045 / OS-045. It covers 12 woven pouches at GBP 8.00 each, GBP 96.00 total, made in the fictional origin jurisdiction Aster Reach. Please review the stated fields.

<a id="event-005"></a>
## 2026-03-18 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Ossmere Trade Desk, appointed customs broker
- **To:** Iona Quill, Rivet Delivery Desk

CI-045 is received and all fields requested for this document package are complete. The package can proceed to our processing queue. Customs clearance and charges remain undecided.

