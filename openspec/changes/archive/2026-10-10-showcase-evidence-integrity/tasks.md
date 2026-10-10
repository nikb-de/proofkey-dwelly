## 1. Reproduce

- [x] 1.1 Add realistic offline capture fixtures and regressions for changed model input and future coordination.
- [x] 1.2 Observe the new regression tests failing before changing production code.

## 2. Validate

- [x] 2.1 Validate full model inputs and canonical snapshot hashes.
- [x] 2.2 Bind historical coordination and nested evidence/terms to their recorded cutoff.

## 3. Verify and archive

- [x] 3.1 Run focused tests and confirm both real bundles rebuild byte-identically without database/provider access.
- [x] 3.2 Validate and archive this change into the living specification.

## Verification evidence

- Initial red: `PYTHONPATH=.:tools:runtime/src /tmp/proofkey-postgres-tests-20261010/bin/python -m pytest -q tools/dwelly_platform/tests/test_showcase.py` produced 18 failed, 14 passed, 10 subtests passed. The failures were expected `ValueError not raised` assertions for inconsistent captures, before production edits.
- Follow-up red: the same command with `-k without_its_recorded_creation_cutoff` produced 1 failed, 19 deselected before requiring nested creation snapshots.
- Green: `PYTHONPATH=.:tools:runtime/src /tmp/proofkey-postgres-tests-20261010/bin/python -m pytest -q tools/dwelly_model/tests/test_providers.py tools/dwelly_model/tests/test_parallel.py tools/dwelly_model/tests/test_runner.py tools/dwelly_analysis/tests/test_model.py tools/dwelly_platform/tests/test_showcase.py tools/dwelly_platform/tests/test_video_assembly.py` produced 97 passed, 176 subtests passed.
- Both authoritative capture reports rebuilt to bytes identical to the existing assets: LLM 28,805 bytes, SHA-256 `0204b5ac3b1164bdb119e90fcc40d58706846c83d069af831aa4c7b60f6eeb36`; scripted 17,497 bytes, SHA-256 `f4df7cbb599799ac52fa220ac187f2ec55fbc59d4e310bfd95415e2e26c2201b`.
- No database or provider calls, capture regeneration, staging, commit or push occurred in this fix.
