# Case 015-N2 history — Parcel has been routed to the wrong local depot (Linehaul record contradicts shelf check)

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
## 2026-02-16 16:40:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Our transfer record shows DL-015 loaded on the 14:30 UTC linehaul from North Sedgeglass to East Copperfin. The North Sedgeglass shelf check at 15:50 UTC still lists DL-015 on its outbound shelf. We have not resolved which is correct.

<a id="event-005"></a>
## 2026-02-16 16:55:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing control, Plover Arc Logistics

Your transfer record shows DL-015 loaded on the 14:30 UTC linehaul, but the 15:50 UTC shelf check still lists it at North Sedgeglass. We are keeping both records and will report nothing to Kiva yet. Please get a physical scan of DL-015, either at North Sedgeglass or on arrival at East Copperfin.

<a id="event-006"></a>
## 2026-02-16 18:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

North Sedgeglass found DL-015 on its outbound shelf at 17:55 UTC and scanned it. The 14:30 UTC loading entry was made in error. The parcel is now planned for the 06:00 UTC linehaul tomorrow. This fixes its location; only an East Copperfin receipt scan proves the transfer.
