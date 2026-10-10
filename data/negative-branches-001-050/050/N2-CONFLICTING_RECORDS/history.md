# Case 050-N2 history — Customer requests reimbursement of a guaranteed-delivery surcharge after confirmed delay (Billing scan contradicts route record)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 050; events 004–006 are this branch.

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
## 2026-03-23 09:45:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Guarantee billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Our handover scan for DL-050 shows 07:55 UTC on 2026-03-23, inside the guarantee. On that basis the request is declined. No credit will be posted.

<a id="event-005"></a>
## 2026-03-23 10:00:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Guarantee billing, Plover Arc Logistics

Your handover scan for DL-050 shows 07:55 UTC on 2026-03-23. The service guarantees route record shows a carrier sorting delay and actual recipient handover at 08:40 UTC. Please check the two records against each other and tell us which one your decision relies on.

<a id="event-006"></a>
## 2026-03-23 10:45:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Guarantee billing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The 07:55 UTC scan was the arrival scan at the delivery depot, not the recipient handover. The route record's 08:40 UTC handover stands. The decline is withdrawn and credit GC-050 for GBP 7.50 is approved against the surcharge, posted to the booking account. This is not a cash transfer.
