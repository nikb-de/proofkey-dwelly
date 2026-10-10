# reality-test-execution Specification

## Purpose
TBD - created by archiving change official-reality-test-run. Update Purpose after archive.
## Requirements
### Requirement: Frozen official inputs and actual model outputs
The runner SHALL preserve the official source revision, original files,
extraction provenance, decision-time input, exact prompt and configuration,
provider responses and failures. It SHALL NOT tune prompts on official cases.

#### Scenario: Official case produces a candidate or error
- **WHEN** an official case is run
- **THEN** its original result is retained without manual answer correction
- **AND** proposed actions are distinguished from executed business effects.

### Requirement: Organiser answer layout
Every supplied case SHALL receive `ANSWERS/<official-id>/ANSWER.md` and
`REASONING.md`, including cases with failed or unavailable output.

#### Scenario: Batch is incomplete
- **WHEN** a call fails or never starts
- **THEN** its case remains visible with the actual error or missing status
- **AND** the exporter does not invent a successful decision or rationale.

### Requirement: Separate bounded judge reliability pilot
Calibration SHALL use development controls, preserve identical candidate bytes
across repetitions and keep coverage, errors, abstention and score variation
separate. Each experiment SHALL enforce at most USD 25 per provider/model,
retain pre-dispatch intents and avoid automatic retries.

#### Scenario: A judge is unavailable or unstable
- **WHEN** repeated ratings fail or disagree
- **THEN** the report retains that result and does not certify human calibration.
