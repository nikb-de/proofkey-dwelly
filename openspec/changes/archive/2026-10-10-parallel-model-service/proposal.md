## Why

The model package runs independent requests serially and exposes only a non-resumable experiment CLI. The team needs an asynchronous, inspectable service without confusing model suggestions with authorized business actions, plus an honest path to Google Cloud.

## What Changes

- Add bounded parallel provider calls, preserving deterministic admission and the proposal/reference barrier.
- Add proposal-only operation, cooperative cancellation, and a shared persistent local spend ledger.
- Add authenticated single-operator local HTTP jobs backed by SQLite and persistent POSIX storage.
- Prepare an offline Cloud Run Job template; refuse live cloud execution until external durable admission and dispatch storage exists.
- Document deterministic orchestration versus nondeterministic inference and the missing operational bridge.

## Capabilities

### New Capabilities
- `parallel-model-service`: Parallel model execution, durable local service admission and bounded cloud preparation.

### Modified Capabilities
None. The operational runtime and its business authority remain unchanged.

## Impact

Changes are restricted to model tooling, a new service package, deployment preparation, tests and documentation. No real logistics writes, cloud deployment, paid experiments, new native integrations or autonomous refunds are authorized by this change.
