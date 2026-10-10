# Model proposals and three API judges

Experimental Python 3.11+ standard-library package. This adds API-backed next-action proposals and independent OpenAI, Anthropic and Gemini judge calls. It does **not** send customer messages, change bookings, create returns or move money. Model grades are **provisional and not human validated**.

## Quick start from this repository

```sh
python3 -B -m tools.dwelly_model --help
python3 -B -m tools.dwelly_model preflight --config tools/dwelly_model/config.example.json
python3 -B -m tools.dwelly_model dry-run \
  --config tools/dwelly_model/config.example.json \
  --bundle data/dwelly-public-cases --output /tmp/proofkey-offline-new --limit 2
```

The output directory must not exist. `preflight` makes no API requests and exits 2 if credentials are missing. Offline mode uses the original deterministic baseline, records missing judgments and makes no model-quality claim. A successful dry-run is not a successful model experiment.

Set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` in your shell or private secret manager. Do not put keys into config, commits or chat. The example model IDs and prices are editable: check current provider availability/prices before live execution. API access/billing is separate from availability in a chat application.

```sh
python3 -B -m tools.dwelly_model run --live \
  --config tools/dwelly_model/config.example.json \
  --bundle data/dwelly-public-cases --output /tmp/proofkey-live-new --limit 2
```

Start with 2 cases, inspect the actual provider receipts and reservations, then use a new output directory and `--limit 50` for the full development batch. `--no-reference` asks judges to grade without the recorded next-action example. `--no-baseline` skips baseline comparison. `--repeat-judges 1` repeats grading of identical proposals to expose verdict variability; repeats consume the same model budget. No automatic retry or silent provider substitution is performed.

## Docker

```sh
docker build -t proofkey-model:0.1 .
docker run --rm proofkey-model:0.1 --help
docker run --rm \
  -v "$PWD/data/dwelly-public-cases:/data:ro" \
  -v /tmp/proofkey-results:/results \
  proofkey-model:0.1 dry-run \
  --config /app/tools/dwelly_model/config.example.json \
  --bundle /data --output /results/offline-new --limit 2
```

For live mode use the same read-only input mount, `run --live`, and pass credentials at runtime with `--env-file /absolute/private/path/provider.env`. The env file is never copied into the image. Do not run with privileged mode or mount the entire repository as writable agent input. Base image tag is not digest-pinned; record the locally built image ID when reproducing.

## Evaluation meaning

The model receives only validated decision-time events. It does not receive index summaries, later confirmations, or the recorded next action. All proposals are frozen before references are loaded. Judges receive the visible snapshot, anonymized proposal and optionally only the recorded next action as a **non-unique example**, not future outcomes.

Eight rubric dimensions score 0–4: next action, routing, required details, grounding, authority/consent, no fabrication, escalation and clarity. Critical failures and abstentions remain separate from numeric means. Missing/invalid judges never count as zero or success. Model agreement is not ground truth or execution authorization. The example uses OpenAI for both proposer and one judge: this family relationship is not independent and must be considered when interpreting agreement.

Retained outputs include exact prompts/receipts as produced by the runner, proposal identity, scores, missing/error status, budget reservations and a summary. They can contain case text. Keep real-data outputs private and redact/review before publication. Never embed a provider credential in source case text; no system can promise to sanitize an arbitrary secret echoed from its input.

All 50 public cases are already-exposed **development** examples. New evaluation cases and real examples must come from the team: [intake contract](../../docs/model-team-intake.md). No unseen test accuracy, human calibration, vision/audio understanding or real provider integration is claimed.

## Spending

`budget_per_model_usd` cannot exceed 25. Reservations are shared by identical provider/model within an experiment, including producer and judge calls. Reservations precede dispatch and remain charged after errors/unknown billing. Input is conservatively estimated using UTF-8 bytes plus framing allowance; output uses the configured cap. This is an application admission limit under the configured rates, **not a provider-side billing cap or exact invoice**. Configure provider billing limits separately. A fresh output directory starts a new experiment and a new budget; do not use it to bypass your own approved campaign cap.

Example-rate sources checked 10 October 2026: [OpenAI GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). No model alias availability is established until its actual API call succeeds.

## Tests

```sh
python3 -B -m unittest discover -s tools/dwelly_model/tests -v
python3 -B -m unittest discover -s tools/dwelly_cases/tests -v
```

Transport tests replace the network boundary. Their synthetic replies are test fixtures, never reported as live participation. This release does not include the separate operational runtime.
