# Three independent training cases with extra context difficulty

These three English synthetic cases extend the reviewed previews as separate records. Each has one additional complication and a new ID. Existing public cases, negative branches and previously added context variants are unchanged. The proposed wider distribution from this preview has not been generated.

| Case ID | Parent | Added complication | Decision at cutoff |
|---|---|---|---|
| 001-A1-NOISE | 001 | Conversational filler and informal spelling | Ask the recipient to choose from dispatch's two windows. |
| 012-N2-A1-MISSING | 012-N2 | Alternative delivery windows withheld | Ask dispatch for current replacement options. |
| 002-N4-A1-LONG | 002-N4 | Twelve historical intake records, eighteen messages total | Wait for the already-requested saved-address readback. |

Cases end at a decision cutoff. They do not inherit later parent outcomes or claim completed coordination. The long case renumbers its events to 001–018; `index.json` maps original and added events to the new IDs.

## Training files

- `agent_inputs/<id>.json`: evidence-only model input in the existing `proofkey-step-input-v1` format.
- `targets/<id>.json`: structured supervision, stored separately from model input.
- `training.jsonl`: three `input` / `target` pairs, one per independent case.
- `manifest.json`: input and target hashes and source family identities.
- `sources/<id>/index.md` and `history.md`: narrative source records.
- `../../case-state-widget/annot/<id>.json`: editable compact annotations.
- `../../case-state-widget/cases/<id>.json`: compiled viewer records.

Only send `input` to a model. Keep each public source family and all descendants in the same train/evaluation split. Targets are assistant-authored drafts for review, not independently adjudicated labels.

## Rebuild and validate

From the repository root:

```sh
python3 case-state-widget/pipeline/compile.py 001-A1-NOISE 012-N2-A1-MISSING 002-N4-A1-LONG
python3 case-state-widget/pipeline/export_context_training.py
python3 case-state-widget/pipeline/test_context_training.py
node case-state-widget/pipeline/validate.mjs case-state-widget/cases/*-A1-*.json
```

Edit narrative sources and compact annotations, then rebuild the viewer records and export the training files. Update targets when the available evidence changes the next action. No model calls, training run or operational messages are made by the exporter.
