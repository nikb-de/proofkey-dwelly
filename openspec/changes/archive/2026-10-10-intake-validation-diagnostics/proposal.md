## Why

The local intake form reports only `Invalid case payload` for a failed create, preventing recovery. A source-level reproduction also shows that valid plain records from another JavaScript realm are rejected by prototype identity; the exact cause of the user's embedded-browser failure remains unconfirmed.

## What Changes

- Accept plain data records across JavaScript realms without accepting arrays or class instances.
- Report the invalid declaration field or participant rule without disclosing submitted values.
- Add regression tests for the reported declaration, foreign-realm declarations/events, and retained validation boundaries.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `local-case-workbench`: portable record validation and actionable create errors.

## Impact

Only browser-local validation and its tests. No backend schema, persistence migration, operational authority, network access, or attachment limits change.
