# Case model E2E report

Status: failed (exit 1)
Mode: live. live mode requested; execution evidence depends on status and receipts; authored expectations unvalidated; no held-out accuracy claim
Requested profile: gemini-2-5-flash

| Source | Cutoff | Status | Error |
|---|---:|---|---|
| case-002 | 0 | failed |  |
| case-002 | 1 | succeeded |  |
| case-002 | 2 | succeeded |  |
| case-002 | 3 | succeeded |  |
| case-002 | 4 | unavailable | incomplete_response |
| case-002 | 5 | not_run |  |
| case-002-n4 | 0 | not_run |  |
| case-002-n4 | 1 | not_run |  |
| case-002-n4 | 2 | not_run |  |
| case-002-n4 | 3 | not_run |  |
| case-002-n4 | 4 | not_run |  |
| case-002-n4 | 5 | not_run |  |
| case-002-n4 | 6 | not_run |  |
| case-002-n4 | 7 | not_run |  |
| minimal | 0 | not_run |  |
| minimal | 1 | not_run |  |

Semantic and operational counts (separate):
```json
{
  "mode": "live",
  "record_count": 16,
  "unavailable_count": 12,
  "semantic_qualification": "author_labels_unvalidated",
  "coverage_qualification": "development_only_one_logistics_family_plus_ui_control",
  "semantic": {
    "pass": 29,
    "fail": 3,
    "not_run": 96
  },
  "operational": {
    "pass": 117,
    "fail": 1,
    "not_run": 44
  }
}
```

Source families and author expectations are not independent held-out accuracy evidence.
