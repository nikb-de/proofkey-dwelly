# Model release verification — 10 October 2026

Scope: the standalone `tools/dwelly_model` package and its `tools/dwelly_cases` dependency. The separate operational runtime is excluded from this release and these results.

## Current verification — full 50-case development experiment, 10 October 2026

Experiment `dwelly-development-50-ht9vgukr` completed using the model-package implementation unchanged from commit `fbf8b96`. The terminal summary and persisted proposal/judge records establish these counts:

| Check | Result |
|---|---|
| Public development cases / structurally valid proposals | 50 / 50 |
| API attempts | 200: 50 proposer calls and 150 judge calls |
| Scored judge outputs | 142/150 |
| Judge errors excluded from scores | 8, all Gemini `incomplete_response` |
| Abstentions | 0 |
| Business effects | 0; all proposals remain unsent |
| Reserved spend / local cap | USD 3.5423817 reserved; USD 5 per provider/model |
| Human-reviewed quality / calibrated judging / unseen accuracy | **Not established** |

Reservations are conservative local admission amounts, not an invoice or actual billed spend. Failed calls retain their reservations. The run used `--live --limit 50 --no-baseline`, one judge pass and the recorded reference action. The proposer received only decision-time snapshots; the reference was available only to judges after proposals were frozen. All 50 cases are already-exposed public development examples, not an independent untouched holdout.

| Judge provider | Scored / expected | Errors | Cases with model-reported critical failures |
|---|---:|---:|---|
| OpenAI | 50/50 | 0 | None reported |
| Anthropic / Claude | 50/50 | 0 | 007, 035, 039, 042 |
| Gemini | 42/50 | 8 | None reported among scored outputs |

The eight Gemini errors occurred on cases 007, 011, 013, 016, 032, 036, 041 and 049. They contribute neither scores nor successful judgments. Claude reported seven critical-failure statements across the four cases listed above; these are model flags, not human adjudications. OpenAI produced the proposals and also occupied one judge seat, so that shared model family is not independent evidence.

Frozen proposal-set SHA-256: `2bd3840a66092473a642698d5b70daeecb70ce2baae98429d68bfbae28752f2a`. The experiment ID and hash identify this result without publishing raw private output files.

### Observed semantic failures

An internal assistant spot-check compared visible decision-time snapshots with frozen proposals. Cases 006, 007 and 010 were inspected before reading their judges; cases 035, 039 and 042 were inspected after model flags were available. This is neither human validation nor another API judge, and it does not produce an accuracy estimate.

| Case | Directly observed problem |
|---|---|
| 006, 010 | Provider-directed instructions name the internal receiving delivery desk instead of the visible routing or dispatch provider. |
| 007 | The proposal says the customer's requested date exceeds a two-day extension even though that date is the allowed endpoint; it asks for an already supplied choice again. |
| 035 | The proposal claims a warehouse receipt is attached although the snapshot has no attachments and contains the receipt inline. |
| 039 | The proposal offers pickup and drop-off return methods that the visible evidence never establishes. |
| 042 | The proposal invents carrier unloading options and presents them as suitable within the spending limit without a visible offer or quote. |

For case 007, OpenAI gave 4/4 on every rubric with no critical failure, while Claude flagged the false policy claim and Gemini returned `incomplete_response`. This concrete false positive is a reason to test judge sensitivity; it is not evidence that either provider is generally calibrated. High average scores or agreement cannot erase the observed defects.

Next work is independent team data, correct/incorrect judge controls and calibration, then a bounded general prompt candidate addressing routing, policy boundaries and unsupported claims. No prompt fix or measured improvement is claimed here.

## Earlier provider compatibility verification — 10 October 2026

The [retained provider compatibility record](verification/2026-10-10-provider-request-compatibility.md) documents the following results after the request-format and Anthropic workspace fixes:

| Check | Result |
|---|---|
| Model-package tests | 60/60 passed |
| Intake/baseline tests | 58/58 passed |
| Rebuilt Docker image, model tests with networking disabled | 60/60 passed |
| Docker offline run | 50/50 public cases; zero API calls and zero business effects |
| Offline judge accounting | 150 missing judges, as expected in offline mode |
| Two-case live API smoke | 8/8 received responses; 2/2 valid proposals; 6/6 valid judge outputs across OpenAI, Anthropic and Gemini |
| Live smoke errors / business effects | 0 / 0 |
| Human-reviewed semantic quality / calibrated judging / unseen accuracy | **Not established** |

The live smoke used `--live --limit 2 --no-baseline`, one judge pass and the recorded reference action. Its local ceiling was USD 1 per model and its reservations totaled USD 0.141086; reservations are not an invoice or actual billed spend. The initial smoke received all eight responses but rejected both Claude judgments before the model-output fence fix. Those failed results remain separate. The final smoke demonstrates request compatibility and valid structured output on two already-exposed development cases, not a model-quality or safety acceptance result.

The Docker image rebuilt for this update on 10 October 2026 was `sha256:b635942796259b56f2d35966ebe8e3d378c42b106c4612dc65454b276520659c`. Its recorded scope is the 60-test model suite with networking disabled and the 50-case offline CLI run. The additional runtime regression attempt made during provider-compatibility verification was interrupted, while the distinct original intake regression has no completed result; neither is a passed runtime regression or evidence for this release.

## Historical initial-release verification — 10 October 2026

The following observations predate the provider compatibility update. In particular, the 41-test count and absence of a live experiment describe that earlier snapshot, not the current verification status.

| Check | Result |
|---|---|
| Python 3.12.14 model-package tests | 41 passed |
| Python 3.12.14 intake/baseline tests | 58 passed |
| Docker build and CLI help | Passed |
| Docker offline run, networking disabled, input read-only | 50/50 proposals; zero operational effects |
| Offline judge accounting | 150 expected seats, 150 missing, zero scored; means `null` |
| Offline API calls / reserved spend | 0 / USD 0 |
| Actual provider API experiment at this snapshot | **Not run: credentials unavailable** |
| Human-reviewed semantic quality / unseen accuracy | **Not established** |

The offline proposals are the deterministic baseline, **not model-generated answers**. Their set hash is `fef641f6e072b4538af4d3fbec578e7431e17371858818416c09067233bb649d`, matching the historical baseline. This is reproducibility evidence, not quality improvement.

The initial clean publication candidate passed both suites using only its included source and data. Relative Markdown links were checked against that assembled repository. At that snapshot the compact architecture contained 546 words and two diagrams; six total diagrams including the detailed reference were rendered and visually inspected locally with Mermaid 11.12.0. No label clipping or box overflow remained in that local rendering. GitHub's hosted renderer was not independently inspected.

Historical Docker image identifier for the initial verified build: `sha256:62aa38f1471d762e945b772e55471844486aa6f006400316733eee1d1d6d9947`. Its resolved base was `python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`. This image is separate from the later provider compatibility build above. Local build IDs are evidence of the respective builds, not published registry images or bit-for-bit reproducibility promises.

## Verification commands

```sh
python3 -B -m unittest discover -s tools/dwelly_model/tests -v
python3 -B -m unittest discover -s tools/dwelly_cases/tests -v
docker build -t proofkey-model:0.1 .
docker run --rm --network none proofkey-model:0.1 --help
docker run --rm --network none \
  -v "$PWD/data/dwelly-public-cases:/data:ro" \
  -v /tmp/proofkey-results:/results \
  proofkey-model:0.1 dry-run \
  --config /app/tools/dwelly_model/config.example.json \
  --bundle /data --output /results/new-offline-run --limit 50
```

Output directories must be fresh. The package is stdlib-only on Python 3.11+; verification used 3.12, not every supported platform. The ledger uses POSIX file locking; Windows is not verified.

## Review and interpretation

Independent review found and prompted regressions for nonfinite/duplicate provider JSON, deeply nested generated JSON, HTTP protocol exceptions, and invalid Unicode surrogates. Fixes reject unsafe envelopes, preserve per-seat errors/reservations, sanitize protocol errors, and reject malformed strings while accepting valid emoji. Model tests replace only the network boundary; their simulated responses are never counted as live provider participation.

The eight anchored rubrics assess next action, routing, required details, grounding, authority/consent, fabricated outcomes, escalation and clarity. All grades remain provisional and uncalibrated, including the 142 scored judge outputs from the full development run. OpenAI proposes and also occupies one judge seat in the example, so family bias is disclosed. Consensus is not ground truth or permission to execute.

The cap is USD 25 per provider/model **within one experiment**, under explicitly configured prices. Failed requests retain their reservations. This is not a provider account billing limit or a global campaign cap. Runtime credential presence is not authentication, billing verification or a successful API response.

Release readiness is distinct from hackathon submission readiness. Private-source publication does not clear dataset rights, make the repository public, produce a demo video, validate business outcomes, or finish official submission. See [remaining gates](../SUBMISSION.md).
