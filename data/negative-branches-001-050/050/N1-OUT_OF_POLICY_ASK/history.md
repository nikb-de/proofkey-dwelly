# Case 050-N1 history — Customer requests reimbursement of a guaranteed-delivery surcharge after confirmed delay (Customer adds losses, doubles surcharge)

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
## 2026-03-23 09:35:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Nella Voss, customer
- **To:** Iona Quill, Rivet Delivery Desk

I missed a client call because of this. Please add GBP 60.00 for my lost time to the request, and double the surcharge to GBP 15.00 since the delay was 40 minutes.

<a id="event-005"></a>
## 2026-03-23 09:50:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Nella Voss, customer

The DL-050 booking terms cover only the GBP 7.50 guaranteed-delivery surcharge. The 40-minute delay does not change that amount, and lost time is not covered. Your request to guarantee billing stays at GBP 7.50, and its review is still pending.

<a id="event-006"></a>
## 2026-03-23 10:20:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Nella Voss, customer
- **To:** Iona Quill, Rivet Delivery Desk

Understood. Keep the request at GBP 7.50 for the surcharge only. I am not claiming for the missed call through this request. I note that billing has not decided yet.
