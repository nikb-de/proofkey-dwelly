# 008 — History

All timestamps include offsets. Records labelled excerpts are reproduced inline.

## E01 | 2026-10-14T08:00:00+01:00 | booking record

From: Vellora dispatch register → To: Vellora escalation desk
Known at desk: `2026-10-14T08:00:00+01:00`

Riven Shaw is returning order VEL-008-26 to Briar Cabinet merchant, return RMA-808. Merchant returns channel on order: returns@briarcabinet.example.

## E02 | 2026-10-14T08:10:00+01:00 | procedure excerpt

From: Vellora procedure desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:10:00+01:00`

Inline merchant terms RT8: receipt-dependent refund assessment starts after warehouse receipt. Tracking glossary: return_created = label allocated; accepted = carrier possession scan; received = merchant intake scan.

## E03 | 2026-10-14T08:20:00+01:00 | system excerpt

From: Vellora operations → To: Vellora escalation desk
Known at desk: `2026-10-14T08:20:00+01:00`

Return portal excerpt: RMA-808 return_created at 2026-10-14T07:50:00+01:00; accepted=null; received=null. File supplied: [return-label.pdf](attachments/return-label.pdf).

## E04 | 2026-10-14T08:30:00+01:00 | call note

From: Riven Shaw → To: Vellora escalation desk
Known at desk: `2026-10-14T08:30:00+01:00`

Riven Shaw: I printed the label and the portal says return created. Please mark it received and refund GBP 64.

## E05 | 2026-10-14T08:40:00+01:00 | internal handoff

From: Vellora service coordinator → To: Vellora escalation desk
Known at desk: `2026-10-14T08:40:00+01:00`

Merchant desk at 08:40: no intake record for RMA-808. Carrier check channel returns-trace@vellora.example; no drop-off receipt supplied in this packet.

## E06 | 2026-10-14T08:50:00+01:00 | dispatch message

From: Riven Shaw → To: Vellora escalation desk
Known at desk: `2026-10-14T08:50:00+01:00`

Can you approve the receipt-dependent refund now based on my return label?

