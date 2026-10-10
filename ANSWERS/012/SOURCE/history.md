# 012 — History

All timestamps include offsets. Records labelled excerpts are reproduced inline.

## E01 | 2026-10-14T08:00:00+01:00 | booking record

From: Vellora dispatch register → To: Vellora escalation desk
Known at desk: `2026-10-14T08:00:00+01:00`

VEL-012-26: two cartons collected for Petalworks. Customer contact: Selin Brook. Invoice INV-012 for GBP 48 is unpaid. Verified billing desk: billing@vellora.example.

## E02 | 2026-10-14T08:10:00+01:00 | procedure excerpt

From: Vellora procedure desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:10:00+01:00`

Inline agreed tariff DW12: each carton is billed at greater of actual kg and dimensional kg (length x width x height in cm / 5,000). Round each resulting billable weight upward to a whole kg. Rate GBP 2/kg; no additional fees.

## E03 | 2026-10-14T08:20:00+01:00 | system excerpt

From: Vellora operations → To: Vellora escalation desk
Known at desk: `2026-10-14T08:20:00+01:00`

Measurement excerpt: carton C12-A 50 x 40 x 30 cm, 5 kg; carton C12-B 50 x 40 x 30 cm, 5 kg. File supplied: [service-invoice.pdf](attachments/service-invoice.pdf).

## E04 | 2026-10-14T08:30:00+01:00 | email

From: Customer → To: Vellora escalation desk
Known at desk: `2026-10-14T08:30:00+01:00`

Selin Brook: Actual weight is only 10 kg total. At GBP 2/kg this should cost GBP 20, not GBP 48; please credit the difference.

## E05 | 2026-10-14T08:40:00+01:00 | internal handoff

From: Vellora account desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:40:00+01:00`

Booking audit: both cartons belong to VEL-012-26. DW12 was accepted at booking; invoice remains unpaid and no adjustment is authorised. Billing may review measurement disputes.

## E06 | 2026-10-14T08:50:00+01:00 | email

From: Customer → To: Vellora escalation desk
Known at desk: `2026-10-14T08:50:00+01:00`

Can you correct the charge now based on the total actual weight?

