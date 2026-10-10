# Case 035-N6 history — Merchant has received the return but the refund review has not started (Phone call opens a second review)

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
## 2026-03-08 10:20:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Email
- **From:** Refunds team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

A second review, RF-035-B, was opened at 10:05 from the customer's phone call, also citing WH-035. TG-035 now has two open reviews. Please confirm how to proceed.

<a id="event-006"></a>
## 2026-03-08 10:35:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Refunds team, Tallowmere Goods

RF-035-B duplicates RF-035: both concern TG-035 and the same receipt, WH-035. Please link RF-035-B to RF-035, close it, and keep RF-035 as the single review. Please confirm once done.

<a id="event-007"></a>
## 2026-03-08 11:00:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Refunds team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

RF-035-B is closed and linked to RF-035. RF-035 is the single review for TG-035 with WH-035, and its update remains due by 2026-03-10, 16:00 UTC. Nothing is approved or paid.
