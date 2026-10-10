# Model release verification — 10 October 2026

Scope: the standalone `tools/dwelly_model` package and its `tools/dwelly_cases` dependency. The separate operational runtime is excluded from this release and these results.

## Observed verification

| Check | Result |
|---|---|
| Python 3.12.14 model-package tests | 41 passed |
| Python 3.12.14 intake/baseline tests | 58 passed |
| Docker build and CLI help | Passed |
| Docker offline run, networking disabled, input read-only | 50/50 proposals; zero operational effects |
| Offline judge accounting | 150 expected seats, 150 missing, zero scored; means `null` |
| Offline API calls / reserved spend | 0 / USD 0 |
| Actual provider API experiment | **Not run: credentials unavailable** |
| Human-reviewed semantic quality / unseen accuracy | **Not established** |

The offline proposals are the deterministic baseline, **not model-generated answers**. Their set hash is `fef641f6e072b4538af4d3fbec578e7431e17371858818416c09067233bb649d`, matching the historical baseline. This is reproducibility evidence, not quality improvement.

The clean publication candidate passed both suites using only its included source and data. Relative Markdown links were checked against the assembled repository. The compact architecture contains 546 words and two diagrams; six total diagrams including the detailed reference were rendered and visually inspected locally with Mermaid 11.12.0. No label clipping or box overflow remained in that local rendering. GitHub's hosted renderer was not independently inspected.

Docker image identifier for the verified build: `sha256:62aa38f1471d762e945b772e55471844486aa6f006400316733eee1d1d6d9947`. Resolved base: `python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`. Local build IDs are evidence of this build, not a published registry image or a bit-for-bit reproducibility promise.

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

The eight anchored rubrics assess next action, routing, required details, grounding, authority/consent, fabricated outcomes, escalation and clarity. Their future grades remain provisional. OpenAI proposes and also occupies one judge seat in the example, so family bias is disclosed. Consensus is not ground truth or permission to execute.

The cap is USD 25 per provider/model **within one experiment**, under explicitly configured prices. Failed requests retain their reservations. This is not a provider account billing limit or a global campaign cap. Runtime credential presence is not authentication, billing verification or a successful API response.

Release readiness is distinct from hackathon submission readiness. Private-source publication does not clear dataset rights, make the repository public, produce a demo video, validate business outcomes, or finish official submission. See [remaining gates](../SUBMISSION.md).
