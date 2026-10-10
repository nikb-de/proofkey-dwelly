# Freeze the team contract and add a case workbench

## Why

UI, end-to-end tests and training/evaluation work currently assume different identifiers, revisions and success states. The supplied Right onTime v4.1 prototype has six fixed scenarios, but no general case creation or real attachment-byte intake. The existing service stores immutable case JSON; it does not analyse new cases or receive media bytes.

## What Changes

- Publish a versioned contract pack for existing intake and explicitly proposed analysis/media/operation interfaces, with implemented-versus-target coverage.
- Freeze separate input, media, analysis and operation state machines, storage ownership, source hashes, stale-result handling and evaluator-only labels.
- Import the supplied v4.1 design without changing its brand or original simulation semantics.
- Add an English local case workbench with creation, message append, real bounded image/audio selection, hash/preview, browser persistence, removal and JSON export. Keep it labelled browser-local: no provider, booking or server upload is implied.

## Capabilities

### New Capabilities
- `team-backend-contract`: shared versioned states, data and API vocabulary for parallel consumers.
- `local-case-workbench`: a real browser-local input and attachment surface beside the existing simulator.

## Impact

No existing service API, runtime guard, policy or frozen package changes. Server media ingest, automatic analysis, BFF authentication and cloud storage remain specified target capabilities, not implementation claims. No remote publication or live provider calls.
