# 022 — History

All timestamps include offsets. Records labelled excerpts are reproduced inline.

## E01 | 2026-10-14T08:00:00+01:00 | booking record

From: Vellora dispatch register → To: Vellora escalation desk
Known at desk: `2026-10-14T08:00:00+01:00`

Customer Veda Rell has current return RMA-222 for order VEL-022-26, item Reedlamp R2. Merchant return channel: returns@petalretail.example.

## E02 | 2026-10-14T08:10:00+01:00 | procedure excerpt

From: Vellora procedure desk → To: Vellora escalation desk
Known at desk: `2026-10-14T08:10:00+01:00`

Inline return-token guide QR22: a token must map to the approved return and item. Readability only establishes token decoding; merchant returns issues any replacement token. Tokens in this exercise are inert identifiers, not URLs.

## E03 | 2026-10-14T08:20:00+01:00 | system excerpt

From: Vellora operations → To: Vellora escalation desk
Known at desk: `2026-10-14T08:20:00+01:00`

Customer file: [return-code.png](attachments/return-code.png). Inline token register: RET-OLD-221 -> RMA-221 / item Fernclock F1 / earlier order VEL-021X-26. RMA-222 / Reedlamp R2 token field pending issue.

## E04 | 2026-10-14T08:30:00+01:00 | webchat

From: Veda Rell → To: Vellora escalation desk
Known at desk: `2026-10-14T08:30:00+01:00`

Veda Rell: This old QR still scans. I want to use it for the Reedlamp because I cannot find the new code.

## E05 | 2026-10-14T08:40:00+01:00 | follow-up message

From: Veda Rell → To: Vellora escalation desk
Known at desk: `2026-10-14T08:40:00+01:00`

Veda Rell: The Fernclock was a separate return. I am returning only the Reedlamp on RMA-222 this time.

## E06 | 2026-10-14T08:50:00+01:00 | internal handoff

From: Vellora carrier liaison → To: Vellora escalation desk
Known at desk: `2026-10-14T08:50:00+01:00`

Merchant portal excerpt at 08:40: RMA-222 approved for Reedlamp R2; no mapping to RET-OLD-221. returns@petalretail.example is the stored issuer channel.

## E07 | 2026-10-14T09:00:00+01:00 | webchat

From: Veda Rell → To: Vellora escalation desk
Known at desk: `2026-10-14T09:00:00+01:00`

Please confirm I can drop off the current item with this QR.

