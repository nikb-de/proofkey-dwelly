# Case 006-N2 history — Customer requests collection from a staffed pickup point (Routing ticket creation failed)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 006; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-02-07 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Routing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-006 is redirectable without charge before route release. Copperfin Counter has space and is open 10:00–18:00 UTC on 2026-02-08. We need the customer’s recorded choice before transfer.

<a id="event-002"></a>
## 2026-02-07 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Pella Rusk, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Please send DL-006 to Copperfin Counter, rather than my home. I can collect there on 2026-02-08.

<a id="event-003"></a>
## 2026-02-07 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing, Plover Arc Logistics

Pella has chosen Copperfin Counter in the verified order thread. Please redirect eligible parcel DL-006 and notify us only when the counter has physically received it.

<a id="event-004"></a>
## 2026-02-07 09:27:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Routing request system, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Automatic reply. Your message about DL-006 was received at 09:25. Ticket creation failed with a system error, so no reference number was issued. Your request may not appear in the Routing queue.

<a id="event-005"></a>
## 2026-02-07 09:42:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Dispatch chat
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing, Plover Arc Logistics

Our 09:25 email asking you to redirect DL-006 to Copperfin Counter was received, but ticket creation failed and no reference was issued. What does DL-006's saved destination show now? Please do not create a second change. We will send no second redirect request until we know.

<a id="event-006"></a>
## 2026-02-07 10:05:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Dispatch chat
- **From:** Routing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-006's saved destination is Copperfin Counter. Your 09:25 request reached our queue despite the ticket error and was applied once at 09:38. There is one transfer task. The counter has not yet received the parcel.
