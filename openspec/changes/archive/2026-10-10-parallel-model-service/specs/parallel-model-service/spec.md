## ADDED Requirements

### Requirement: Bounded parallel inference
The system SHALL run independent provider calls concurrently under validated global and per-provider limits while a single coordinator owns durable admission, output writes and result aggregation.

#### Scenario: Replies arrive out of order
- **WHEN** concurrent responses finish in a different order from input
- **THEN** persisted proposals and assessments retain stable case and seat identity, every call has one pre-dispatch reservation, and configured limits are not exceeded.

### Requirement: Inference is not authority
The system SHALL emit unsent proposals with zero business effects. Evaluation SHALL remain optional and all proposals SHALL be frozen before references are accessed.

#### Scenario: Proposal-only request
- **WHEN** the service accepts its default proposal job
- **THEN** no reference file is opened and no judge is called.

### Requirement: Persistent local admission
The local service SHALL authenticate requests, durably persist idempotent jobs, use fixed server-owned inputs, serialize active jobs, and share conservative budget reservations across jobs and restarts. Current startup live authorization SHALL be required before claiming any live job, including previously queued work.

#### Scenario: Restart without live authorization
- **WHEN** a prior live job remains queued and the service starts without live enablement
- **THEN** that job remains queued without provider dispatch, offline jobs can progress, and later explicitly enabled startup can claim the live job.

#### Scenario: Duplicate request
- **WHEN** the same idempotency key and body are submitted twice
- **THEN** one job is returned; a different body with the same key is rejected.

#### Scenario: Consume a result
- **WHEN** an authenticated client requests a job's proposals
- **THEN** the service returns bounded validated unsent drafts in stable case order without exposing raw provider responses or incomplete files.

#### Scenario: Queue or worker unavailable
- **WHEN** 256 jobs are pending or the worker has failed
- **THEN** the service rejects new admissions with a safe unavailable response, while an existing idempotent result remains retrievable at capacity.

#### Scenario: Process restart
- **WHEN** a service restarts with an unfinished running job
- **THEN** it reconciles terminal evidence or marks the job interrupted without automatically redispatching model calls.

### Requirement: Cancellation retains uncertainty
The system SHALL stop new calls on cancellation, retain all reservations, drain in-flight calls and preserve their results without promising reversal.

#### Scenario: Cancel with an in-flight call
- **WHEN** cancellation arrives after a request was sent
- **THEN** that call is not retried or refunded and later calls are not admitted.

### Requirement: Honest cloud preparation
The system SHALL provide offline Cloud Run Job preparation with retries disabled and SHALL NOT expose the local queue or paid model execution as a durable Cloud Run service.

#### Scenario: Managed cloud environment
- **WHEN** local service startup or live model CLI runs with Cloud Run environment markers
- **THEN** execution fails closed before any paid provider request.
