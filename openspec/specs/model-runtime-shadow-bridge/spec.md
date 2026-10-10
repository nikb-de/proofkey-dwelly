# model-runtime-shadow-bridge Specification

## Purpose
Preserve provenance when associating completed local model results with optional trusted runtime state, without granting authority or performing operational effects.

## Requirements
### Requirement: Completed drafts retain their source identity

The bridge SHALL accept only validated completed draft artifacts from a configured service-owned artifact root and SHALL bind each record to source job/case, exact snapshot, proposal and receipt hashes. For a provider result it SHALL verify the saved job/spec, producer request, response receipt and parsed proposal form one linked attempt for that snapshot; independently valid but unrelated files SHALL be rejected. Unsupported or missing producer linkage SHALL remain rejected rather than be manufactured. It SHALL preserve original processing provenance and distinguish historical import from a fresh invocation. It SHALL NOT convert a contact draft to an executable runtime operation.

An offline baseline SHALL use an explicitly identified deterministic-baseline record binding the snapshot, the current verifying baseline implementation hash and proposal hash. The bridge SHALL independently reproduce the baseline proposal and SHALL NOT claim that the verifying implementation hash proves the original generation version. It SHALL NOT fabricate a provider receipt, observed model or actual-processing status.

#### Scenario: Previous live output is imported
- **WHEN** a saved live-provider draft is imported
- **THEN** the record preserves its original provider provenance and identifies the current operation as historical readback, not a fresh actual runtime invocation

#### Scenario: Source content differs
- **WHEN** the proposal, snapshot, receipt or citation does not match the supplied source identity
- **THEN** the bridge rejects the import without modifying runtime state

#### Scenario: Valid files belong to different attempts
- **WHEN** a receipt and proposal are each valid but are not linked to the same saved producer request and snapshot
- **THEN** the bridge rejects the import even if a caller supplies matching hashes of those unrelated files

### Requirement: Runtime bindings come from the trusted host

The bridge SHALL obtain target case, object, principal, request, request/consent revisions, generation, profile/process/policy versions and checkpoint identity through a configured read-only host resolver, not caller-authored mapping JSON. The resolver SHALL verify caller scope and compare the binding against the current persisted host state without invoking workflow execution. The record SHALL retain the observed state identity and check time; this is a point-in-time association, not ongoing authorization. Missing resolvers and mappings SHALL produce `unmapped`; stale or mismatched bindings SHALL be rejected. Conversation labels, model output and judge scores SHALL NOT establish identity, consent or authority. Citations SHALL remain scoped to the exact source case and snapshot.

#### Scenario: No authenticated mapping exists
- **WHEN** a model draft names a recipient but the host has no valid target mapping
- **THEN** the result is `unmapped` and the recipient name is not promoted to a runtime principal

#### Scenario: Host generation changed
- **WHEN** the read-only resolver observes a different generation or checkpoint from the requested association
- **THEN** the bridge rejects the stale association without advancing the runtime

### Requirement: Shadow imports cannot act

The bridge SHALL return only `shadow_recorded`, `unmapped` or `rejected` with stable reasons. It SHALL NOT call model providers, run workflows, invoke prepared consumers, create effect intents, dispatch adapters or modify runtime checkpoints, budgets, ownership or consent. `shadow_recorded` SHALL NOT imply policy approval or correctness.

#### Scenario: Draft requests a reschedule or refund
- **WHEN** a valid draft discusses a business operation
- **THEN** import records the suggestion only and no operation, message or financial effect is performed

### Requirement: Import is bounded and idempotent

The bridge SHALL apply finite input limits and use safe read-only access to source artifacts. It SHALL persist its own bounded shadow record atomically under a stable import identity and target binding. Repeated identical input SHALL return the same record; conflicting content under an existing identity SHALL fail. Stored records SHALL NOT contain provider secrets or unrestricted copies of original media.

#### Scenario: Retry after an interrupted response
- **WHEN** an identical import is repeated after its record was committed
- **THEN** the same record is returned with no provider call or duplicate runtime activity

#### Scenario: Input path escapes the declared artifact root
- **WHEN** traversal, a symlink escape or an oversized source is supplied
- **THEN** the bridge rejects the input before reading outside the authorized boundary
