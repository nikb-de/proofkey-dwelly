# Case 100 history — Merchant email and carrier booking show different delivery dates

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-05-12 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Recipient services, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-100 is booked on route. The Cobblereed Outfitters dispatch email to the recipient states delivery on 2026-05-13; the carrier tracking page shows 2026-05-14, 08:00–12:00 UTC. The tracking page is a copy that can lag; only the booking record held by Dispatch is authoritative, and merchant emails are estimates.

<a id="event-002"></a>
## 2026-05-12 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Imra Yostel, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Cobblereed's email says my boots arrive on 13 May, but your tracking says 14 May. Which day should I stay home?

<a id="event-003"></a>
## 2026-05-12 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Dispatch, Plover Arc Logistics

DL-100 has two dates on file: the merchant's email says 2026-05-13; the tracking page shows 2026-05-14, 08:00–12:00 UTC. Please confirm from the booking record which date and slot DL-100 is booked for. Neither source is overwritten, and the recipient has been given neither date as fact.

<a id="event-004"></a>
## 2026-05-12 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Booking record for DL-100: 2026-05-14, 08:00–12:00 UTC, unchanged since it was booked on 2026-05-10. No booking exists for 2026-05-13. This confirms the booked date, not a completed delivery.

<a id="event-005"></a>
## 2026-05-12 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Imra Yostel, recipient

Dispatch confirms from its booking record that DL-100 is booked for 2026-05-14, 08:00–12:00 UTC. The 2026-05-13 date in the merchant's email is not a carrier booking. Delivery is still pending.
