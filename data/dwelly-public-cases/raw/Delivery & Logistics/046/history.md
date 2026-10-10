# Case 046 history — Import broker needs the consignee to appoint it before processing

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-03-19 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Ossmere Trade Desk, customs broker
- **To:** Iona Quill, Rivet Delivery Desk

DL-046 is waiting for a consignee mandate. Our fictional procedure requires the registered authorised signatory to accept the shipment-specific mandate in the verified business portal. No passport or banking credentials are required in this exercise.

<a id="event-002"></a>
## 2026-03-19 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Celand Arc Imports account administrator
- **To:** Iona Quill, Rivet Delivery Desk

Account register excerpt: Mara Vesk, director, is the authorised signatory for broker appointment on DL-046. Her verified business-portal channel is active. Please ask her to complete the mandate; our operator account cannot sign it.

<a id="event-003"></a>
## 2026-03-19 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Business portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Mara Vesk, Celand Arc authorised director

Please complete Ossmere’s shipment-specific broker mandate for DL-046 through your verified business portal. The account register records your signing authority; the broker must confirm acceptance.

<a id="event-004"></a>
## 2026-03-19 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Business portal
- **From:** Mara Vesk, Celand Arc authorised director
- **To:** Ossmere Trade Desk, customs broker; Iona Quill, Rivet Delivery Desk

I accepted mandate MND-046 for DL-046 in the verified portal at 09:42 UTC. It authorises Ossmere to process this shipment, not unrelated payments or future mandates.

<a id="event-005"></a>
## 2026-03-19 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Broker portal
- **From:** Ossmere Trade Desk, customs broker
- **To:** Iona Quill, Rivet Delivery Desk

MND-046 is accepted against the registered signatory Mara Vesk. Broker appointment is complete for DL-046; clearance is still pending.

