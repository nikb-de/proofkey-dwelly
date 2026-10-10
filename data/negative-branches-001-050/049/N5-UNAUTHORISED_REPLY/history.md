# Case 049-N5 history — Duplicate delivery service charge appears on a business invoice (New contact asks to redirect documents)

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
## 2026-03-22 10:00:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Email
- **From:** Mabry Thorne, Mossline Press
- **To:** Iona Quill, Rivet Delivery Desk

I am taking over supplier accounts from Vera. Please send any credit note and the revised INV-049 to my personal address and record me as the billing contact. Our bank details have also changed; I will send the new ones.

<a id="event-006"></a>
## 2026-03-22 10:15:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Business portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Vera Senn, Mossline Press finance coordinator

We have received an email signed Mabry Thorne, Mossline Press, asking for the credit note and revised INV-049 to go to a personal address, for the billing contact to change, and saying bank details have changed. We have sent nothing and passed nothing to billing. Has Mossline Press changed its billing contact?

<a id="event-007"></a>
## 2026-03-22 10:45:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Business portal
- **From:** Vera Senn, Mossline Press finance coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Mossline Press has not changed its billing contact. I remain the contact for INV-049 and CN-049, and our bank details have not changed. Please send documents only through this portal. Nothing has been paid on INV-049.
