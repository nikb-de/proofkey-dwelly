# Case 035-N4 history — Merchant has received the return but the refund review has not started (Customer asks to confirm amount and approval)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 035; events 005–007 are this branch.

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
## 2026-03-08 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Refunds team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Review RF-035 is registered with WH-035. We will update the order thread by 2026-03-10, 16:00 UTC. Eligibility, amount and payment remain undecided.

<a id="event-005"></a>
## 2026-03-08 10:10:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Melli Orven, customer
- **To:** Iona Quill, Rivet Delivery Desk

I can see RF-035 now. My bank needs written confirmation. Please confirm the refund of GBP 89.00 is approved and will be paid this week.

<a id="event-006"></a>
## 2026-03-08 10:25:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Melli Orven, customer

We cannot confirm an approval, an amount or a payment date. Review RF-035 is registered with warehouse receipt WH-035, but the Tallowmere Goods Refunds team has not decided eligibility, amount or payment. Its next update is due by 2026-03-10, 16:00 UTC. Only that team can give your bank a decision.

<a id="event-007"></a>
## 2026-03-08 11:00:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Melli Orven, customer
- **To:** Iona Quill, Rivet Delivery Desk

Understood. I will tell my bank that review RF-035 is registered and the next update is due by 2026-03-10, 16:00 UTC. I accept that approval, amount and payment are not decided yet.
