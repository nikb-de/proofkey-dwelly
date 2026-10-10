# Case 049-N1 history — Duplicate delivery service charge appears on a business invoice (Account statement ignores the credit)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 049; events 005–007 are this branch.

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
## 2026-03-22 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Business billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Duplicate confirmed: line 2 repeats line 1, not a second service. [Credit and revised statement](attachments/credit-statement.pdf): CN-049 credits GBP 18.00 against INV-049; revised amount due GBP 18.00. No money has been refunded because nothing was paid.

<a id="event-005"></a>
## 2026-03-22 10:05:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Business billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Automated account statement for Mossline Press, generated 10:00 UTC. INV-049: GBP 36.00 outstanding. Credits applied: none. Payments received: none.

<a id="event-006"></a>
## 2026-03-22 10:20:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Business billing, Plover Arc Logistics

Your email of 09:50 UTC says CN-049 credits GBP 18.00 against INV-049, leaving GBP 18.00 due. The Mossline Press account statement generated at 10:00 UTC shows INV-049 at GBP 36.00 outstanding with no credits applied. Is CN-049 posted against INV-049, and which balance is current? We are keeping both records on file.

<a id="event-007"></a>
## 2026-03-22 10:55:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Business billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

CN-049 is now posted against INV-049; the 10:00 UTC statement was generated before posting. The current statement shows GBP 36.00 less the GBP 18.00 credit, GBP 18.00 due. No payment has been received and no money has been refunded. A credit note is not cash.
