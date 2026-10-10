# Evidence-bound public support documentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this documentation task and independent review.

**Goal:** Let an integrating engineer distinguish demonstrated paths from source-only, routed, pending and unsupported capabilities in one short table.

**Architecture:** Docs only. Primary table in runtime README, dated supersession addenda in retained historical docs. No behavior or new acceptance runner.

**Spec:** `openspec/changes/public-support-boundaries/specs/public-support-boundaries/spec.md` and its design. Discovery: `.superpowers/sdd/2026-10-10-observed-route-stop-v2/j08-support-docs-discovery.md`.

## Global constraints

- Own only `runtime/README.md`, `docs/verification/judge-remediation-2026-10-09/support-matrix.md` and `docs/verification/judge-remediation-2026-10-09/integration-discovery.md`. Controller owns register, verification report, OpenSpec and closure.
- No executable code, new examples, commands changed, runtime test reruns, installations, providers, publication or external writes.
- J13 `5bc38c8`: recorded 8/8 installed positions on CPython 3.12.14/macOS arm64; J06 `80e0d6f`: final 4/4 positives, 7/7 negatives, complete 16/20 and 34/35 historical attempt counts in its linked report. These are not new-source qualifications.
- Trace `7b4c6e2`: source only, unverified projection, dispatch unknown, original readback not observed, current files unchecked. Read its actual final report at edit time; do not predict pending regression completion.
- Registered v1 run-only. Stop-v2 stays "in development / not qualified" unless its separate final evidence exists; same-owner/source-only limitations remain even then. Do not promote recover/reply/restart or default API/installed v2.
- Six offline interfaces are not six native integrations or full port coverage. No money, physical receipt, operator acceptance, model/provider or human-onboarding proof.
- Preserve historical discovery bodies. Add dated notes; do not rewrite the past to match current code. No private authority paths/bodies copied into public docs.

### Task 1: Publish the compact evidence map

**Files:** the three owned documentation files above.

- [ ] Read the spec/design/discovery and the J13/J06/trace reports. Inspect only the relevant current CLI/API/package/port declarations needed to check wording.
- [ ] Add a README section after Start here with at most seven rows: fixed installed replay; trusted new cases; source trace; other command routing; registered v1 controls; stop-v2 pending; six offline interfaces. Columns: Path, evidenced scope, candidate/evidence, limits.
- [ ] Make this section the primary Start here integration link. Keep the long matrix as detailed dated audit. Replace ambiguous "current installed" wording with candidate-specific wording; retain historical baselines as historical or move them out of the short introduction.
- [ ] Add a 10 October dated preface to the matrix linking the README table and trace report. Correct the default-CLI versus explicitly configured CLI statement using current source. Preserve other historical source anchors and label them dated.
- [ ] Add only a dated J06 supersession to integration-discovery's introduction: trusted configured CLI/library now exists, default CLI and API do not auto-select it, v1 controls remain denied. Keep its prior findings unchanged.
- [ ] Verify every new relative Markdown link and section anchor resolves; check exact candidate IDs/counts and all seven boundaries above. Retain command/read sources and outcomes in `.superpowers/sdd/2026-10-10-public-support-boundaries/task-1-report.md`. `git diff --check` must pass. This is documentation validation, not a fresh runtime pass; TDD runtime RED/GREEN is not applicable because no behavior changes.
- [ ] Self-review only the owned diff, then commit only those three files. Independent reviewer must separately approve spec compliance and documentation quality before controller closure.

## Controller closure

Run independent exact-diff review and a read-only local-link/anchor checker; preserve any failed check before fixes. Write `docs/verification/2026-10-10-public-support-boundaries.md` with exact docs candidate, linked executable candidates, check results and omissions. Update J08 only, retain all other statuses and scores, validate/archive the child, and do not close combined task 4.5 unless J23/J24 are separately complete. No full runtime rerun is needed for this docs-only delta; any runtime change would invalidate that scope and require a new plan.
