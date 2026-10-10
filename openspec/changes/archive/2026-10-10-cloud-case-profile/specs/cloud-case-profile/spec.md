## ADDED Requirements

### Requirement: Explicit isolated managed profile
The case service SHALL reject managed environments by default and SHALL admit only the explicitly configured cloud case profile for the appropriate serve or migrate command. Legacy model workers SHALL retain their guards.

#### Scenario: Default managed startup
- **WHEN** a managed-cloud marker is present without explicit cloud case profile
- **THEN** startup fails before database work

#### Scenario: Explicit profile
- **WHEN** the supported profile, exact allowed hosts and strong application token are supplied for serve
- **THEN** the service can start without removing Origin or bearer-token checks

### Requirement: Bounded private deployment preparation
Templates SHALL require IAM invocation, version-pinned secret references and image digest, bounded scaling and separate migration/runtime identities. Preparation SHALL not claim actual deployment or a hard financial cap.

#### Scenario: Invalid cloud credentials
- **WHEN** Google credentials fail refresh
- **THEN** release remains blocked and no cloud resource is created

### Requirement: Honest private pilot acceptance
An authorized live release SHALL preserve IAM and application authentication, record its immutable image and tested revision, and distinguish case persistence from model processing. External verification SHALL use actual application paths rather than provider-reserved health paths.

#### Scenario: Persistent case lifecycle
- **WHEN** a synthetic case is created and replayed through a fresh service revision
- **THEN** immutable history and idempotent results remain intact, and pending analysis intents are not reported as completed analysis
