# Context augmentations 001–050

Forty augmented variants of the public Delivery & Logistics cases 001–050. Each selected case receives exactly one added complication from the Reality Test list: sloppy correspondence, a missing prerequisite detail, a long history with irrelevant events, an absent referenced attachment, contradicting sources, an unknown earlier outcome, an ambiguous request, an unusual exception, or a decision that needs a human. The remaining ten public cases stay as clean controls.

These variants are training material. The correct next action stays principled even when the input is messy: ask for exactly the missing item from the right party, verify before repeating, ignore noise, do not act on unrelated threads. Sources and expected decisions follow the reviewed public set; nothing here is ground truth.

## Marking

- `index.csv` (this folder): one row per variant with source case, complication, expected decision and status.
- Each variant card carries a `Derived from:` line naming the source case and the complication tag.

Complication tags: `A1-SLOPPY_NOISE`, `A2-MISSING_DETAIL`, `A3-LONG_HISTORY`, `A4-MISSING_ATTACHMENT`, `A5-CONFLICT`, `A6-UNKNOWN_OUTCOME`, `A7-AMBIGUOUS_TASK`, `A8-UNUSUAL_EXCEPTION`, `A9-NEEDS_HUMAN`.

## Status

- In the viewer catalog: `001/A1` (noise), `012/A2` (missing detail), `019/A3` (long history) — annotated, compiled and validated (`case-state-widget/cases/<id>.json`).
- Planned: the remaining 37 variants, see `index.csv` (`status=planned`). Expected decisions are preliminary and are fixed per variant on authoring.
- Clean controls (no added complication): cases 002, 003, 005, 022, 023, 028, 032, 034, 044, 046.

## Format

`<source>/<tag>/index.md` + `history.md`, same skeleton and style as the public corpus and the negative branches (British English, UTC, fictional parties). A variant keeps its source case's world, shipment and policy; only the documented complication is added.
