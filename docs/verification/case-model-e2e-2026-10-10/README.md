# Authored-case model E2E — 2026-10-10

Status: local integration verified with a **scripted external model transport**.
Live provider validation is **unavailable**, not passed. Zero live provider calls.

## Evidence

| Verification | Observed result |
|---|---|
| New replay, checker, runner, fixture and recovery tests | 99 passed |
| Final canonical Python regression | 667 passed plus 789 subtests |
| Platform and widget Node suites, including Chromium inspector test | 62 passed, zero skips |
| Actual HTTP → PostgreSQL → worker → UI | Passed, `mode=simulated` |
| Source coverage | All 16 specified cutoffs; one logistics family plus one UI control |
| Scripted dispatches | Exactly 18: 16 CLI cutoffs plus two UI-triggered jobs |
| Retry/effect controls | One dispatch per job, zero automatic retries, zero business effects |
| Browser | Running/terminal, waiting target, reload, stale result, unknown outcome, inspector persistence, no exceptions, no mobile overflow |
| Isolation | UUID test schema dropped and absence verified |
| Browser-launch failure control | Intentionally failed launch; zero dispatches; schema still dropped |
| Live canary preflight on normal local platform | Exit 2, `model_execution_disabled`; no provider request |

The 99-test suite is included in, not added to, the final 667-test regression.
The subsequent reporting-wording adjustment was separately RED/GREEN verified:
one targeted test passed. The selected canonical test roots exclude archived
repository copies in `outputs/`; bare repository-wide discovery collides with
those old copies and is not the verification command for this checkout.

## Retained local artifacts

The full raw local run is in `outputs/case-model-e2e-20261010/`, including
`runner/report.json`, individual HTTP exchanges, source/expectation/check records,
`database-report.json`, `browser-report.json`, screenshots and JUnit files. This
ignored output directory is not published by the source commit.

The final unavailable live preflight is retained separately at
`outputs/case-model-e2e-live-preflight-final-20261010/`. Its explicit unavailable status
takes precedence over the requested `live` mode label.

Selected artifact SHA-256 values:

```text
browser-report.json  87866d76e6326fd49fa2c13402bcfd90d7100cc6b69b8524c9a154a961212330
database-report.json 258f1341ae02899bbed37a6f2ee05194c209f085d1a44eb9ac7af283613aaf4c
runner/report.json   3876d1bea6b45de63988fc766956ad32fe2b0936a2bef1b3b27b4854f614ebf3
final-e2e-junit.xml  fe3e5481a832920d865b6e9aa540317b3a2028403c4a78e695d408c66a9f301d
```

## Independent review and remediation

Cross-author reviews found and reproduced: incomplete terminal replay comparison,
malformed capability responses escaping report finalization, Markdown redaction
gaps, open inspectors collapsing during polling, and browser-startup cleanup /
coverage assertion weaknesses. These were fixed and re-reviewed. The final scoped
re-review found no remaining actionable issues. This was code/test review, not a
multi-provider judge assessment or a production certification.

## What is not demonstrated

- Live OpenAI/Claude/Gemini state accuracy or cross-model agreement.
- Team-validated labels, held-out performance or 16 independent business cases.
- Literal host/process-kill recovery: the recovery tests reconstruct runtime objects
  and expire database leases, including saved-response and lost-response branches.
- Production authentication, real carrier/scheduling integrations, or cloud failover.
- Photo/ASR model quality: those have separate media controls and are outside this
  authored text-case semantic run.

See [runbook](../../case-model-e2e.md) for key configuration, execution and interpretation.
