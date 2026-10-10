# Case 049-N4 history — Duplicate delivery service charge appears on a business invoice (Two review tickets risk double credit)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 049; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-22 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Business portal
- **From:** Vera Senn, Mossline Press finance coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Inline invoice INV-049: line 1 delivery service DL-049, 2026-03-22, GBP 18.00; line 2 delivery service DL-049, 2026-03-22, GBP 18.00; invoice total GBP 36.00. Both lines have the same service key. No separate service is listed.

<a id="event-002"></a>
## 2026-03-22 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Vera Senn, Mossline Press finance coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Please ask billing to review the duplicate before we pay this invoice. We have not paid either line.

<a id="event-003"></a>
## 2026-03-22 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Business billing, Plover Arc Logistics

Please review INV-049’s two GBP 18.00 lines for the same DL-049 delivery service and date. If duplication is confirmed, issue the authorised credit and revised invoice balance.

<a id="event-004"></a>
## 2026-03-22 09:45:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Business billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

We hold two review requests for INV-049: ticket BR-049, raised by Mossline Press in our billing portal at 09:05 UTC, and your email of 09:25 UTC. Unless told otherwise, each will be reviewed and credited separately.

<a id="event-005"></a>
## 2026-03-22 10:00:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Business billing, Plover Arc Logistics

Ticket BR-049 and our email of 09:25 UTC are the same review request for INV-049. Please link our email to BR-049 and run one review, with at most one GBP 18.00 credit if the duplicate is confirmed. Please do not review or credit them separately.

<a id="event-006"></a>
## 2026-03-22 10:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Business billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Your email is linked to ticket BR-049. INV-049 has one open review and can receive at most one GBP 18.00 credit. The merge does not decide whether line 2 is a duplicate; the review is still in progress.
