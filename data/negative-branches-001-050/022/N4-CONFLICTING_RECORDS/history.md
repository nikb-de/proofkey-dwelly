# Case 022-N4 history — A delivered household item is confirmed broken (Return logged versus returned-item inspection)

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
## 2026-02-23 09:48:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Replacement authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

We cannot approve TG-022 yet. A replacement needs the broken lamp back first, and no return is logged against TG-022 in our system. Please ask the customer to send it back.

<a id="event-005"></a>
## 2026-02-23 10:03:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Damage assessor, Tallowmere Goods; Replacement authorisations, Tallowmere Goods

Two TG-022 records disagree. The 09:00 UTC inspection record says the recipient report was reviewed against your returned-item inspection. Replacement authorisations wrote at 09:48 UTC that no return is logged against TG-022. Damage assessor, please confirm whether the lamp was returned and inspected under TG-022, and from which record. We have not asked Remi to send anything back.

<a id="event-006"></a>
## 2026-02-23 10:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Damage assessor, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

TG-022: the broken lamp was returned and inspected before our 09:00 UTC record, and the inspection entry holds the return. It was not linked to the order, so Replacement authorisations saw no return. It is now linked. This settles the return status only. The replacement approval is still with Replacement authorisations.
