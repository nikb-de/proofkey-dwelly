# Local case/event intake verification

Date:2026-10-10. Implementation commits: `7bd5fbd` (contracts/persistence), `cb39227` (HTTP integration). No external provider calls, deployments or business operations.

## Controller verification

```sh
python3.12 -B -W error::ResourceWarning -m unittest discover \
  -s tools/dwelly_service/tests -p 'test_*.py' -q
```

Result: **63 passed in32.851s**:19case-store tests,19real loopback HTTP tests and25existing service tests. No skips. Includes restart/idempotency, stale concurrent appends, malformed and oversized inputs, actual256case/128event bounds, corrupt readback, auth/host/origin checks, and absence of job/provider/budget activity during intake.

```sh
PYTHONPATH=runtime/src:runtime/tests \
  .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python \
  -B -W error::ResourceWarning -m unittest discover \
  -s tools/dwelly_bridge/tests -p 'test_*.py' -q
```

Result: **82 passed in2.025s**, no skips, including actual runtime shadow composition. This checks existing shadow behavior after the local-service addition; it does not execute a business workflow from a newly ingested case.

`openspec validate local-case-event-intake --strict`, `git diff --check`, `.env` Git-ignore check, shell syntax check and0600permission check also passed.

## Review status

Independent task reviews accepted both contracts/storage and HTTP integration without actionable findings. Controller verified the final combined service and shadow suites. Final whole-change review accepted the exact09d4a82..3a29b46diff for this local intake scope, with no Critical, Important or Minor findings. This is not approval for automatic analysis or operational effects.

## Precise boundary

- Data: caller-declared JSON relationships and English-labelled events, not authenticated business facts.
- Media: validated metadata references only; no upload, OCR, ASR or visual reasoning.
- Analysis: every new revision is `pending_not_started`; the fixed-bundle worker is unchanged and does not consume new cases.
- Operations: no scheduling, customer messages, returns, refunds, payouts or learned-policy activation.
- Deployment: local POSIX SQLite; cloud settings are reserved, no cloud resources created.

These are software contract tests, not correct-outcome rates or calibrated semantic evaluations. The older full runtime regression subsequently completed with1963tests and2package-closure failures caused by the separate shadow helper; remediation is tracked in `shadow-runtime-package-isolation`. It is not a passing regression for this increment. `.env` remains private and is not committed.
