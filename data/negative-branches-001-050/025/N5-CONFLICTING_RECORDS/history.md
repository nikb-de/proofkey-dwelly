# Case 025-N5 history — Carrier confirms a parcel is lost after investigation (Lost parcel scanned at depot)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 025; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-02-26 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Loss investigations, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Final trace record INV-025: DL-025 could not be located after the completed depot and route search; carrier status is confirmed lost. This finding does not itself create a merchant replacement order.

<a id="event-002"></a>
## 2026-02-26 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Aven Korrin, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I still need the kettle from TG-025. I choose a like-for-like replacement rather than a refund. Please ask the merchant to approve it.

<a id="event-003"></a>
## 2026-02-26 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Replacement authorisations, Tallowmere Goods

Please approve the customer-selected kettle replacement for TG-025. Carrier INV-025 confirms DL-025 lost; Aven’s choice is recorded in the verified order thread.

<a id="event-004"></a>
## 2026-02-26 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Replacement authorisations, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

Replacement approved at no additional charge. Order TG-025-R has been created for the same kettle. Shipment has not yet been booked.

<a id="event-005"></a>
## 2026-02-26 11:20:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Email
- **From:** Tracking support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Automated alert for DL-025: an inbound depot scan was recorded at 11:02 UTC today. INV-025 still shows status confirmed lost. We have not checked the scan against the parcel.

<a id="event-006"></a>
## 2026-02-26 11:35:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Loss investigations, Plover Arc Logistics

DL-025: Tracking support reports an inbound depot scan at 11:02 UTC today, while INV-025 still shows confirmed lost. The scan has not been checked against the parcel. Which status stands, and is DL-025 physically in carrier custody? Replacement order TG-025-R already exists, so we are telling Tallowmere Goods that the loss record is under reconciliation.

<a id="event-007"></a>
## 2026-02-26 12:30:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Loss investigations, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-025 is physically at the depot. Staff matched the parcel to the 11:02 UTC scan at 12:10 UTC, and INV-025 now shows located, not lost. A located parcel is not a delivered one. Whether the original or TG-025-R goes to the customer is for the customer and the merchant.
