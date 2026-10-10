# Parallel model service verification — 10 October 2026

## Scope and evidence levels

This change adds a local single-operator service around the model package, not around the separate operational `runtime/`. It prepares an offline Cloud Run Job, but does not deploy resources or provide durable live cloud execution. No live provider experiment was run for this change.

| Verification | Observed result |
|---|---|
| Python 3.12 model suite | 74 tests passed, including 11 parallel/cancel/shared-budget tests and 3 cloud guards |
| Python 3.12 local service suite | 25 tests passed: real HTTP/SQLite, auth, idempotency, queue limits, corrupt-store errors, proposal readback, cancellation, current live permission and recovery |
| Case-intake suite | 58 tests passed; existing temporal isolation/provenance checks retained |
| Cloud Job template | YAML parsed and local bounds checked; not submitted to the Cloud Run API |
| Local Docker build | Passed using cached `proofkey-model:provider-fix`, `--pull=false --network=none` |
| Docker HTTP smoke | 2 actual public-development snapshots produced 2 unsent drafts, 0 API calls, 0 judge calls and 0 business effects |
| Docker restart | Stop/reopen returned the same completed job for the same idempotency key; no repeat execution |
| Final Docker permission regression | Earlier live task stayed queued after a live-disabled restart; offline work completed and its proposals were retrieved |
| Docker full offline bundle | 50/50 baseline proposals, no judges, zero provider calls/effects; this is not a model-quality result |

Model tests exercise concurrent synthetic transport responses, out-of-order completion, per-provider/global limits, coordinator-owned writes, proposal freezing before judge reference access, timeout/cancel reservation retention and shared cap continuity. They are not a measured speedup, provider throughput test or quality evaluation. Service tests include active cancellation and a second job sharing the retained ledger using a fake transport, not billed provider calls.

The integrated service image config ID at the initial smoke was `sha256:5d0d08e5bd97d9e1e0433a9d0d9278273836e82ddeeed4308dd45ae96129b152` (local Linux ARM64). The image ran as UID 10001 with a read-only input bind and persistent named volume `proofkey-service-smoke-20261010-v1`. That volume contains only offline public-case smoke artifacts and is retained for inspection. This is not an AMD64 Cloud Run image verification.

After the final permission repair, the image config ID was `sha256:44644150a5363521aef007b40676cef5658bf6d243150314906fa12bada45766`. A second network-disabled HTTP smoke used `proofkey-service-smoke-20261010-v2`: a queued live job stayed unclaimed across disabled restarts, two offline cases completed with two draft readbacks, and resubmission returned the same completed job. Both retained volumes contain test state, not real provider credentials or real shipments.

## Independent review

Task-scoped cross-reviews were followed by a fresh whole-change review. The final reviewer found one P1: startup without `--allow-live` still executed earlier queued live work. Commit `10e19e4` propagates current permission into the worker and transactional claim selection. Three new regressions cover default-off claims, Boolean policy validation and real HTTP restart behavior. Independent scoped re-review approved the fix and found no further material issue. Live-disabled jobs now remain queued rather than being cancelled or silently failed, while eligible offline jobs progress.

The final source checks passed with 74 model tests, 25 service tests and 58 case tests. Independent review is not a production security certification, cloud deployment test or model-quality calibration.

## Deterministic and nondeterministic parts

| Step | Existing implementation | What is not established |
|---|---|---|
| Select visible case evidence | Deterministic importer, time boundary, hashes and validators | Trusted origin signatures; meaningful vision/audio processing |
| Choose/contact/clarify next step | Live model emits a structured unsent proposal | Human-validated correctness, real logistics authority |
| Queue, budget, schema and cancellation | Deterministic service/coordinator, persistent local ledger | Multi-tenant or distributed cloud transactional storage |
| Assess quality | Three optional nondeterministic API judges, deterministic accounting | Calibrated ground truth or permission to execute |
| Perform business operation | Separate local synthetic runtime has policies, journal, six adapter interfaces | No implemented bridge from this service's proposal into that runtime; no verified real adapters |

The agent applies to ambiguous evidence and next-step proposals, not to inventing permissions or declaring success. A future runtime bridge must bind an authenticated case/object, pinned policy, consent, allowed operation and authoritative readback. A model or judge score does not supply any of these.

## Delivery limits

- Inference uses canonical bounded batches, favoring repeatable admission over maximum throughput. Direct runner calls remain serial by default; service defaults to four concurrent requests and two per provider.
- One service experiment is active at a time; independent case/provider requests inside it overlap. Pending admission is capped at 256 jobs.
- Proposal-only is the service default. Evaluation is explicit and retains the frozen-proposal barrier.
- The local queue requires private persistent POSIX storage. A previously running job without valid terminal evidence becomes interrupted and is not automatically retried. Cancellation drains already-dispatched calls and is not a refund.
- Cloud Run's ephemeral filesystem cannot hold the production queue/ledger. The cloud template is disposable offline smoke only. Live cloud calls and managed-cloud local-service startup fail closed until external durable admission/artifact storage is implemented.
- Historical full-live results remain 50 structurally valid proposals and 142/150 scored judges, with known semantic failures documented in [model release verification](../model-release-verification.md). This infrastructure change does not fix or re-evaluate those semantic failures.
- Independent implementation review and final verification status are recorded in the archived OpenSpec change and retained implementation ledger. No private GitHub update or deployment is implied by a local commit.

## Reproduction

From repository root, with Python 3.12:

```sh
python3 -B -m unittest discover -s tools/dwelly_model/tests -v
python3 -B -m unittest discover -s tools/dwelly_service/tests -v
python3 -B -m unittest discover -s tools/dwelly_cases/tests -v
```

See [local API usage](../model-service.md) and [Google Cloud preparation](../../deploy/cloud-run/README.md). Deployment, provider-billed throughput, external storage, IAM and crash handling in the target cloud project remain separate acceptance gates.
