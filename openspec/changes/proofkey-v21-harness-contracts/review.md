# Written-design review receipt — 8 October 2026

Scope: active OpenSpec design/requirements/planning documents only. This is not the earlier named five-provider judge panel, an external certification, a runtime test or protected/blind evaluation. Three delegated agents performed independent targeted read-only reviews in this session; root verified and applied the accepted findings. Reviewers rechecked their fixes and reported no remaining blocking contradictions within their declared scopes. User written-design approval remains pending.

| Review seat | Scope | Accepted findings and resolution |
|---|---|---|
| connector_design_review | Core contracts, safety, dependency order and task/estimate consistency | Profile-appropriate offline evidence replaces an impossible native-sample prerequisite. Initial ProcessSpec contracts/enforcement precede consumers; adaptation changes an existing baseline. |
| multimodal_eval_design | Required media/model roles, readiness, timing and labels | All three AI roles are normative; positive batch includes a legitimate operator case. Baseline/resulting release hashes are separate. Label/rubric/lineage changes invalidate affected scores and require regrading. |
| dwelly_integration_research | Public-source grounding and native unknowns | Shared quota/concurrency/rate-limit behavior added. Bringg field ambiguity retained. Source locator ledger explicitly distinguishes authored live-read paraphrases from byte snapshots. |

## Root verification

- `OPENSPEC_TELEMETRY=0 /opt/homebrew/bin/openspec validate proofkey-v21-harness-contracts --strict`: successful after substantive review fixes. This checks OpenSpec structure, not runtime correctness.
- Primary readback covered revised design/tasks, requirements and supporting research/discovery/acceptance documents. Review scope and unfinished gates are explicit.
- Frozen v2.2 DOCX SHA-256 remains `42a6d0027e6fa914e394a7956b87c1ce0d251baf78a58f01e92a1232392bf314`.
- Frozen v2.2 ZIP SHA-256 remains `a5352b538d4f7da5eef1ccf821212bede95a1b69f1005bcb0a3c9eb739a3ba71`.
- No product source scaffold, dependency install, runtime/ASR/vision/planner execution, paid provider campaign, logistics connection, team/organizer message, publication or submission occurred in this revision. Active runtime requirements remain unimplemented/unarchived.

## Process used

Superpowers using-superpowers and brainstorming established the architectural written-design gate; dispatching-parallel-agents enabled the three independent reviews; receiving-code-review required checking findings before applying them; verification-before-completion required fresh structure/hash checks. The build-eval skill shaped provisional labels, grader qualification, versioned assessment evidence and non-cherry-picked timed denominators. The user's OpenSpec workflow places these specs under `openspec/`, not the Superpowers default spec directory. Detailed implementation planning begins only after written-design approval.
