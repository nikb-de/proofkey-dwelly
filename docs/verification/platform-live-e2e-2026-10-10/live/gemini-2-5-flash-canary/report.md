# Case model E2E report

Status: failed (exit 1)
Mode: live. live mode requested; execution evidence depends on status and receipts; authored expectations unvalidated; no held-out accuracy claim
Requested profile: gemini-2-5-flash

| Source | Cutoff | Status | Error |
|---|---:|---|---|
| case-002 | 0 | failed |  |

Semantic and operational counts (separate):
```json
{
  "mode": "live",
  "record_count": 1,
  "unavailable_count": 0,
  "semantic_qualification": "author_labels_unvalidated",
  "coverage_qualification": "development_only_one_logistics_family_plus_ui_control",
  "semantic": {
    "pass": 5,
    "fail": 3,
    "not_run": 0
  },
  "operational": {
    "pass": 27,
    "fail": 0,
    "not_run": 0
  }
}
```

Source families and author expectations are not independent held-out accuracy evidence.
