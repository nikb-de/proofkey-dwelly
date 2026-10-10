# official-answer-assessment Specification

## Purpose
TBD - created by archiving change posthoc-official-answer-assessment. Update Purpose after archive.
## Requirements
### Requirement: Original answer preservation
Post-hoc review SHALL bind each assessment to the original published input,
answer and reasoning hashes and SHALL NOT modify the original official output.

#### Scenario: An original model output is unavailable
- **WHEN** a case has no accepted model decision
- **THEN** the report retains that failure as unassessable
- **AND** no reviewer invents a replacement answer or treats absence as accuracy.

### Requirement: Bounded independent review
Each case SHALL be reviewed through three explicitly identified current API
profiles using the existing eight rubric anchors, with no other judge's output
or producer identity in the review payload. The campaign SHALL cap reservation
at USD 25 per provider/model and SHALL NOT retry ambiguous dispatches.

#### Scenario: Judge calls fail or disagree
- **WHEN** a judge response is missing, invalid or disagrees with another judge
- **THEN** the report preserves the individual evidence and distinguishes it
  from a verified operational failure or organiser grade.

### Requirement: Assessment limitations
The report SHALL disclose that whole-answer framing differs from the earlier
action-only reliability pilot and has not been validated against human labels.

#### Scenario: Scores are summarized
- **WHEN** provisional scores or flags are aggregated
- **THEN** denominators, abstentions and disagreement remain visible
- **AND** no majority vote or average silently authorizes a corrected answer.
