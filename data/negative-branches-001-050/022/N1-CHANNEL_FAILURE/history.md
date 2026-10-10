# Case 022-N1 history — A delivered household item is confirmed broken (Mail gateway times out on request)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 022; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-02-23 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Damage assessor, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Inline inspection record TG-022: ceramic table lamp arrived with a separated base; recipient report reviewed against our returned-item inspection. Damage accepted for replacement assessment. Dispatch DL-022 has completed; replacement approval is not yet recorded.

<a id="event-002"></a>
## 2026-02-23 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Remi Dask, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I would prefer the same lamp rather than a refund. Please ask the merchant to approve a replacement.

<a id="event-003"></a>
## 2026-02-23 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Replacement authorisations, Tallowmere Goods

Please approve a like-for-like lamp replacement for TG-022 using your accepted inspection record. Remi has selected replacement in the order thread.

<a id="event-004"></a>
## 2026-02-23 09:27:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Mail system, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Delivery status unknown for your message to Replacement authorisations sent at 09:25 UTC. The mailbox gateway timed out after accepting part of the message. It may or may not have reached the team. No ticket reference was returned.

<a id="event-005"></a>
## 2026-02-23 09:42:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Damage assessor, Tallowmere Goods

Our 09:25 UTC email asking Replacement authorisations to approve a like-for-like lamp replacement for TG-022 hit a gateway timeout, and no ticket reference came back. Please check the TG-022 record and tell us whether a replacement request is now logged against it. Please do not create a second request. We will not send one until you answer.

<a id="event-006"></a>
## 2026-02-23 10:05:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Damage assessor, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

One replacement request is logged against TG-022, received from your desk at 09:25 UTC and assigned to Replacement authorisations. No second request exists. A logged request is not an approval. No replacement order has been created.
