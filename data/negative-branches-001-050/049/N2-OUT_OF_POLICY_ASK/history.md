# Case 049-N2 history — Duplicate delivery service charge appears on a business invoice (Customer wants refund plus goodwill waiver)

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
## 2026-03-22 09:35:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Vera Senn, Mossline Press finance coordinator
- **To:** Iona Quill, Rivet Delivery Desk

While billing looks at it, please ask them to pay the duplicate GBP 18.00 back to our bank, and to waive the other line as goodwill for the trouble. Then we owe nothing.

<a id="event-005"></a>
## 2026-03-22 09:50:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Business portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Vera Senn, Mossline Press finance coordinator

Neither line on INV-049 has been paid, so there is nothing to refund. We cannot ask billing to waive the other GBP 18.00 line as goodwill. Billing's review can credit a confirmed duplicate, which would leave GBP 18.00 due on the GBP 36.00 invoice.

<a id="event-006"></a>
## 2026-03-22 10:05:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Business portal
- **From:** Vera Senn, Mossline Press finance coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Understood. We will not ask for a refund or a waiver. We will wait for billing's review of INV-049 and pay only the revised balance it shows. Nothing has been paid, and no credit is confirmed yet.
