# ProofKey — model-backed logistics decisions and evaluation harness

Private experimental release for the Dwelly Delivery & Logistics track. **Runnable source, CLI and Docker are included.** The model proposes the next communication; three API judges assess its content. Nothing sends messages, books deliveries or transfers money.

Start with [model quickstart](tools/dwelly_model/README.md), [local asynchronous service](docs/model-service.md), [team data intake](docs/model-team-intake.md), [architecture](docs/architecture.md) and [raw/agent/evaluation data](data/dwelly-public-cases/README.md). There is no complete hackathon submission, video, live logistics integration or human-validated model-quality claim.

## 1. What we built

- A bounded importer for 50 public fictional logistics cases, separating visible input from future answers.
- The original deterministic baseline for comparison.
- A model proposer with OpenAI, Anthropic and Gemini API transports; the example selects OpenAI.
- Three separately attributable API judge seats with eight anchored rubrics, abstention and critical-failure reporting.
- A CLI, Docker build, offline tests, immutable experiment artifacts and conservative per-model spend reservations.
- A local authenticated job service with persistent queue, proposal readback, cancellation and optional evaluation; bounded parallel provider calls run inside one active experiment. See [service boundaries and commands](docs/model-service.md).
- A [local case/event pseudo API](docs/local-case-intake.md) with immutable revisions and declared JSON relationships. New input remains pending analysis; media is metadata-only.
- An optional [read-only shadow bridge](tools/dwelly_bridge/README.md) for validated model-result/runtime associations. It grants no execution authority.

Google Cloud deployment is **prepared, not performed**: the [Cloud Run Job template](deploy/cloud-run/README.md) is offline-only. The local queue must not be deployed as a durable Cloud Run HTTP service; live cloud requests fail closed until external durable admission and artifact storage exist.

The separate operational runtime is **not included**. Its synthetic rescheduling/refusal examples and six adapter interfaces are described only in the architecture.

## 2. Operational problem

Logistics requests contain conflicting messages, missing evidence and unclear permission. A good next step must identify the correct party, ask for exactly what is missing, preserve useful details and avoid claiming that a requested action already happened. The harness separates a proposal, an evaluation and authority to execute.

## 3. Architecture

```text
Public source history
  ├── decision-time snapshot → model proposer → frozen unsent proposal
  └── separate reference action ─────────────────────┐
                                                   ↓
                      OpenAI + Claude + Gemini API judges
                                                   ↓
                      provisional scores / disagreements / errors
```

Judges see anonymized proposed communications, visible evidence and optionally a recorded next-action example. They never receive later confirmations. The reference is not a unique gold answer. Source text and model scores cannot grant execution authority. See [architecture](docs/architecture.md).

## 4. How to run

Python 3.11+; no third-party Python packages required.

```sh
python3 -B -m tools.dwelly_model --help
python3 -B -m tools.dwelly_model dry-run \
  --config tools/dwelly_model/config.example.json \
  --bundle data/dwelly-public-cases --output /tmp/proofkey-offline-new --limit 2
docker build -t proofkey-model:0.1 .
docker run --rm proofkey-model:0.1 --help
```

Then configure credentials and explicitly choose `run --live`; see [full commands, volumes and limits](tools/dwelly_model/README.md). Output paths must be new. A dry-run uses the baseline and never claims model participation.

## 5. Models, APIs and external services

The example configuration selects `gpt-4.1-mini` for proposals and the OpenAI judge, `claude-sonnet-4-6` for the Anthropic judge, and `gemini-2.5-flash` for the Gemini judge. These are configurable example IDs, not a guarantee of account access or a claim about the best current model. Provider-reported identity is preserved separately from the request.

Required environment variables for the example configuration: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` and `ANTHROPIC_WORKSPACE_ID`. For an Anthropic key already scoped to one workspace, remove that seat's `workspace_id_env` field if an explicit workspace header is unnecessary; see [workspace setup](tools/dwelly_model/README.md). Never commit key values or the actual workspace ID. `preflight` checks presence only, not validity or balance. API transports use fixed HTTPS endpoints and do not retry or substitute models. The OpenAI producer/judge family relationship is disclosed in each experiment.

The CLI reserves up to USD 25 per provider/model per experiment, including repeats and proposer/judge calls using the same model. The local service reuses one persistent ledger across its jobs and restarts instead of resetting the cap for each submission. These are conservative local limits under configured prices, not account-level provider billing caps. The service defaults to proposal-only; three-judge assessment is opt-in.

## 6. Assumptions and data

All 50 included public cases are fictional, English, already-seen development examples. Raw Markdown contains future information: **do not give the entire repository to an agent**. Only the selected `agent/<case>.json` is proposal input. The six attachments occur after the original cutoff, and are not initial model inputs.

Team-owned independent evaluation cases and real data remain pending. Follow [the intake contract](docs/model-team-intake.md) for 10–20 new eval cases and 10–20 appropriately permitted/redacted real examples. Do not upload private Drive originals or real data merely because they are accessible locally.

## 7. Known limitations and evidence

The saved historical baseline had 50 valid drafts and 11/50 routing matches; this is **not semantic accuracy**. Its results stay in [pilot/](data/dwelly-public-cases/pilot). New model quality must be read from actual experiment receipts, not inferred from passing unit tests or a Docker build.

The [current verification record](docs/model-release-verification.md) now includes the completed 50-case development experiment: 50 structurally valid proposals, 200 API attempts, 142/150 scored judge outputs, eight Gemini errors, no abstentions and zero business effects. USD 3.5423817 was reserved under a USD 5 per-provider/model cap; this is not an invoice. Earlier verification recorded 60 model tests, 58 intake tests, an offline 50-case Docker run and a two-case live smoke.

An internal assistant spot-check found wrong-party routing, a false date-boundary claim, an invented attachment and unsupported service options; see [observed semantic failures](docs/model-release-verification.md#observed-semantic-failures). On one faulty proposal, OpenAI awarded all eight maximum scores while Claude flagged a critical error. Structurally valid outputs and judge agreement do not establish correctness.

Eight rubric scores assess next action, routing, required details, grounding, authority/consent, fabrication, escalation and clarity. All are provisional model judgments. No human calibration, untouched holdout, semantic safety certification, meaningful vision/audio or operational execution is claimed. Missing/error/abstaining judge seats never become zero scores or successes. Read [release verification](docs/model-release-verification.md) for the actual available evidence.

This private release does not resolve ownership or redistribution rights for upstream examples. [Licence status](LICENSE-STATUS.md) remains applicable; model service/output terms are separate. Standard-library code introduces no provider SDK dependency. The Docker base image has its own terms.

## 8. Next steps

Collect the team's independent evaluation cases and permitted real examples, calibrate judges against explicit correct and incorrect controls, and test a bounded general prompt candidate for routing, policy boundaries and unsupported claims. That candidate has not been implemented or evaluated. Obtain human review before asserting correctness. A bridge to the execution runtime, native adapters, demo video and unseen challenge submission remain separate work.
