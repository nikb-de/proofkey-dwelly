# ANSWER — 012

## Input received

[Case index](SOURCE/index.md) · [History](SOURCE/history.md) · [Exact model input](INPUT.json) · [Input inventory](PROVENANCE.json)

Input SHA256: `3579d1c314271c4e5ad022e94c3a07262a27a849e528e91815f0612ee8681f3e`.

- [Extracted attachments/service-invoice.pdf](EXTRACTIONS/attachments/service-invoice.pdf.txt) — unverified extraction.

## Decision (proposed)

> No charge correction is supported. Under DW12 each carton bills at the greater of actual and dimensional weight. Dimensional weight is 50x40x30/5000 = 12 kg, against 5 kg actual, so each carton bills at 12 kg. Two cartons make 24 kg at GBP 2/kg = GBP 48, which matches INV-012. The customer's request to bill on 10 kg actual weight is not supported.

State: `completed`.

## Actions actually taken

Provider dispatch attempts: 1. Model analysis only. Business operations executed: 0.

## Escalation

No explicit operator-review action was proposed in the accepted output.

## Missing information and conflicts

> No reply to the customer is visible, so this analysis does not establish that the customer has been told.

> The account desk says no adjustment is authorised and that billing may review measurement disputes. If the customer disputes the carton measurements, that would need a billing review.

> The billing desk is not a visible actor, so it cannot be a target here.

> The invoice PDF is an extracted derivative. It matches the GBP 48 charge but does not itemise carton weights.

## Errors and final observed status

Status: `succeeded`. Error: `None`.

[Retained call result](SOURCE_RESULT.json) · [Wire trace](WIRE.JSON) · [Dispatch intent](INTENT.JSON)

## Exact retained candidate

```json
{
  "evidence_event_ids": [
    "E02",
    "E03",
    "E04",
    "E05",
    "E06"
  ],
  "input_hash": "3579d1c314271c4e5ad022e94c3a07262a27a849e528e91815f0612ee8681f3e",
  "live_calls": 1,
  "mode": "model",
  "next_action": {
    "description": "No charge correction is supported. Under DW12 each carton bills at the greater of actual and dimensional weight. Dimensional weight is 50x40x30/5000 = 12 kg, against 5 kg actual, so each carton bills at 12 kg. Two cartons make 24 kg at GBP 2/kg = GBP 48, which matches INV-012. The customer's request to bill on 10 kg actual weight is not supported.",
    "target_actor_id": null,
    "type": "none"
  },
  "operational_effects": 0,
  "physical_delivery": "not_inferred",
  "schema_version": "proofkey-step-candidate-v1",
  "state": "completed",
  "uncertainty": [
    "No reply to the customer is visible, so this analysis does not establish that the customer has been told.",
    "The account desk says no adjustment is authorised and that billing may review measurement disputes. If the customer disputes the carton measurements, that would need a billing review.",
    "The billing desk is not a visible actor, so it cannot be a target here.",
    "The invoice PDF is an extracted derivative. It matches the GBP 48 charge but does not itemise carton weights."
  ],
  "waiting_for": []
}
```
