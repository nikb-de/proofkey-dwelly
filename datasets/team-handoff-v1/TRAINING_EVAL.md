# Training and evaluation use

Training changes or conditions the system using reference responses. Evaluation generates a fresh candidate and compares it with private expectations. Keep these uses separate even when they share the canonical input format.

## Before tuning

Group all related cases, steps, translations and counterfactuals into families. Assign families to train/development/test before tuning. Keep every family in one split. These seed examples are entirely development data, not a reserved final test set.

Collect 10–20 independent evaluation cases and 10–20 authorised redacted snapshots from real workflows. Record collection overlap and true independent-family counts. Offline captures do not authorize fresh provider calls or business operations. Review permissions, retained identifying details, source cutoff and policy provenance.

## Training eligibility

Only human-reviewed, accepted annotations may become training demonstrations or export candidates. `assistant_authored_draft`, `human_authored_draft` and `rejected` records are ineligible. A passing structural validator does not promote them. Review the label and semantic criteria together, with real reviewer identity and timestamp.

A future exporter must separately define and validate the model's output target. Canonical `decision-label` is evaluator metadata, not a ready-to-send assistant message. No training exporter, provider-specific messages or trained weights are included. Never include criteria, all acceptable alternatives, forbidden behavior lists, future events or evaluation metadata in the model input. Few-shot demonstrations must come from eligible training families only.

## Evaluation protocol

Provide only one selected input's bytes to the system under test. Deny repository access to private labels, criteria, episodes, manifest, documentation and future snapshots. Capture unmodified candidate bytes, parse failures, requested and observed model/provider identities, prompt/system versions, input hash, timestamp and any actually measured latency/cost. Preserve failed and missing attempts; do not replace them with the reference.

Use exact assertions for schema, source binding and prohibited operational effects, and qualified semantic review for content. Criteria sidecars are a proposed review interface, not an implemented grader. The canonical schema does not supply the current model runner's adapter; compatibility must be verified by that adapter before execution.

Use development families to choose changes. Once test cases or labels influence a prompt, model, threshold or selection, retire those cases from final-test status and acquire independent holdout families. Keep a log of exposure and versions.

Report attempted, valid, scored, failed, missing, abstained and ambiguous counts; independent families; hard failures; and rubric distributions. Do not claim measured quality, calibration or significance from the supplied seeds. Compare paired changes only after reviewing labels and qualifying the evaluator with the controls in [RUBRIC.md](RUBRIC.md).
