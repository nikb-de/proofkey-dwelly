# 030 — History

All timestamps include offsets. Records labelled excerpts are reproduced inline.

## E01 | 2026-10-14T08:00:00+01:00 | booking record

From: Vellora dispatch register → To: Vellora escalation desk
Known at desk: `2026-10-14T08:00:00+01:00`

VEL-030-26 is a two-parcel order for Kael Rook. Order mapping: parcel A = VR-030-A, parcel B = VR-030-B. Stored trace channel: trace@vellora.example; merchant care care@irisretail.example.

## E02 | 2026-10-14T08:10:00+01:00 | procedure excerpt

From: Vellora procedure desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:10:00+01:00`

Inline order completion guide OC30: completion requires matched handover evidence for each parcel. Broker release is a processing status, not a physical delivery event. Merchant care handles any order-level remedy.

## E03 | 2026-10-14T08:20:00+01:00 | system excerpt

From: Vellora operations → To: Vellora escalation desk
Known at desk: `2026-10-14T08:20:00+01:00`

Parcel A file: [delivery-record.pdf](attachments/delivery-record.pdf). Parcel B excerpt: broker_release at 2026-10-14T07:40:00+01:00; last physical scan broker holding depot at 07:10:00+01:00; delivery_handover=null.

## E04 | 2026-10-14T08:30:00+01:00 | email

From: Kael Rook → To: Vellora escalation desk
Known at desk: `2026-10-14T08:30:00+01:00`

Kael Rook: I have one box and the delivery record. The other parcel says released, so can you close the whole order as delivered?

## E05 | 2026-10-14T08:40:00+01:00 | follow-up message

From: Kael Rook → To: Vellora escalation desk
Known at desk: `2026-10-14T08:40:00+01:00`

Kael Rook: The box I received is labelled VR-030-A. I cannot find a second package at the receiving desk.

## E06 | 2026-10-14T08:50:00+01:00 | internal handoff

From: Vellora reconciliation desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:50:00+01:00`

Order desk at 08:40: VR-030-A receiver mark KR-30 is matched; no last-mile receipt for VR-030-B is in the record. Each parcel is a separate package under VEL-030-26.

## E07 | 2026-10-14T09:00:00+01:00 | email

From: Kael Rook → To: Vellora escalation desk
Known at desk: `2026-10-14T09:00:00+01:00`

Please confirm both parcels have arrived and close my order now.

