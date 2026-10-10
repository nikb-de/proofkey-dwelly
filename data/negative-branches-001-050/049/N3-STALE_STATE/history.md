# Case 049-N3 history — Duplicate delivery service charge appears on a business invoice (Invoice paid in full mid-review)

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
## 2026-03-22 09:40:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Vera Senn, Mossline Press finance coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Bad news. Our payment run released INV-049 in full, GBP 36.00, at 09:35 UTC before I could hold it. So both lines are now paid. What happens to the review?

<a id="event-005"></a>
## 2026-03-22 09:55:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Business billing, Plover Arc Logistics

Mossline Press reports that its payment run paid INV-049 in full, GBP 36.00, at 09:35 UTC. If you confirm that line 2 duplicates line 1, what settlement options apply to the GBP 18.00 paid for it? We will pass the options to Vera Senn to choose.

<a id="event-006"></a>
## 2026-03-22 10:45:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Business billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Payment of GBP 36.00 against INV-049 is received. Line 2 is confirmed as a duplicate of line 1. Options for the GBP 18.00: a credit on the Mossline Press account against future invoices, or a refund to the paying account. Vera Senn must choose. Neither is posted yet, and no money has moved back.
