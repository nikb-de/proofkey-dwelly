# Case 015-N1 history — Parcel has been routed to the wrong local depot (Transfer intake outage loses requests)

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
## 2026-02-16 11:20:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Notice: our transfer request intake failed between 09:00 and 11:00 UTC today. Emails received in that period may not have created transfer requests. Do not assume a request sent then is queued.

<a id="event-005"></a>
## 2026-02-16 11:35:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing control, Plover Arc Logistics

Our 09:25 UTC request to transfer DL-015 from North Sedgeglass to East Copperfin falls inside your intake outage. Is a transfer request for DL-015 saved? If not, we will submit it once. Please do not create a second transfer from any copy of the email.

<a id="event-006"></a>
## 2026-02-16 12:05:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

One transfer request for DL-015 is saved, reference TR-015-1, created at 09:26 UTC. No duplicate exists. This proves the request exists, not that DL-015 has left North Sedgeglass or reached East Copperfin.
