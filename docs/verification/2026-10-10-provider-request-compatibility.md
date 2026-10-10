# Provider request compatibility — 10 October 2026

## Scope

Repair the production model-evaluation runner, not the separate operational
runtime. All generated contacts remain unsent proposals. No booking, payment,
return, customer message or other business effect is executed.

Three defects were reproduced and corrected:

1. OpenAI JSON mode: both model-input builders now explicitly include
   `output_format: json_object` before budget reservation and request persistence.
2. Anthropic organizational keys: optional `workspace_id_env` is validated and
   resolved into `anthropic-workspace-id` only for Anthropic. The public example
   contains an environment-variable name, never an account ID or secret.
3. Claude response formatting: a single complete outer JSON Markdown fence is
   normalized at the model-output parser, then strict JSON and schema validation
   still apply. Original provider receipts remain unchanged.

## Verification

- Model suite: **60/60 passed**. Includes missing/malformed workspace values,
  other-provider rejection, legacy scoped keys, secret-free preflight, exact
  saved/outbound OpenAI prompt equality, single-fence parsing, malformed replies,
  unchanged raw receipts and invalid evidence references.
- Case-intake suite: **58/58 passed**.
- Docker: rebuilt image and ran **60/60 model tests** with `--network none`.
- Docker offline CLI: **50/50 public cases** processed, zero API calls, zero
  operational effects, 150 missing judges as expected in offline mode.
- Independent code review: spec and quality passed; no actionable regressions.
- Separate-runtime regression: **incomplete, not passed**. It was deliberately
  interrupted after more than five minutes while running nested factory
  qualification checks. The separate `runtime/` tree is not shipped in this
  repository release and has no imports of `tools.dwelly_model`; its regression
  is not claimed as evidence for these fixes. The interrupted log is retained
  privately with the final smoke artifacts.

Docker image ID:
`sha256:b635942796259b56f2d35966ebe8e3d378c42b106c4612dc65454b276520659c`.

## Real API smoke

The unchanged production CLI ran two public development cases, `001` and `002`,
with `--live --limit 2 --no-baseline`, one judge pass and the optional recorded
reference action. The local budget ceiling was lowered to **USD1 per model**.
No transport was mocked and no requests were automatically retried.

| Provider | Requested model | Observed model | Received calls | Valid judge outputs |
|---|---|---|---:|---:|
| OpenAI | gpt-4.1-mini | gpt-4.1-mini-2025-04-14 | 4: 2 proposals + 2 judges | 2/2 |
| Anthropic | claude-sonnet-4-6 | claude-sonnet-4-6 | 2 judges | 2/2 |
| Gemini | gemini-2.5-flash | gemini-2.5-flash | 2 judges | 2/2 |

Final result: **8/8 responses, 2/2 valid proposals, 6/6 valid judge outputs, no
execution errors, zero operational effects**. Local reservations total
**USD0.141086**; this is not an invoice or actual billed spend.

The initial smoke, before fence normalization, also received all eight API
responses but rejected both Claude judgments as invalid formatting. Those
failed results are retained separately, not relabeled as success. Across both
smokes, reservations totaled **USD0.2823681**.

Private local evidence directories (ignored by Git):

- Initial: `outputs/dwelly-provider-compatibility-smoke-04epm95s/experiment/`
- Final: `outputs/dwelly-provider-compatibility-smoke-b7cz9p4b/experiment/`

Each contains exact requests, raw receipts, parsed proposals/judgments,
reservations and terminal summary. Private keys and the actual workspace ID
remain outside the repository in the operator's environment file.

## Meaning and limits

This establishes request compatibility and valid structured outputs for this
small live check. It does **not** establish unseen-case accuracy, calibrated
judging, 50-case coverage, human acceptance, image/audio understanding, or
production business-system integration. Public cases were already exposed;
the OpenAI proposer and OpenAI judge are not independent model families.

## Reproduce

```sh
python3 -B -m unittest discover -s tools/dwelly_model/tests
python3 -B -m unittest discover -s tools/dwelly_cases/tests
docker build -t proofkey-model:provider-fix .
docker run --rm --network none --entrypoint python \
  proofkey-model:provider-fix -B -m unittest discover -s tools/dwelly_model/tests
```

For live execution, configure private environment variables as described in
[the runner guide](../../tools/dwelly_model/README.md), lower the experiment
budget if appropriate, and use a fresh output directory. Do not publish raw
real-data receipts without review and redaction.
