# 009 — History

All timestamps include offsets. Records labelled excerpts are reproduced inline.

## E01 | 2026-10-14T08:00:00+01:00 | account intake

From: Vellora dispatch register → To: Vellora escalation desk
Known at desk: `2026-10-14T08:00:00+01:00`

VEL-009-26 is travelling from Vellora to the fictional partner Fennel Mile for last-mile delivery in Silverfen. Customer: Liora Tern. Verified partner desk: partner@vellora.example.

## E02 | 2026-10-14T08:10:00+01:00 | procedure excerpt

From: Vellora procedure desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:10:00+01:00`

Inline event dictionary H9: manifest_transmitted records electronic shipment data; physical_handover records depot loading receipt signed by the receiving carrier. partner_received records the partner intake scan.

## E03 | 2026-10-14T08:20:00+01:00 | system excerpt

From: Vellora operations → To: Vellora escalation desk
Known at desk: `2026-10-14T08:20:00+01:00`

Event excerpt: VEL-009-26 physical_scan at Vellora Fern depot 2026-10-14T07:15:00+01:00; manifest_transmitted to Fennel Mile at 07:55:00+01:00; physical_handover=null; partner_received=null. Inline handoff: Partner integration desk: Fennel Mile acknowledged the electronic manifest. The next scheduled vehicle loading is under review, with no receiving signature in the record.

## E04 | 2026-10-14T08:30:00+01:00 | email

From: Liora Tern → To: Vellora escalation desk
Known at desk: `2026-10-14T08:30:00+01:00`

Liora Tern: The partner entry means Fennel Mile has it now. Tell me which local van is bringing it.

## E05 | 2026-10-14T08:40:00+01:00 | email

From: Liora Tern → To: Vellora escalation desk
Known at desk: `2026-10-14T08:40:00+01:00`

Please confirm local-carrier custody and a delivery run from this handover entry.

