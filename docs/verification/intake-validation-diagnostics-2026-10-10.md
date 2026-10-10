# Local intake validation correction — 2026-10-10

## Report and scope

The user reported `Not saved: Invalid case payload. Your draft is retained.` in the Codex in-app browser on `design/right-ontime/prototype/intake.html`. Visible values were `tst`, `das`, `order-1`, `customer`, and `operator`, with no additional participants.

That exact declaration passes the original validator in one JavaScript realm. An otherwise identical declaration from a separate Node VM realm fails its strict `Object.prototype` identity comparison. This is a confirmed compatibility defect, but **not a confirmed root cause of the user's actual tab failure**: the UI normally builds its own local literal, and hidden whitespace or another environment difference remains possible.

## Changes and evidence

- Plain-record validation no longer relies on realm-local prototype identity; closed field sets, ID constraints, participant requirements, and rejection of arrays/class instances remain enforced.
- Create errors identify the field or participant rule, without echoing submitted values. The existing UI retains the draft on failure.
- Before the implementation, the expanded unit suite had 3 failures: foreign declarations, foreign events, and missing actionable diagnostics.
- Independent review found an inherited-field/comma-key collision and a non-enumerable-required-field collision. Failing regressions reproduced both; exact enumerable own-key membership now replaces comma-joined key comparison and mismatched property sets.
- After these corrections, `node --test tools/intake-model.test.mjs`: 10 passed, 0 failed.
- `python3 -m unittest discover -s contracts/v1 -p 'test*.py'`: 20 passed.
- `node --check assets/intake-model.js`: passed.
- `openspec validate intake-validation-diagnostics --strict`: passed before archival.
- Independent final code review: approved, no remaining in-scope P1/P2 findings; reviewer reran all 10 model tests and whitespace checks.

## Verification limit / manual acceptance

Browser tooling denied access to the actual `file://` tab because only HTTP(S) is permitted. No alternate browser, proxy, server, or raw browser protocol was used to bypass that denial. Existing browser suites were not rerun through such a workaround; earlier Chromium results are not evidence for this correction.

The user must reload the existing tab, submit the retained/re-entered values, and confirm that a saved case appears and survives reload. If creation still fails, the new field-specific message is the next diagnostic evidence. The original embedded-browser incident is **pending this confirmation**, not closed by unit-test success.

No database migration, deletion, backend write, provider call, network integration, or operational action was performed.
