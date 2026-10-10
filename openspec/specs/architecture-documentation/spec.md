# architecture-documentation Specification

## Purpose
Keep architecture diagrams readable across document viewers while preserving editable sources, source integrity and explicit verification limits.
## Requirements
### Requirement: Stable architecture previews
Active architecture documentation SHALL display diagram labels without depending on the host viewer's Mermaid HTML-label font measurements.

#### Scenario: Viewer applies different typography
- **WHEN** the host document viewer changes surrounding font size or family
- **THEN** the diagram preview remains a fixed rendered image with intact label pixels

### Requirement: Editable and attributable diagram sources
Each active architecture preview SHALL link to its editable source and a standalone vector artifact, with source and asset hashes recorded in a render receipt.

#### Scenario: Reader needs to inspect or edit a diagram
- **WHEN** the reader follows the links below a preview
- **THEN** the corresponding SVG and Mermaid source are available without changing the displayed architecture semantics

### Requirement: Honest rendering verification
Architecture rendering evidence SHALL distinguish browser asset verification from direct inspection of a native document viewer.

#### Scenario: Native app cannot be automated
- **WHEN** the native viewer is unavailable to the verification surface
- **THEN** the receipt states that limitation and reports only the browser and asset checks actually performed
