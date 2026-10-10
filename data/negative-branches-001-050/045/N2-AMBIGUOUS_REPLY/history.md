# Case 045-N2 history — Import shipment is waiting for the shipper's commercial invoice (Invoice supplied without origin declaration)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 045; events 004–006 are this branch.

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
## 2026-03-18 09:45:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Fera Noll, Mavelle Export Studio shipping lead
- **To:** Iona Quill, Rivet Delivery Desk

Our invoice for DL-045 / OS-045 is attached with seller, buyer, date, reference, goods, quantity and values. We do not normally put an origin statement on it, as the goods come from more than one workshop. Is that enough?

<a id="event-005"></a>
## 2026-03-18 10:00:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Fera Noll, Mavelle Export Studio shipping lead

The appointed broker's list for DL-045 / OS-045 includes an origin declaration on the commercial invoice. Please add Mavelle's own origin declaration to the invoice and send the revised version. We cannot write the origin in for you.

<a id="event-006"></a>
## 2026-03-18 11:00:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Fera Noll, Mavelle Export Studio shipping lead
- **To:** Iona Quill, Rivet Delivery Desk

Revised commercial invoice CI-045 for DL-045 / OS-045 is attached, with our origin declaration: made in Aster Reach. All other fields are unchanged. Ossmere Trade Desk still has to review it for completeness; nothing is cleared.
