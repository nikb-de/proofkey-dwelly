# Case model E2E report

Status: unavailable (exit 2)
Mode: live. live mode requested; execution evidence depends on status and receipts; authored expectations unvalidated; no held-out accuracy claim
Requested profile: openai-gpt-4-1-mini

| Source | Cutoff | Status | Error |
|---|---:|---|---|
| case-002 | 0 | unavailable | model_output_unavailable |

Semantic and operational counts (separate):
```json
{
  "mode": "live",
  "record_count": 1,
  "unavailable_count": 1,
  "semantic_qualification": "author_labels_unvalidated",
  "coverage_qualification": "development_only_one_logistics_family_plus_ui_control",
  "semantic": {
    "pass": 0,
    "fail": 0,
    "not_run": 8
  },
  "operational": {
    "pass": 22,
    "fail": 1,
    "not_run": 0
  }
}
```

Source families and author expectations are not independent held-out accuracy evidence.
