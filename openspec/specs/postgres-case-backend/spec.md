# postgres-case-backend Specification

## Purpose
TBD - created by archiving change postgres-case-backend. Update Purpose after archive.
## Requirements
### Requirement: Preserve the case contract on PostgreSQL
The PostgreSQL store SHALL return the same v1 snapshots and public errors as the local CaseStore and SHALL preserve immutable history, idempotency and optimistic revisions across processes.

#### Scenario: Concurrent append at one revision
- **WHEN** two independent connections append different events at the same expected revision
- **THEN** exactly one succeeds and the other receives `revision_conflict`, with one new snapshot and one analysis intent

#### Scenario: Retry after restart
- **WHEN** the service restarts and an identical request is retried with its original key
- **THEN** the original snapshot is returned and no duplicate revision or intent is created

### Requirement: Transactional analysis intent
The store SHALL atomically persist each new snapshot and one corresponding pending analysis intent, and SHALL fence completion by lease token and database-time expiry.

#### Scenario: Write failure
- **WHEN** inserting the outbox record fails
- **THEN** no head, snapshot or idempotency change commits

#### Scenario: Expired worker
- **WHEN** another worker reclaims an expired lease
- **THEN** the old token cannot acknowledge the job and the new token can

### Requirement: Explicit bounded deployment
The case API SHALL require explicit schema migrations and a bounded connection pool, expose no model/execution endpoints, and reject unauthenticated case requests and untrusted browser origins.

#### Scenario: Local Compose use
- **WHEN** the documented local setup and smoke are run
- **THEN** cases persist across API restart in PostgreSQL without a paid service or provider call

#### Scenario: Existing dataset use
- **WHEN** the existing training/evaluation kit is validated after this change
- **THEN** no canonical JSON schema or dataset file must change

### Requirement: Pinned model-input export
The dataset adapter SHALL export only an explicitly selected revision matching its expected hash, SHALL reject included events after the supplied occurrence-time cutoff, and SHALL exclude evaluation metadata and lease secrets. A file export SHALL not overwrite an existing file and SHALL create private output.

#### Scenario: Export after a later event
- **WHEN** revision two exists but revision one and its expected hash are requested
- **THEN** only revision one's content is exported in the unchanged decision-input schema

#### Scenario: Read without job recovery
- **WHEN** the export adapter reads a previously owned SQLite store or the CLI reads PostgreSQL
- **THEN** benchmark running jobs are not recovered or changed by the export operation
