## Why

ProofKey currently accepts trusted structured replay requests, not Dwelly's public case folders. We need an honest, reproducible bridge from those folders to next-action assessment without leaking their completed histories into the decision.

## What Changes

- Add a standalone, standard-library offline tool under `tools/dwelly_cases`, outside the registered runtime package.
- Import all 50 Delivery & Logistics cases, preserving raw sources and hashes while separating pre-action snapshots from reference actions and later evidence.
- Run a source-cited, deterministic next-action baseline and report routing agreement separately from semantic correctness.
- Publish a provisional evaluation ledger, controls, limitations and reproduction commands. No live calls, operational effects or source-data publication.

## Capabilities

### New Capabilities

- `dwelly-case-intake`: Bounded source parsing, temporal isolation, offline next-action proposals and honest assessment artifacts.

### Modified Capabilities

None. Existing runtime registration, package inventory, authority and payment behavior remain unchanged.

## Impact

New standalone tooling, tests and documentation only, plus a README link. Raw public examples remain local output artifacts. No dependencies, runtime modules, database changes, external services or new execution authority.
