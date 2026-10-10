# Team training and evaluation handoff v1

Use this package to author reviewable logistics-agent decision examples. Its main format is the canonical `proofkey-decision-input-v1` / `proofkey-decision-label-v1` / `proofkey-episode-v1` contract, originating in the repository's `contracts/v1/`. The required schemas are included here: [input](schemas/decision-input.schema.json), [label](schemas/decision-label.schema.json) and [episode](schemas/episode.schema.json). Evaluator criteria and dataset manifests are separate sidecars; they add no backend fields.

**Status:** synthetic development seeds; assistant-authored, unreviewed, not gold labels. No training, model evaluation, semantic grader, live integration or performance measurement is delivered by this package. Canonical snapshot compatibility does not mean the current model runner can import it: that adapter remains necessary.

## Give colleagues this directory

1. Read [the Russian team brief](TEAM_BRIEF_RU.md) and [format](FORMAT.md).
2. Use [the generator prompt](GENERATOR_PROMPT.md) with authorised source material and the schemas in `schemas/`.
3. Review each case with [the annotation checklist](ANNOTATION_CHECKLIST.md); preserve uncertainty and human review status.
4. Follow [training/evaluation separation](TRAINING_EVAL.md) and the [rubric](RUBRIC.md).
5. Run the quickstart below from this package's extracted directory.

```bash
python3 -m pip install -r requirements.txt
python3 scripts/validate.py .
python3 -m unittest discover -s tests -v
```

The requested next delivery is **10–20 independent evaluation cases plus 10–20 authorised, redacted real/live-workflow snapshots**. A live-workflow snapshot means an offline capture of already available evidence, not a request to call providers, contact participants or operate business systems. Record whether these collections overlap; do not count repeated decisions or branches as independent cases.

## Layout and access

- `examples/inputs/`: canonical model-visible inputs.
- `examples/labels/`: canonical evaluator-only reference labels.
- `examples/episodes/`: canonical evaluator-only episode membership.
- `examples/criteria/`: evaluator-only semantic criteria.
- `manifest.jsonl`: inventory, family splits, provenance classification and exact-byte checksums.

The model receives only the selected input bytes. Directory names are not access controls: keep labels, criteria, episodes, manifest, this documentation and other examples outside the evaluated agent's accessible context. Preserve originals and create new versions when reviewing or correcting examples.

Validation checks the implemented structural and cross-record rules; it does not establish source truth, permission, policy correctness, semantic quality or human calibration. These seeds are development material only. `scripts/build_examples.py` regenerates the generated seeds; do not use it to overwrite colleagues' authored records. The earlier `docs/dataset-drafts/2026-10-10-decision-episodes` kit remains a separate legacy draft and is not the main interchange format.
