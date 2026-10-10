# 006 — History

All timestamps include offsets. Records labelled excerpts are reproduced inline.

## E01 | 2026-10-14T08:00:00+01:00 | booking record

From: Vellora dispatch register → To: Vellora escalation desk
Known at desk: `2026-10-14T08:00:00+01:00`

VEL-006-26, carrier reference VR-40681, due at 14 Laurel Row, Reedmere on 2026-10-14. Customer Sera Ives disputes receipt. Verified trace channel: trace@vellora.example.

## E02 | 2026-10-14T08:10:00+01:00 | procedure excerpt

From: Vellora procedure desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:10:00+01:00`

Inline trace procedure T6: match the carrier reference and service date before closing a delivery dispute. A disputed or unmatched record may be referred for trace; documentary differences alone do not establish forgery.

## E03 | 2026-10-14T08:20:00+01:00 | system excerpt

From: Vellora operations → To: Vellora escalation desk
Known at desk: `2026-10-14T08:20:00+01:00`

Notification packet includes [delivery-record.pdf](attachments/delivery-record.pdf) and [tracking-screen.png](attachments/tracking-screen.png). The live booking reference is VR-40681.

## E04 | 2026-10-14T08:30:00+01:00 | email

From: Sera Ives → To: Vellora escalation desk
Known at desk: `2026-10-14T08:30:00+01:00`

Sera Ives: I was home and received nothing. Your notification says delivered; the record in the packet looks familiar but I cannot identify the handover.

## E05 | 2026-10-14T08:40:00+01:00 | follow-up message

From: Sera Ives → To: Vellora escalation desk
Known at desk: `2026-10-14T08:40:00+01:00`

Sera Ives: My notification account is sera@ives.example. I was expecting the parcel at 14 Laurel Row today and would like the supplied record reviewed.

## E06 | 2026-10-14T08:50:00+01:00 | internal handoff

From: Vellora reconciliation desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:50:00+01:00`

Trace intake: dispute TR-006 is open for VR-40681, review pending. The notification service supplied the two files at 08:20; no investigation finding has been entered.

## E07 | 2026-10-14T09:00:00+01:00 | email

From: Sera Ives → To: Vellora escalation desk
Known at desk: `2026-10-14T09:00:00+01:00`

Can you settle this delivery dispute from the record and tell me where my parcel is?

