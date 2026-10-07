## ADDED Requirements

### Requirement: Required evidence classes preserve processing status

The candidate SHALL accept structured/no-text records, free text, supplied transcripts, images/photos, documents and raw audio through explicitly declared initial formats and limits. It SHALL retain malformed, encrypted, unsupported, unavailable and failed states. Per class it SHALL distinguish intake-only, deterministic-processed, actual-provider-processed and recorded-replay. Required actual-processing readiness SHALL NOT be satisfied by file references, mock findings, supplied transcripts presented as ASR or replay presented as a fresh model call.

#### Scenario: Raw audio has no enabled transcription route
- **WHEN** actual audio bytes are present but no authorized processor is usable
- **THEN** audio remains explicitly unavailable for transcription, no transcript is fabricated and complete multimodal readiness remains unfinished

#### Scenario: PDF has only recorded extraction
- **WHEN** the route replays a recorded PDF extraction
- **THEN** the run reports recorded-replay and does not count it as actual PDF processing for that candidate

### Requirement: Evidence provenance and access accompany assertions

The evidence catalog SHALL bind originals to source, hash, MIME type, case, access scope, observation time and transformations. Extracted assertions SHALL reference available text spans, page/region or audio intervals without invented coordinates. Authorized operator packets SHALL retain relevant originals as well as extracts/conflicts/unknowns. Public derivatives SHALL record scoped redaction and lineage without claiming certified anonymization. Untrusted content SHALL NOT establish policy, identity, consent, process or permission.

#### Scenario: Transcript instructs the agent to ignore return policy
- **WHEN** a transcript contains policy-changing instructions
- **THEN** the instructions remain untrusted evidence and cannot modify the policy gate, adapter mapping or approved process

### Requirement: AI roles are bounded and provider neutral

The complete candidate SHALL support all three AI roles: evidence/intent extraction, bounded runtime step proposals and development adapter/process preparation. It SHALL expose provider-neutral extraction, transcription and planning protocols with provider/model/version/prompt/input identity, processing mode, latency/usage and output status. Actual declared model/coding-agent evidence SHALL be required for each role's readiness; replay/stubs SHALL leave actual-role readiness unfinished. A deterministic no-text path MAY operate without a model but SHALL NOT satisfy all-role readiness alone. Only deterministic authority/process/policy gates SHALL permit effect dispatch. Development proposals SHALL require tests and human review before activation. Provider access, privacy permissions and capped spend SHALL be verified before paid campaigns; subscriptions SHALL NOT be treated as API entitlement.

#### Scenario: Model proposes a financial action
- **WHEN** a planner proposes issuing a refund beyond the approved operation graph
- **THEN** the proposal is rejected without dispatch and the case may use only separately permitted operator routing

### Requirement: Common entry points share one action discipline

The implementation SHALL provide a Python library, CLI and thin loopback API with the same canonical schemas, authority checks, intent journal, budgets, verifier and output semantics. Local caller or HTTP authentication SHALL NOT replace scoped business-principal binding. Non-loopback deployment SHALL remain unsupported until explicitly designed and reviewed.

#### Scenario: API request lacks authenticated case authority
- **WHEN** a syntactically valid local request lacks authoritative customer/case binding
- **THEN** it cannot dispatch a business effect even if the HTTP request was accepted

### Requirement: Clean release distinguishes owned code and private evidence

Owned new runtime source SHALL use Apache-2.0 and retain dependency notices/terms. Private evidence, third-party archives, service/model terms and organizer material SHALL NOT be automatically relicensed or copied into a public source release. A clean reproduction SHALL disclose processor/replay/unavailable modes and remaining requirements.

#### Scenario: Release preparation encounters a private recording
- **WHEN** a private source recording is present in the historical workspace
- **THEN** it is excluded from automatic public release unless specific rights and scope are established, and safe synthetic fixtures do not masquerade as that original
