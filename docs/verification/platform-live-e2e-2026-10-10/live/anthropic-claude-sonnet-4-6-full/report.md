# Case model E2E report

Status: failed (exit 1)
Mode: live. live mode requested; execution evidence depends on status and receipts; authored expectations unvalidated; no held-out accuracy claim
Requested profile: anthropic-claude-sonnet-4-6

| Source | Cutoff | Status | Error |
|---|---:|---|---|
| case-002 | 0 | failed |  |
| case-002 | 1 | succeeded |  |
| case-002 | 2 | failed |  |
| case-002 | 3 | succeeded |  |
| case-002 | 4 | failed |  |
| case-002 | 5 | succeeded |  |
| case-002-n4 | 0 | failed |  |
| case-002-n4 | 1 | succeeded |  |
| case-002-n4 | 2 | failed |  |
| case-002-n4 | 3 | succeeded |  |
| case-002-n4 | 4 | failed |  |
| case-002-n4 | 5 | failed |  |
| case-002-n4 | 6 | succeeded |  |
| case-002-n4 | 7 | succeeded |  |
| minimal | 0 | failed |  |
| minimal | 1 | succeeded |  |

Semantic and operational counts (separate):
```json
{
  "mode": "live",
  "record_count": 16,
  "unavailable_count": 0,
  "semantic_qualification": "author_labels_unvalidated",
  "coverage_qualification": "development_only_one_logistics_family_plus_ui_control",
  "semantic": {
    "pass": 113,
    "fail": 15,
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
