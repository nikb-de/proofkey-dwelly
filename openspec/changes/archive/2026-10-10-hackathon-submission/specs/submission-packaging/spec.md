## ADDED Requirements

### Requirement: Canonical reproducible submission
The repository SHALL document setup, architecture, models, assumptions, limitations and next steps, and SHALL contain the team-supplied video with its verified duration and digest.

#### Scenario: Independent engineer opens the repository
- **WHEN** an engineer follows the README from a clean environment
- **THEN** the local product can be started without private model credentials and optional external services are explicitly identified.

### Requirement: Evidence-preserving answer packaging
The retained-record exporter SHALL preserve input identity, original bytes, retained output, failures and public rationale without inventing official challenge provenance or operational success.

#### Scenario: A retained attempt has no accepted output
- **WHEN** the record is exported
- **THEN** the answer retains its failure or no-output status and does not substitute a corrected answer.

### Requirement: Narrow recoverable cleanup
Submission cleanup SHALL preserve working source, dependency assets, contracts, datasets and real evaluation traces, including failures.

#### Scenario: Obsolete planning artifacts are removed
- **WHEN** the reviewed cleanup is applied
- **THEN** only the enumerated current-tree files are removed and their prior Git history remains recoverable.
