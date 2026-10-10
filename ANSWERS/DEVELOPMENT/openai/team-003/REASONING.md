# Public rationale and evidence — team-003

This file exposes only the recorded public evidence references, rationale, uncertainty and approval requirements. It does not reconstruct hidden model reasoning or correct the model's answer.

## Recorded public rationale

    {
      "evidence_event_ids": [
        "001",
        "002",
        "003",
        "004"
      ],
      "uncertainty": [
        "No confirmation yet from the driver about successful entry and handover.",
        "Recipient has released the gate but no driver confirmation after that."
      ]
    }

## Evidence limits

    {
      "evidence_class": "development",
      "input_file": "INPUT.json",
      "model_evaluation": {
        "accuracy_score": null,
        "input_hash": "af2292fc34533297116a5c91a5c255a4ac62d1da71ecede08d4774c347d3cc5e",
        "qualification": "mechanical_comparison_only",
        "schema_version": "proofkey-step-comparison-v1",
        "state_agreement": false,
        "wait_target_agreement": false
      },
      "note": "Comparisons are retained observations, not independent human calibration. Absent execution receipts do not prove completion.",
      "official_reality_test": false,
      "run_checks": [
        {
          "actual": true,
          "expected": "same terminal job",
          "name": "terminal_readback_unchanged",
          "status": "pass"
        },
        {
          "actual": true,
          "expected": "same terminal job; no new job",
          "name": "terminal_replay_unchanged",
          "status": "pass"
        },
        {
          "actual": "af2292fc34533297116a5c91a5c255a4ac62d1da71ecede08d4774c347d3cc5e",
          "expected": "af2292fc34533297116a5c91a5c255a4ac62d1da71ecede08d4774c347d3cc5e",
          "name": "bound_original_input",
          "status": "pass"
        },
        {
          "actual": true,
          "expected": "original unvalidated author reference",
          "name": "reference_binding",
          "status": "pass"
        },
        {
          "actual": [
            1,
            0
          ],
          "expected": [
            1,
            0
          ],
          "name": "one_dispatch_zero_retries",
          "status": "pass"
        },
        {
          "actual": 0,
          "expected": 0,
          "name": "zero_operational_effects",
          "status": "pass"
        },
        {
          "actual": [
            "001",
            "002",
            "003",
            "004"
          ],
          "expected": [
            "001",
            "002",
            "003",
            "004"
          ],
          "name": "visible_evidence",
          "status": "pass"
        },
        {
          "actual": "not_inferred",
          "expected": "not_inferred",
          "name": "physical_delivery_not_inferred",
          "status": "pass"
        }
      ],
      "source_record_file": "SOURCE_RECORD.json",
      "source_record_sha256": "84d0004ec4c4498b576372b2d99c8662e115accc6fab2fc6271f44405507f1e0"
    }
