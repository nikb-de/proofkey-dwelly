# Case 050 history — Customer requests reimbursement of a guaranteed-delivery surcharge after confirmed delay

All identities, records and communications are fictional. Total events: 4.

<a id="event-001"></a>
## 2026-03-23 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Service guarantees, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-050 booking terms excerpt: guaranteed by 2026-03-23 08:00 UTC; surcharge GBP 7.50. If carrier-caused delay is confirmed, the surcharge may be credited after billing review. Route record: carrier sorting delay, actual recipient handover 2026-03-23 08:40 UTC. No exclusion is recorded.

<a id="event-002"></a>
## 2026-03-23 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Nella Voss, customer
- **To:** Iona Quill, Rivet Delivery Desk

My parcel arrived at 08:40, later than the guaranteed 08:00 deadline. Please submit a request for the GBP 7.50 service surcharge under these booking terms.

<a id="event-003"></a>
## 2026-03-23 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Guarantee billing, Plover Arc Logistics

Please review a service-guarantee credit request for DL-050: guaranteed 2026-03-23 08:00 UTC, actual handover 08:40, confirmed carrier sorting delay, surcharge GBP 7.50. Customer seeks only the surcharge under this booking’s terms.

<a id="event-004"></a>
## 2026-03-23 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Guarantee billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Approved after review: credit GC-050 for GBP 7.50 against DL-050’s service surcharge. The credit is posted to the fictional booking account. This is not a cash transfer and does not compensate any other loss.

