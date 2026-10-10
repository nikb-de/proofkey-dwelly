# ProofKey / Right onTime

An evidence-backed case operations platform for delivery exceptions, built by **Sunday Grind** for the **Delivery & Logistics** track. The product keeps customer requests, delivery terms, model proposals, human decisions and action receipts together without treating a proposed action as an executed one.

Start with the local platform below. Submission status and the A–G requirements are recorded in [SUBMISSION.md](SUBMISSION.md), with scope and checks in the [submission audit](docs/submission-audit-2026-10-10.md). Watch the [product video](DEMO/Right-onTime-FINAL-1080p.mp4).

## 1. What you built

- A Team workspace for cases, evidence, requests, ownership, model runs and review history.
- A Customer view for reviewing offered delivery terms and recording a preference or acceptance against the current offer.
- A Preparation workspace for inspecting six adapter surfaces and exporting a local configuration draft.
- A PostgreSQL backend with immutable case revisions, source hashes, durable model jobs, budget reservations and stale-result checks.
- A cancellation, negotiation and booking workflow with explicit consent, local pseudo-Dispatch receipts, and a sandbox scheduler.
- Optional text-model reasoning, photo analysis and speech transcription; all provider calls are disabled by default.
- Separate development datasets, model/judge evaluation tools and a synthetic operational runtime.

The integrated product is a **local demonstration**, not a production logistics service. A local booking receipt does not establish a booking with a real carrier; coordination completion does not establish physical delivery. See the [platform guide](docs/platform-operations.md), [API contract](contracts/platform-v1/README.md) and [runtime scope](runtime/README.md).

## 2. What operational problem it solves

A delivery exception often arrives across several messages: cancel an old slot, find an alternative, check who must be present, agree a price, obtain consent and wait for Dispatch. Lost context can cause an agent to book an unacceptable slot, reuse consent after terms change, or announce success before the carrier confirms anything.

ProofKey preserves the evidence available at each step and distinguishes **request → proposed terms → explicit agreement → action request → confirmation**. The operator can see who is waiting on whom, what is missing and which exact evidence supports the next step.

## 3. Architecture

```mermaid
flowchart LR
  Team[Team and Customer UI] --> API[Loopback platform API]
  API --> DB[(PostgreSQL: cases, evidence, revisions)]
  DB --> Projection[Evidence-only projection]
  Projection --> Jobs[Durable model jobs and budget admission]
  Jobs --> Models[Optional model APIs]
  Models --> Proposal[Candidate and provider receipt]
  Proposal --> Team
  Team --> Review[Human review and consent record]
  Review --> Gate[Deterministic revision, terms and policy checks]
  Gate --> Sandbox[Local pseudo-Dispatch and sandbox scheduler]
  Sandbox --> Receipt[Stored local effect and confirmation receipt]
  Receipt --> DB
```

Deterministic code owns schema validation, revision/hash binding, offer freshness, consent and policy checks, idempotency, budget admission and local effect recording. Models propose interpretations and next steps; they cannot grant authority or execute business actions. Photo/ASR output remains a draft derivative until explicitly reviewed. Incoming text is evidence, not an instruction to change system policy.

Six integration surfaces exist: case/CRM, delivery, scheduling, returns, messaging and operator inbox. In the main platform, case records and the scheduler use local PostgreSQL; Dispatch and communication paths are local simulations or interfaces. No real courier, mailbox, telephone or payment account is connected. The separate [private cloud case-storage pilot](docs/verification/cloud-case-pilot-2026-10-10.md) is not the integrated product deployment.

## 4. How to run it

Run from the repository root. Prerequisites: **Python 3.12**, **uv**, **Docker Engine**, a modern browser and an available loopback port 8095. The example below starts PostgreSQL 17 on loopback port 54329. Internet access is needed for the first package/image download. No model API key is needed for the default local workflow. Optional audio validation requires `ffprobe` on `PATH`.

### Install Python dependencies

```sh
uv venv --python 3.12 .venv
. .venv/bin/activate
uv pip install --require-hashes -r requirements-postgres.lock
uv pip install -r requirements-platform.txt
```

The PostgreSQL dependencies are pinned with artifact hashes. The optional image dependency is version-pinned in [requirements-platform.txt](requirements-platform.txt). The explicit `uv` environment setup also works with uv-managed Python installations whose shortcut cannot bootstrap `python -m venv`. The separate runtime has its own [installation and dependency instructions](runtime/README.md); it is not required to start this UI.

### Start a fresh local database

The following is a first-start example. Use a new container/volume name if those names already exist. Keep the generated password in your private secret store for subsequent sessions; changing the environment variable later does not change an existing database's password.

```sh
export POSTGRES_PASSWORD="$(openssl rand -hex 32)"
docker run -d --name proofkey-platform-db \
  -p 127.0.0.1:54329:5432 \
  -e POSTGRES_USER=proofkey -e POSTGRES_DB=proofkey -e POSTGRES_PASSWORD \
  --mount type=volume,source=proofkey-platform-postgres,target=/var/lib/postgresql/data \
  postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652
docker exec proofkey-platform-db pg_isready -U proofkey -d proofkey
```

Wait until `pg_isready` reports accepting connections before continuing. An existing PostgreSQL instance may be used instead by supplying its connection string privately.

### Start the product

```sh
export PROOFKEY_PLATFORM_DATABASE_URL="postgresql://proofkey:${POSTGRES_PASSWORD}@127.0.0.1:54329/proofkey"
PYTHONPATH=.:tools:runtime/src python -m tools.dwelly_platform serve \
  --database-url-env PROOFKEY_PLATFORM_DATABASE_URL \
  --schema proofkey_platform_local --migrate --port 8095
```

Open [http://127.0.0.1:8095/](http://127.0.0.1:8095/). `--migrate` creates or updates the selected schema without clearing cases. The Team, Customer and Preparation pages share this local API. The server intentionally uses a trusted local operator model; keep it on loopback.

For a scripted case, in another terminal with the same virtual environment active:

```sh
python -m tools.dwelly_platform.terms_demo \
  --base-url http://127.0.0.1:8095 \
  --case-id "demo-terms-$(date +%s)" \
  --anchor-date "$(python -c 'from datetime import date, timedelta; print(date.today() + timedelta(days=1))')"
```

This creates a disclosed, date-shifted development replay in the local database. Its customer/Dispatch records are scripted operator attestations, with **zero model calls and zero external effects**. Open the resulting case in Team to inspect the request, terms, consent and confirmation history. It is not an official Reality Test result. See the [scenario packet](docs/demos/2026-10-10-case-001-terms/README.md).

Stop the server with Ctrl-C. `docker stop proofkey-platform-db` preserves the named database volume; `docker start proofkey-platform-db` resumes it. Do not delete the volume as part of routine shutdown.

### Optional services and verification

- [Local inbound email/chat/phone harness](docs/inbound-communications.md): add `--channel-config tools/dwelly_channels/examples/channels.local.json`; signed webhooks additionally need their configured secret environment variables and `--channel-port`. No real channel account is connected.
- [Offline case analysis workbench](docs/analysis-workbench.md): `python -m tools.dwelly_analysis serve --port 8093`. This is a separate UI, not the primary product.
- [Legacy model/evaluation CLI](tools/dwelly_model/README.md): `python -B -m tools.dwelly_model --help`; its `dry-run` uses a deterministic baseline, not a model.
- [Separate case-only Docker API](deploy/postgres/README.md): `compose.postgres.yaml` runs the older API, not the integrated platform UI.

For platform checks against a disposable PostgreSQL schema, the test DSN must permit schema creation and removal:

```sh
PROOFKEY_TEST_DATABASE_URL="$PROOFKEY_PLATFORM_DATABASE_URL" \
  PYTHONPATH=.:tools:runtime/src python -m unittest discover -s tools/dwelly_platform/tests -v
```

Database tests are skipped when the test DSN is absent; skips do not demonstrate database behavior. Browser and scripted-transport E2E setup is in [the E2E runbook](docs/case-model-e2e.md). Tests and local simulations do not establish real carrier integration or model accuracy.

## 5. Models, APIs and external services used

The platform's **active default configuration** is [model-profiles.example.json](tools/dwelly_analysis/model-profiles.example.json): `gpt-4.1-mini`, `claude-sonnet-4-6` and `gemini-2.5-flash`. The separately selectable [current profiles](tools/dwelly_analysis/model-profiles.current.json) contain `gpt-6.1-sol`, `claude-sonnet-5-5` and `gemini-3.8-flash`; they are not automatically selected. The [model-choice note](docs/releases/2026-10-10-model-choice/README.md) records a Claude Sonnet 5.5 fallback decision, not an activated deployment or a proven evaluation winner.

Text transports use OpenAI, Anthropic and Gemini APIs. Their environment variables are `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` and, when required by the configured Anthropic profile, `ANTHROPIC_WORKSPACE_ID`. Optional media defaults are OpenAI `gpt-4.1` for image analysis and `whisper-1` for ASR. Requested IDs are configuration; only retained provider responses establish an observed model identity.

New provider calls require explicit server startup flags: `--allow-live` for text reasoning and `--allow-media` for image/ASR. `--model-config` selects another text profile file; `--image-model` and `--asr-model` select media IDs. `--provider-env-file .env` loads allowlisted credentials without executing the file. Use [.env.platform.example](.env.platform.example) as a template; keep actual values in an ignored private file or secret store, never browser code or Git. Check account access, applicable pricing and data terms before authorizing paid calls.

Durable reservations limit each configured provider/model scope to USD 25. Reuse the same `--budget-scope` across restarts of one experiment. Media currently reserves the full USD 25 per request; unknown/failed requests retain their reservation. These are conservative application limits, not exact invoices or provider-enforced billing caps. No provider call is needed to inspect recorded results or the default demonstration.

## 6. Key assumptions

The included Dwelly public examples, authored case-state annotations and synthetic extensions are **development material**. They are already seen and do not constitute an unseen benchmark. Author labels and model-judge scores are not human-validated ground truth.

Only a selected, revision-bound evidence projection belongs in a model input. Raw narrative files may contain later outcomes; reference actions, labels and future continuations must remain outside the proposer input. Preserve case-family grouping when designing evaluation splits. Identity, consent and original evidence authenticity are not established merely by their presence in a submitted JSON record.

On 10 October 2026, the user confirmed that the organisers permitted publication of the provided Dwelly cases and derivatives. This is recorded as user-attested permission, not an independently inspected licence or a grant to re-license those materials. Their original terms remain separate from the application-code licence. See [public case provenance](data/dwelly-public-cases/README.md), [team catalog](datasets/team-widget-v1/README.md), [independent-case intake](docs/model-team-intake.md) and [licence status](LICENSE-STATUS.md).

## 7. Known limitations

- Local state, pseudo-Dispatch receipts and sandbox bookings are implemented. Production authentication/tenancy, real carriers, outbound messages, payments and end-to-end cloud operation are not verified.
- [Scripted-transport E2E evidence](docs/verification/case-model-e2e-2026-10-10/README.md) covers real local HTTP, PostgreSQL, workers and browser behavior while substituting the external model response.
- [A separate live-provider rerun](docs/verification/platform-live-e2e-2026-10-10-rerun/README.md) records 15 provider attempts, 13 retained responses and 12 accepted candidates. It found state/action errors and incomplete responses. Accepted JSON is not proof of a correct business decision.
- [The legacy 50-case development experiment](docs/model-release-verification.md) includes 142/150 scored judge outputs and eight Gemini errors. Uncalibrated judge scores and exposed cases cannot establish held-out accuracy.
- Media validation and review controls exist; meaningful image/audio quality, evidence authenticity and general operational reliability are not established by those controls.
- The official unseen Reality Test is not evidenced in [ANSWERS](ANSWERS/README.md). Do not replace missing or unsuccessful system outputs with human-written successes.
- Apache-2.0 applies to eligible original application code. The recorded organiser permission covers the provided Dwelly cases and derivatives; third-party code, services and other materials retain their own terms. [NOTICE.md](NOTICE.md) and [LICENSE-STATUS.md](LICENSE-STATUS.md) distinguish that permission from independently verified licensing.

## 8. What you'd build next

Retain the final audited source/video hashes and third-party notices. Launch post links are recorded in [SUBMISSION.md](SUBMISSION.md). Run the actual unseen cases through the frozen submitted system and preserve every outcome, including failures and escalations.

For product development, validate the state/action contract with independent cases and human reviewers; measure routing, groundedness and authority errors; then connect authenticated tenant identities and one real carrier adapter with explicit action authority and authoritative readback. Production hosting, durable media storage/retention, operational recovery and model-quality acceptance require separate verification.
