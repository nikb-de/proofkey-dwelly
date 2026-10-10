# Official Reality Test run — Delivery & Logistics

## Result and scope

The fixed baseline completed **30 provider calls** at **16:37:51 Europe/London,
10 October 2026**. The unchanged model parser accepted 29 candidates; case
**014** returned malformed JSON and remains a failed result. There were no
automatic retries, no manual answer corrections and zero external business
effects. Format acceptance is not an assessment of decision correctness.

The organiser-format answers are in [ANSWERS](../../../ANSWERS/README.md).
The raw failed output is retained in
[case 014](../../../ANSWERS/014/SOURCE_RESULT.json).

## Frozen configuration

- Official source: `DwellyOrg/HackatonChallenges`, revision
  `ce84e8c0d8f7f8ddacd8d8fcfe53516c22885db7`, Delivery & Logistics only.
- Base application revision: `fd8533297d259f4a997710045852e4eb2f3ef771`.
  The input adapter/runner's exact source hashes are also in the manifest;
  they were added for this run and were not part of that base commit.
- Requested and observed model: `claude-sonnet-5-5`; adaptive thinking with
  high effort explicitly requested in the retained wire payloads.
- Existing baseline system prompt SHA-256:
  `61592fb429180e7da972a572ffc17e0379944c8bd7f2a84f049f725e510cbf80`.
  It differs from the existing platform system string only by a trailing newline.
- Three concurrent calls; USD 25 per-provider/model admission cap.
  Total retained reservation: USD **2.891794**, not an invoice or actual spend.
- Exact prompts, selected profiles, code/source hashes and all 30 outcomes:
  [run/](run/), [manifest](run/manifest.json),
  [summary](run/run-summary-1791646671592086000.json).

## Inputs and attachment limits

All 79 supplied files were retained. The model consumed each case's decision-time
history, case card and extracted text from 13 PDF and 6 PNG attachments. Original
files, text sidecars and extraction receipts are preserved in the run directory.
Text extraction is not independent verification of a document's truth.

PNG extraction used Apple Vision OCR via the supplied Objective-C helper after
the local Swift compiler failed. OCR is not image reasoning or QR/barcode decoding.
Case 022 has a low-confidence OCR line (0.30) whose glyphs remain unchanged.
Confidence/geometry remain in the OCR receipt but were not included in the model
input; this is a limitation, not a silently corrected observation.

## Execution boundaries

This run invokes the existing model contract directly through a new input-only
adapter and retained provider transport. It does **not** exercise the UI,
PostgreSQL case lifecycle, real carrier or mailbox integration. Actor names and
roles come from supplied records and do not establish authenticated authority.
Selected action targets can still be wrong despite valid JSON.

The formatter quotes the actual model's decision, uncertainty and evidence
references. It does not invent a separate explanation or reconstruct hidden
reasoning. Proposed transfers, callbacks and escalations are not recorded as
performed operations. The separate development eval campaign and judge
reliability pilot do not alter these official answers.

The separate [judge pilot report](../reality-calibration-2026-10-10/RESULTS.md)
retains 108 judgments on fixed development controls. It records repeat-score
variation and three abstentions; it does not certify these official decisions.

## Reproduction

See [the runner](../../../tools/dwelly_reality/README.md) for preparation,
live execution and export commands. Reuse retained results for inspection;
a new paid run must use a new explicitly budgeted experiment. Never overwrite
or repair these submitted output files.
