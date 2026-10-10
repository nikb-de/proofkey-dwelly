# Case 035-N2 history — Merchant has received the return but the refund review has not started (Refunds record shows return not received)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 035; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-08 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Warehouse receiving, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Inline receipt WH-035: RT-035 for TG-035 physically received at 08:10 UTC today. We can confirm receipt, but our receiving role does not approve refunds.

<a id="event-002"></a>
## 2026-03-08 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Melli Orven, customer
- **To:** Iona Quill, Rivet Delivery Desk

The warehouse says it has my return, but my order has no refund review. Please pass the receipt to the team that handles it.

<a id="event-003"></a>
## 2026-03-08 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Refunds team, Tallowmere Goods

Please register the refund review for TG-035 / RT-035 using warehouse receipt WH-035. Notify us of the case reference and next update date; receipt alone is not refund approval.

<a id="event-004"></a>
## 2026-03-08 09:55:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Refunds team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Our order record for TG-035 shows RT-035 as not received and holds no WH-035. We register reviews only against a receipt posted to the order. We have not opened a review.

<a id="event-005"></a>
## 2026-03-08 10:10:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Warehouse receiving, Tallowmere Goods

Two records disagree for RT-035. Your inline receipt WH-035 shows it physically received at 08:10 UTC today. The Refunds team's order record for TG-035 shows RT-035 not received and holds no WH-035, so it cannot register a review. Please confirm whether WH-035 is posted to the TG-035 order record.

<a id="event-006"></a>
## 2026-03-08 10:50:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Warehouse receiving, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

WH-035 was recorded at the returns bay at 08:10 but had not posted to the TG-035 order record. It posted at 10:40, so the Refunds team can now register against it. Posting confirms receipt only; it is not a review or refund approval.
