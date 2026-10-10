# Case 047-N4 history — Customer asks for an explanation of a carrier-issued import charge (Billing ticketing outage, request unlogged)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 047; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-20 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Import support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Charge notice IC-047 for DL-047 totals GBP 32.00. The itemisation is held by our billing team. This is a fictional operator notice; payment is not confirmed.

<a id="event-002"></a>
## 2026-03-20 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Teren Osk, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Please explain the GBP 32.00 charge before I decide what to do. I do not understand which part is handling and which part is the import assessment.

<a id="event-003"></a>
## 2026-03-20 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Import billing, Plover Arc Logistics

Please provide the itemised explanation for IC-047 / DL-047 through Teren’s verified order thread, including the total. This is a request for information, not payment authorisation.

<a id="event-004"></a>
## 2026-03-20 09:27:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Mail system, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Automatic reply from Import billing: our ticketing system is unavailable between 09:20 and 10:00 UTC. Messages received in this period may not be logged. No ticket number has been issued for your message.

<a id="event-005"></a>
## 2026-03-20 09:42:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Import billing, Plover Arc Logistics

Our email of 09:25 UTC asked for the itemised IC-047 / DL-047 explanation, and your ticketing system was down when it arrived. Once the system is back after 10:00 UTC, please check whether that request is logged. We will not resend it, so that no second ticket is opened.

<a id="event-006"></a>
## 2026-03-20 10:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Import billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

One request for the IC-047 / DL-047 breakdown is logged, received at 09:25 UTC. No second ticket exists. The breakdown is not yet supplied; this confirms only that the request is on file.
