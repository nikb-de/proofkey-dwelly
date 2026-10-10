# Case model E2E report

Status: unavailable (exit 2)
Mode: live. live mode requested; execution evidence depends on status and receipts; authored expectations unvalidated; no held-out accuracy claim
Requested profile: openai-gpt-4-1-mini

| Source | Cutoff | Status | Error |
|---|---:|---|---|
| case-002-n4 | 6 | succeeded |  |
| case-002 | 5 | unavailable | model_output_unavailable |
| case-002-n4 | 5 | not_run |  |

Semantic and operational counts (separate):
```json
{
  "mode": "live",
  "record_count": 3,
  "unavailable_count": 2,
  "semantic_qualification": "author_labels_unvalidated",
  "coverage_qualification": "development_only_one_logistics_family_plus_ui_control",
  "semantic": {
    "pass": 8,
    "fail": 0,
    "not_run": 16
  },
  "operational": {
    "pass": 49,
    "fail": 1,
    "not_run": 4
  }
}
```

Source families and author expectations are not independent held-out accuracy evidence.
