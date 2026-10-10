# Retained development answer export

This offline adapter exports an existing `proofkey-model-job-v1` JSON document,
or a saved harness record containing `job`. It does not run a model, retry a
failed attempt, execute a proposed action, or turn development examples into
official unseen Reality Test results. Official inputs and results are not
available in the current submission evidence.

```sh
python3 -m tools.dwelly_submission \
  --record docs/verification/platform-live-e2e-2026-10-10-rerun/openai-gpt-4-1-mini/team/team-003-4.json \
  --output ANSWERS/DEVELOPMENT/openai
```

The directory named by the original case ID contains:

- `ANSWER.md`: retained input identity, exact candidate or no-output state,
  attempts, receipts, errors, evaluation and final observed status. Proposed
  communications and escalations remain proposals.
- `REASONING.md`: only recorded public rationale, evidence references,
  uncertainty and approval requirements. It never reconstructs hidden reasoning.
- `SOURCE_RECORD.json`: byte-identical source record, including all fields not
  repeated in the summary.
- `INPUT.json`: complete stored input field from the retained job. This is not
  necessarily the provider wire request or system prompt; its hash and the
  system's recorded input hash are distinct.
- `EXPORT.json`: SHA256 hashes of every other exported file and zero-call/zero-action
  packaging receipt. The original system's attempt and effect counts remain in
  `ANSWER.md` and the source record.

Repeat `--attachment path/to/file` to preserve raw provider responses or
operational logs byte for byte with indexed names. Attach only artifacts known
to belong to this run. The exporter cannot recover missing responses, verify
an attachment's relationship to the job, or verify source authenticity.

Existing case directories are refused, including partial exports. The caller
must supply separate output roots for different providers or attempts that use
the same case ID. All exports are explicitly marked **development**; the CLI
does not provide an official-result mode. No result is manually corrected.

Verification: `python3 -m unittest discover -s tools/dwelly_submission/tests -v`.
