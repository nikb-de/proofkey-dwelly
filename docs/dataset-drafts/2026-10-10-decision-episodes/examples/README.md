# Example index

All files are original synthetic development examples. Labels are assistant-authored drafts, not adjudicated truth. Input links are the only files a proposer should receive; labels, this index and simulator files belong to the evaluator.

| ID / input | Stage | Coverage | Private reference |
|---|---|---|---|
| [d001](agent_inputs/d001.json) | intake | missing_attachment, intake, claim_vs_evidence | [label](private_labels/d001.json) |
| [d002](agent_inputs/d002.json) | decide | missing_attachment, minimal_question, no_unnecessary_escalation | [label](private_labels/d002.json) |
| [d003](agent_inputs/d003.json) | decide | unreadable_attachment, artifact_state | [label](private_labels/d003.json) |
| [d004](agent_inputs/d004.json) | resume | resume, evidence_arrival, no_repeated_question | [label](private_labels/d004.json) |
| [d005](agent_inputs/d005.json) | decide | sufficient_evidence, hitl, authority_gap | [label](private_labels/d005.json) |
| [d006](agent_inputs/d006.json) | authorize | gate_block, missing_approval | [label](private_labels/d006.json) |
| [d007](agent_inputs/d007.json) | authorize | gate_allow, valid_approval, positive_control | [label](private_labels/d007.json) |
| [d008](agent_inputs/d008.json) | authorize | stale_approval, changed_amount, revision_binding | [label](private_labels/d008.json) |
| [d009](agent_inputs/d009.json) | decide | rescheduling, customer_choice, no_unnecessary_escalation | [label](private_labels/d009.json) |
| [d010](agent_inputs/d010.json) | decide | refusal, no_inferred_cancellation | [label](private_labels/d010.json) |
| [d011](agent_inputs/d011.json) | authorize | hotl, gate_allow, positive_control | [label](private_labels/d011.json) |
| [d012](agent_inputs/d012.json) | execute | execute, bounded_effect, hotl | [label](private_labels/d012.json) |
| [d013](agent_inputs/d013.json) | verify | accepted_not_completed, verify | [label](private_labels/d013.json) |
| [d014](agent_inputs/d014.json) | resume | crash_recovery, unknown_outcome, no_duplicate | [label](private_labels/d014.json) |
| [d015](agent_inputs/d015.json) | verify | verified_completion, positive_control, verify | [label](private_labels/d015.json) |
| [d016](agent_inputs/d016.json) | decide | inline_evidence, no_attachment_needed, positive_control, hitl | [label](private_labels/d016.json) |
| [d017](agent_inputs/d017.json) | decide | missing_receipt, correct_information_owner | [label](private_labels/d017.json) |
| [d018](agent_inputs/d018.json) | decide | conflicting_evidence, no_invented_explanation | [label](private_labels/d018.json) |
| [d019](agent_inputs/d019.json) | resume | timeout, nonresponse, escalation | [label](private_labels/d019.json) |

The manifest binds exact bytes and families. Simulator files describe seven hypothetical episodes; no replay runner is included. For the timeout example d019, the snapshot advances to 11 October so that a full 24 hours has elapsed after the request described in d017.

Useful contrasts: d002 vs d016 (missing file/content vs sufficient inline evidence), d006 vs d007 vs d008 (missing, valid, stale approval), d013 vs d015 (accepted vs authoritatively applied), d009 vs d010 (selection needed vs options refused).

## Separate draft

[case-001-terms.json](case-001-terms.json) is a full case in `case-step-viewer/1.0`, not one of the decision snapshots above. Для Ника.
