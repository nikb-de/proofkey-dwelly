# Case 004-N2 history — Recipient requests a call shortly before arrival (Callback request lost in channel rebuild)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 004; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-02-05 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-004 is on the 2026-02-06 afternoon route. For this route we can add a call request using the verified number already in the order record; we cannot guarantee an exact advance interval.

<a id="event-002"></a>
## 2026-02-05 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Oren Sile, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Could the driver call shortly before reaching me? I work in the studio next door and need a few minutes to walk over. Use my saved order contact.

<a id="event-003"></a>
## 2026-02-05 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Dispatch chat
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

Please record Oren’s request on DL-004: call the verified saved order contact shortly before arrival, if route conditions allow. No contact change is requested.

<a id="event-004"></a>
## 2026-02-05 09:26:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Dispatch chat
- **From:** Dispatch chat system, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Message from Iona Quill, Rivet Delivery Desk, to Dispatch: send status unknown. The 2026-02-06 afternoon route channel was being rebuilt at 09:25, and messages from that minute may not have reached the route card queue. No read receipt is recorded.

<a id="event-005"></a>
## 2026-02-05 09:41:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

Our 09:25 Dispatch chat message about DL-004 shows send status unknown after the route channel rebuild. Does the DL-004 route card already show a call request to the verified saved order contact? Please do not create a second change. We will send no second request until we know.

<a id="event-006"></a>
## 2026-02-05 10:05:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The DL-004 route card shows one call request to the verified saved order contact, saved at 09:27. There is no duplicate. The route is still scheduled for 2026-02-06; no call or arrival has occurred.
