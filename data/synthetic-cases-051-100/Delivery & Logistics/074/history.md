# Case 074 history — Routing never acknowledged a redirect and the depot scan is ambiguous

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-04-16 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-074 has a 07:15 UTC outbound sort scan at Lanthorn depot; that scan is used for both home routes and pickup-point linehauls, so it does not show the destination. A redirect to Brackenfold Counter was sent to Routing on 2026-04-15 at 17:30 UTC and has no acknowledgement. Routing applies one redirect per shipment and alone can confirm the saved destination.

<a id="event-002"></a>
## 2026-04-16 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Joss Ollerin, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Yesterday I asked for DL-074 to go to Brackenfold Counter instead of my flat, but nobody confirmed it. Today’s scan does not say where it is going. Please send the redirect again so I can be sure.

<a id="event-003"></a>
## 2026-04-16 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Routing, Plover Arc Logistics

Please confirm the saved destination and current state of DL-074: a redirect to Brackenfold Counter sent on 2026-04-15 at 17:30 UTC was never acknowledged, and the 07:15 UTC outbound sort scan does not show the route. Do not apply a second redirect or any new instruction until that state is known. We will act only on your reported record.

<a id="event-004"></a>
## 2026-04-16 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-074 carries one saved redirect to Brackenfold Counter, applied on 2026-04-15 at 17:42 UTC. The 07:15 UTC scan loaded it onto linehaul LH-74 to the counter, expected on 2026-04-17. No second redirect was applied. The parcel is in transit and has not arrived at the counter.

<a id="event-005"></a>
## 2026-04-16 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Joss Ollerin, recipient

Routing confirms your earlier redirect was saved once, so we have not sent it again. DL-074 is in transit to Brackenfold Counter, expected on 2026-04-17. It has not arrived yet; please wait for the counter’s arrival notice before going to collect.
