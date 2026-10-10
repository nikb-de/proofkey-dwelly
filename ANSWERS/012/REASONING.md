# REASONING — 012

The submitted model contract has no rationale field. These are only its recorded evidence references and uncertainty; no reasoning is reconstructed.

```json
{
  "evidence_event_ids": [
    "E02",
    "E03",
    "E04",
    "E05",
    "E06"
  ],
  "uncertainty": [
    "No reply to the customer is visible, so this analysis does not establish that the customer has been told.",
    "The account desk says no adjustment is authorised and that billing may review measurement disputes. If the customer disputes the carton measurements, that would need a billing review.",
    "The billing desk is not a visible actor, so it cannot be a target here.",
    "The invoice PDF is an extracted derivative. It matches the GBP 48 charge but does not itemise carton weights."
  ]
}
```

## E02 — [source](SOURCE/history.md)

> From: Vellora procedure desk → To: Vellora escalation desk
> Known at desk: `2026-10-14T08:10:00+01:00`
> 
> Inline agreed tariff DW12: each carton is billed at greater of actual kg and dimensional kg (length x width x height in cm / 5,000). Round each resulting billable weight upward to a whole kg. Rate GBP 2/kg; no additional fees.

## E03 — [source](SOURCE/history.md)

> From: Vellora operations → To: Vellora escalation desk
> Known at desk: `2026-10-14T08:20:00+01:00`
> 
> Measurement excerpt: carton C12-A 50 x 40 x 30 cm, 5 kg; carton C12-B 50 x 40 x 30 cm, 5 kg. File supplied: [service-invoice.pdf](attachments/service-invoice.pdf).

## E04 — [source](SOURCE/history.md)

> From: Customer → To: Vellora escalation desk
> Known at desk: `2026-10-14T08:30:00+01:00`
> 
> Selin Brook: Actual weight is only 10 kg total. At GBP 2/kg this should cost GBP 20, not GBP 48; please credit the difference.

## E05 — [source](SOURCE/history.md)

> From: Vellora account desk → To: Vellora escalation desk
> Known at desk: `2026-10-14T08:40:00+01:00`
> 
> Booking audit: both cartons belong to VEL-012-26. DW12 was accepted at booking; invoice remains unpaid and no adjustment is authorised. Billing may review measurement disputes.

## E06 — [source](SOURCE/history.md)

> From: Customer → To: Vellora escalation desk
> Known at desk: `2026-10-14T08:50:00+01:00`
> 
> Can you correct the charge now based on the total actual weight?
