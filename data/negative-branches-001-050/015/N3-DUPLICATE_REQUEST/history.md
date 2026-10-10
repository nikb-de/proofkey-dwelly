# Case 015-N3 history — Parcel has been routed to the wrong local depot (Second transfer request from phone call)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 015; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-02-16 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-015 is at North Sedgeglass depot; its destination is Merrow Quay, served by East Copperfin depot. Routing error confirmed. No delivery attempt is scheduled.

<a id="event-002"></a>
## 2026-02-16 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Kiva Rell, recipient
- **To:** Iona Quill, Rivet Delivery Desk

The tracker shows a depot in the wrong area. Can you get my parcel to the local depot before arranging delivery?

<a id="event-003"></a>
## 2026-02-16 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing control, Plover Arc Logistics

Please transfer DL-015 from North Sedgeglass to East Copperfin. Send the destination receipt scan, not just a planned linehaul entry.

<a id="event-004"></a>
## 2026-02-16 10:05:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

We now hold two transfer requests for DL-015: yours at 09:25 UTC and one from Tracking support at 09:40 UTC after a call from Kiva Rell. Both ask for transfer to East Copperfin. Both are open.

<a id="event-005"></a>
## 2026-02-16 10:20:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing control, Plover Arc Logistics

Please link Tracking support's 09:40 UTC transfer request for DL-015 to our 09:25 UTC request and run one transfer to East Copperfin only. Keep the 09:25 request as the open one. Please do not book a second linehaul movement.

<a id="event-006"></a>
## 2026-02-16 10:50:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The 09:40 UTC request is linked to your 09:25 UTC request and closed. One transfer of DL-015 to East Copperfin remains open, with one linehaul movement planned. This settles the duplicate, not East Copperfin receipt.
