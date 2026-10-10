# Independent frozen-run review

Reviewed read-only on 10 October 2026. No live code, inputs, prompts, outputs,
credentials, or dispatch state were edited. This review is not a semantic answer
grade or an operational end-to-end acceptance.

## Scope and findings

No critical source mutation, known-credential disclosure, evaluator-label
injection, prompt substitution, or business-effect execution was observed in the
inspected campaign at `/tmp/proofkey-reality-campaign-20261010`.

One concrete input limitation remains: the case 022 PNG OCR includes the line
`可 口` at native Vision confidence approximately 0.30. The model input contains
that line as ordinary untrusted extracted text without its confidence value.
`tools/dwelly_reality/runner.py:112` constructs this text-only derivative;
`runner.py:116` records hashes but no confidence. The confidence and bounding box
are retained in `sidecars/022/attachments/return-code.png.ocr.json` and the copied
extraction manifest, so the uncertainty is recoverable for review. This is not a
claim that a QR code was decoded or that the glyphs are correct. No live input
was changed to address it.

## Verified bindings

- The 79 source files are exactly 30 case indexes, 30 histories, and 19 attachments.
  Their SHA-256 hashes match both the original source checkout and all frozen
  copies. Source commit: `ce84e8c0d8f7f8ddacd8d8fcfe53516c22885db7`.
- The 19 attachment derivatives are present and match their manifest hashes.
  All are explicitly qualified as unverified extraction. Thirteen use Poppler
  text extraction; six use native Apple Vision OCR. The full copied extraction
  manifest equals the independently checked source manifest.
- All seven frozen implementation/configuration files still match the campaign
  manifest. Code commit recorded at preparation:
  `fd8533297d259f4a997710045852e4eb2f3ef771`.
- All 30 frozen JSON inputs and prompt hashes match. Each model user payload is
  exactly an `input` object, without evaluator labels or answer files.
- Independently checked timestamps and known-at-desk times for all 182 included
  history events: none exceeds its case's decision cutoff.
- System prompt SHA-256 is
  `61592fb429180e7da972a572ffc17e0379944c8bd7f2a84f049f725e510cbf80`, matching the
  existing evaluation baseline file. It equals the submitted platform system
  after trimming whitespace. Effort is explicitly `high`.
- All 30 actual retained request bodies preserve the frozen system and user
  prompt and use Anthropic adaptive thinking with high effort. No tool-call or
  business-operation adapter is attached. Requested and observed identity are
  retained separately and both equal `claude-sonnet-5-5` in inspected responses.
- A value-only scan using the four configured credential variables found no
  exact credential value in retained JSON, JSONL, Markdown, or text files. This
  checks known configured values, not every possible sensitive datum.
- The runner's nine existing tests pass. Their replaced transport boundaries are
  local tests, not live provider evidence.

## Completed transport run, independently checked at 15:38 UTC

All 30 result files and wire records were present. There were 30 dispatches,
29 structurally accepted outputs, and one failed local validation (`014`,
`invalid_model_output`). All 30 recorded both requested and observed model as
`claude-sonnet-5-5`. There were zero retries, zero skipped cases, and zero business
effects. The run took 56.312 seconds. Thirty conservative budget reservations
totalled USD 2.891794 under the USD 25 per-model cap; this is not billed cost.

No binding or known-credential-scan failure was found across the complete run.
The terminal record is
`/tmp/proofkey-reality-campaign-20261010/run-summary-1791646671592086000.json`.
Structural acceptance does not establish correct decisions. The reviewer did
not amend prompts from official case answers or author replacement answers.

The independent development evaluation campaign remains separate, with its own
dataset, ledger and outputs. It was not restarted or changed by this review.
