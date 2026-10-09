# Registered fresh-case host admission — implementation plan

> Required execution: Superpowers TDD + subagent-driven development. Root owns
> specification, review and commits; one author owns the four product/test paths.

**Goal:** join trusted B3 synthetic registration to the existing fixed runtime
without charging an existing case or importing fresh case debt before its actual
route/binding is durably sealed.

**Binding spec:** `openspec/changes/proofkey-v21-harness-contracts/registered-host-admission.md`.
**Base:** `1a9b209`, linked worktree `codex/proofkey-runtime`.
**Stack:** Python 3.12, stdlib unittest/SQLite, existing Pydantic/contracts.
**Limits:** local synthetic only; no dependencies, providers, network, user data
or historical evidence edits. Entire original Task13 and branch remain open.

## Task 1 — exact bridge, review and isolated resource ownership

Files: new `runtime/src/proofkey/host_admission.py`, modify
`runtime/src/proofkey/host.py`, new `runtime/tests/test_host_admission.py`.

1. Read binding and named public APIs (B3, host, retained images, execution).
2. Add literal failing tests using real fixed profiles and isolated temp roots:
   registration/grant mismatch and marked-root legacy denial. New API absence
   alone is not the desired final RED: where needed establish interfaces then
   show behavioral assertion failures before implementing branches.
3. Implement exact detached trusted bridge and finite synthetic review resolver;
   validate actual local pins/profile/fixture/resource/account identities.
4. Exclusive durable marker binds resource to composition, with new-root-only
   first adoption. Validate marker before reopening, fixed host denies marker.
5. Focused GREEN. Preserve original output; no sweeping formatting changes.

## Task 2 — durable prepared/sealed/observed admission

Files: same module/host/test plus modify `runtime/src/proofkey/gateway.py`.

1. Write RED behavior cases for early denial and seal-before-import, restart
   pending block, post-admission observation failure, and full real positive.
2. Implement bounded separately-owned claim store, exact wire validation,
   retained-image freshness check and caller-anchored operation timing.
3. Prepare outside engine scope; gateway guard before replay/journal scope;
   exact original/auth and predetermined attempt; B3 reserve/readback then claim
   seal/readback immediately before existing atomic admission. No engine/schema
   or accounting edits, no journal subclass.
4. After return capture images and observe route before observed claim. Keep
   pending states/debt/effects on every failed stage, including restarted host.
5. Add creator-owned lifecycle; inner owners close before outer writer lease.
   Preserve compatibility for ordinary factory and four positional resources.
6. Wire optional exact composition into HostDispatcher; only run supported in
   the new path. Retain ordinary unmarked behavior and existing CLI contract.

## Task 3 — qualification, review, integration

1. Focused negative/edge tests from binding acceptance list, then new module
   unittest discovery. Use existing qualified bundled interpreter with `-B`,
   `PYTHONPATH=runtime/src:runtime/tests`, `PYTHONDONTWRITEBYTECODE=1`.
2. Run full `runtime/tests` unittest discovery once on final code; report actual
   counts/errors, preserve raw output and no ignored failures. Failed candidate
   receives diagnosis/TDD correction, not a silently repaired receipt.
3. Author self-review/report (actual commands, RED/GREEN, files, caveats) at
   `.superpowers/sdd/2026-10-08-proofkey-runtime/task-13b4b-author-report.md`.
4. Root independent focused verification; nonauthor diff review for both
   compliance and quality. Original author handles review fixes and new tests.
5. Commit exact four code/test files only after green verification and review;
   root updates status with precise scope. Validate OpenSpec. Do not archive the
   entire unfinished change or claim Task13/branch/event complete.

Implementation may choose internal helper names/SQL layout, but must not weaken
the binding guarantees. Escalate a need for additional product paths, trust
inputs, runtime semantics or inability to meet cleanup/early-entry contract.
