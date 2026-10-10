# Case 015-N5 history — Parcel has been routed to the wrong local depot (Torn label blocks relabelling)

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
## 2026-02-16 13:10:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

North Sedgeglass found DL-015 for the transfer, but the address label is torn and the destination line is unreadable. It cannot be relabelled for East Copperfin until the Address desk confirms the destination from the order record. It has not moved.

<a id="event-005"></a>
## 2026-02-16 13:25:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Address desk, Plover Arc Logistics

North Sedgeglass cannot relabel DL-015 for its transfer to East Copperfin because the address label is torn and the destination line is unreadable. Please confirm DL-015's destination from the order record directly to Routing control, Plover Arc Logistics, so the parcel can be relabelled. We are not supplying an address from our case messages.

<a id="event-006"></a>
## 2026-02-16 14:40:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing control, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The Address desk confirmed DL-015's destination from the order record at 14:05 UTC. North Sedgeglass relabelled the parcel for East Copperfin at 14:30 UTC. It has not left North Sedgeglass. This is a relabel, not a transfer or an East Copperfin receipt.
