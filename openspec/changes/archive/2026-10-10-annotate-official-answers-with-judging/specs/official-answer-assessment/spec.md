## MODIFIED Requirements

### Requirement: Original answer preservation
Post-hoc review SHALL bind each assessment to the original published input,
answer and reasoning hashes and SHALL NOT rewrite the original official output.
User-requested auxiliary annotations MAY be appended after the unchanged
original byte prefix, but SHALL be labelled post-hoc and not original output.

#### Scenario: An original model output is unavailable
- **WHEN** a case has no accepted model decision
- **THEN** the report retains that failure as unassessable
- **AND** no reviewer invents a replacement answer or treats absence as accuracy.

#### Scenario: Existing judgments are shown in case documents
- **WHEN** the user requests inline visibility of completed judgments
- **THEN** ANSWER.md and REASONING.md preserve their original byte prefixes
- **AND** append separately labelled receipt-backed observations and statuses
- **AND** leave candidate JSON, failed outputs, frozen copies and traces unchanged
- **AND** never present judge observations as the original model reasoning.
