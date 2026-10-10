# Case 045-N5 history — Import shipment is waiting for the shipper's commercial invoice (Broker needs compliance officer review)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 045; events 005–007 are this branch.

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
## 2026-03-18 10:00:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Broker portal
- **From:** Ossmere Trade Desk, appointed customs broker
- **To:** Iona Quill, Rivet Delivery Desk

CI-045 for DL-045 states origin Aster Reach. Our procedure sends goods declared from Aster Reach to a compliance officer before we accept a package. I cannot mark the file complete or reject it. No officer review is booked yet.

<a id="event-006"></a>
## 2026-03-18 10:15:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Desk operator, Rivet Delivery Desk

Escalation for DL-045 / OS-045. Facts: Mavelle's commercial invoice CI-045 reached Ossmere Trade Desk at 09:50 UTC and states origin Aster Reach. Ossmere's procedure sends Aster Reach goods to a compliance officer before it accepts a package; it cannot mark the file complete or reject it, and no review is booked. Sources: CI-045 and Ossmere's broker-portal message of 10:00 UTC. Question: who books the officer review, and by when? Pending: completeness and clearance.

<a id="event-007"></a>
## 2026-03-19 11:30:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Broker portal
- **From:** Ossmere Trade Desk, appointed customs broker
- **To:** Iona Quill, Rivet Delivery Desk

Compliance officer review for DL-045 was booked by the Rivet desk operator, who owns the escalation, and completed at 11:10 UTC. The officer accepts the Aster Reach origin declaration on CI-045 for document review, and the package returns to our document check. This is not document completeness or customs clearance; charges remain undecided.
