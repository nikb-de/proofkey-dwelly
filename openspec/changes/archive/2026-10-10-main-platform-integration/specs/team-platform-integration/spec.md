## ADDED Requirements

### Requirement: Preserve both product surfaces
The integration SHALL preserve the team GitHub case library and the platform runtime without routing incompatible case envelopes through the same API server.

#### Scenario: Existing source files survive integration
- **WHEN** the integration is verified
- **THEN** all main-only files remain present and current authored case JSON files retain their original bytes.

### Requirement: Interpret current team cases
The platform SHALL expose pinned, namespaced current team cases alongside unchanged legacy fixtures. It SHALL validate copied recipients and limits, preserve relevant observed communication context, and never promote authored limits into execution authority.

An incoming message MAY identify the current actor as a primary recipient or an explicit copied recipient. Copied recipient IDs SHALL be strings referencing known actors. An empty copy list SHALL be valid. Messages not addressed or copied to the current actor SHALL NOT be classified as its incoming event.

#### Scenario: Team case selected for analysis
- **WHEN** a namespaced team case is selected
- **THEN** bounded visible evidence is available for analysis and hidden future/answer data remains excluded.

#### Scenario: Current expanded catalog
- **WHEN** the catalog loads the pinned main revision `4fa3f4d0196db82e0816909590d176b0eb0c4e5e`
- **THEN** it exposes 51 team documents with 286 cutoffs and preserves the legacy three documents with 16 cutoffs as a separate export group.

### Requirement: Verify integration without live effects
The integration SHALL pass local tests and scripted end-to-end flows before merge. Results SHALL distinguish scripted providers from live model validation.

#### Scenario: Offline integration verification
- **WHEN** verification runs
- **THEN** no paid provider call or production operational effect is issued.
