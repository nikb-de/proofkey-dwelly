# Case 035-N5 history — Merchant has received the return but the refund review has not started (Customer wants the item back instead)

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
## 2026-03-08 09:45:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Melli Orven, customer
- **To:** Iona Quill, Rivet Delivery Desk

I have changed my mind. I would rather have the item back than a refund. Please stop the refund review for TG-035.

<a id="event-005"></a>
## 2026-03-08 10:00:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Refunds team, Tallowmere Goods

At 09:45 the customer asked us to stop our 09:25 refund review request for TG-035 and would now prefer the item back. Please register nothing further on our request and tell us whether a review was already opened. Returning the item would be a separate request for Tallowmere to decide.

<a id="event-006"></a>
## 2026-03-08 10:30:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Refunds team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Stop recorded against your 09:25 request. No review had been opened for TG-035, and none will be registered on it. The item remains in our returns stock under WH-035. Sending it back to the customer needs a separate merchant decision; nothing is decided on that.
