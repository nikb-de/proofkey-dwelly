# Case model E2E report

Status: passed (exit 0)
Mode: simulated. fixture-only; zero live provider evidence
Requested profile: simulated-case-fixture

| Source | Cutoff | Status | Error |
|---|---:|---|---|
| case-002 | 0 | succeeded |  |
| case-002 | 1 | succeeded |  |
| case-002 | 2 | succeeded |  |
| case-002 | 3 | succeeded |  |
| case-002 | 4 | succeeded |  |
| case-002 | 5 | succeeded |  |
| case-002-n4 | 0 | succeeded |  |
| case-002-n4 | 1 | succeeded |  |
| case-002-n4 | 2 | succeeded |  |
| case-002-n4 | 3 | succeeded |  |
| case-002-n4 | 4 | succeeded |  |
| case-002-n4 | 5 | succeeded |  |
| case-002-n4 | 6 | succeeded |  |
| case-002-n4 | 7 | succeeded |  |
| minimal | 0 | succeeded |  |
| minimal | 1 | succeeded |  |

Semantic and operational counts (separate):
```json
{
  "mode": "simulated",
  "record_count": 16,
  "unavailable_count": 0,
  "semantic_qualification": "fixture_only_not_live_evidence",
  "coverage_qualification": "development_only_one_logistics_family_plus_ui_control",
  "semantic": {
    "pass": 128,
    "fail": 0,
    "not_run": 0
  },
  "operational": {
    "pass": 432,
    "fail": 0,
    "not_run": 0
  }
}
```

Source families and author expectations are not independent held-out accuracy evidence.
