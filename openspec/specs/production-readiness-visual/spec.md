# production-readiness-visual Specification

## Purpose
TBD - created by archiving change production-readiness-visual. Update Purpose after archive.
## Requirements
### Requirement: Evidence-backed architecture status
The architecture graphic SHALL distinguish locally connected components from separately implemented components and unimplemented production connections, and SHALL identify the source revision and the observed deployment status. A verified case-only pilot SHALL NOT imply a deployed complete product.

#### Scenario: Reading the analysis path
- **WHEN** a user follows the case API to its PostgreSQL outbox
- **THEN** the graphic states that an analysis consumer is not connected and does not imply completed model analysis

#### Scenario: Reading the verification numbers
- **WHEN** historical test counts are displayed
- **THEN** they are described as recorded verification at the source revision rather than fresh cloud validation

#### Scenario: Private case pilot accepted
- **WHEN** Cloud Run, Cloud SQL and the authenticated case lifecycle have passed live checks
- **THEN** only those observed cloud connections are marked live, with UI, model worker and real integrations still explicitly disconnected

### Requirement: Legible graphic and deployment boundary
The supplied graphic SHALL have non-clipped labels and a locally verified raster preview. The cloud handoff SHALL record credential failure without interpreting it as absent cloud resources or a deployed service.

#### Scenario: Cloud credentials cannot refresh
- **WHEN** inventory checks return invalid_grant
- **THEN** no resources are created, the inventory remains unknown, and the required reauthentication and project decisions are stated
