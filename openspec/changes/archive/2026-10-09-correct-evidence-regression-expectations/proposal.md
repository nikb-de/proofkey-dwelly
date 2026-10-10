## Why

One baseline regression conflates a valid saved narrative with the malformed
artifact ID `unavailable-artifact`. Fresh original intake intentionally denies
the latter before processing; expecting both to be authorized is incorrect.

## What Changes

- Separate valid narrative/registered-original recovery coverage from denied
  malformed, missing and unauthorized artifact references.
- Assert no prepared consumer, processing attempt or effect in either path.
- Preserve runtime behavior and all original-intake access checks.

## Capabilities

### New Capabilities

- `evidence-regression-expectations`: accurate regression coverage of the existing
  intake and no-processor boundary.

### Modified Capabilities

None. This is a test-only correction of the existing fresh-intake contract.

## Impact

Only `runtime/tests/test_engine_processing.py` changes executable test code.
It does not fix or reclassify factory registration failures, qualify the
platform, or amend the frozen five-provider assessment.
