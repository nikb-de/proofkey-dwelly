# Case 015-N4 history — Parcel has been routed to the wrong local depot (Recipient stops transfer to collect)

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
## 2026-02-16 10:30:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Kiva Rell, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Please stop the transfer. North Sedgeglass is near my work and I would rather collect DL-015 there today. Do not move it.

<a id="event-005"></a>
## 2026-02-16 10:45:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing control, Plover Arc Logistics

Kiva Rell has asked us to stop the transfer of DL-015. Please record the stop and take no new transfer action on DL-015. What had already been done before this message: was a transfer booked, and has the parcel moved?

<a id="event-006"></a>
## 2026-02-16 11:15:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Stop recorded for DL-015 at 11:05 UTC. Before it, a transfer was booked on the 14:30 UTC linehaul, but the parcel has not moved and is still at North Sedgeglass. No new transfer action will be taken. This does not authorise collection at North Sedgeglass.
