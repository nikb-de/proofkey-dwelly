## 1. Approval and exact scope

- [x] 1.1 Inspect resource readers, package configuration, current/historical pins and local dependency availability without mutation.
- [x] 1.2 Prepare the bounded design and explicit verification criteria.
- [x] 1.3 Obtain design approval; record acquisition permission or offline-only choice. User “работай над фиксом”, 2026-10-09, in reply to linked design plus four-artifact acquisition request; approved scope retained in design.md.
- [x] 1.4 Write the implementation plan from this task list and independently review it before execution. Plan `docs/superpowers/plans/2026-10-09-installed-offline-resources.md`; independent GO after current-digest and exact-constructor corrections.

## 2. Test-first packaging repair

- [x] 2.1 Add failing explicit-inventory, package-relative and fail-closed regression checks; retain RED evidence. Three tests / fourteen expected RED failures.
- [x] 2.2 Include exact resources and schema, repair only built-in path selection and make focused tests pass. Three new and 169 existing focused tests passed.
- [x] 2.3 Refresh current factory registration under a new identity; prove historical vectors and registrations unchanged. `synthetic-factory-installed-resources-v1`; historical byte audit retained.
- [x] 2.4 Independently review scope, security boundaries and test quality; resolve verified findings. Task review Spec Compliant, Quality Approved, no findings.

## 3. Installed verification

- [x] 3.1 Stage exact local build/runtime artifacts, recording hashes and compatible target tags; acquire missing items only if approved. Twenty artifacts rehashed; sixteen cached and exactly four approved downloads.
- [x] 3.2 Build wheel and sdist, inspect contents and resource identities independently. Fixed-2 includes exact thirteen resources; sdist rebuild produced the identical wheel hash.
- [x] 3.3 Install outside checkout and execute console/module/library/API with isolated import paths and fresh state. Fixed-2 eight positions passed; 55 module origins checked.
- [x] 3.4 Verify both fixed synthetic effects, persisted state, exports and closure without inferring success from exit code alone. Fixed-2 original/journal/source/export/owner checks passed and 1,732 installed files unchanged.
- [x] 3.5 Run focused regressions, one frozen full suite and current factory qualification with raw receipts. Full 1,696/1,696 in 888.324s, 260 files/HEAD stable; same-code qualifier 37/37. README-only post-suite correction is byte-bridged, with fresh final installed 8/8.

## 4. Handoff and archival

- [x] 4.1 Update support/install docs with exact observed target and unresolved gates. Runtime README, verification report and support matrix retain target/authority/provider limits; no full-release or native claim.
- [x] 4.2 Obtain whole-change review and reconcile J13 evidence; keep J14 and all unrelated items open. Independent final technical approval: C0/I0/M0; 1,696 full tests, final 8/8 installed positions, source/artifact and retained-state joins checked. Administrative archive follows.
- [x] 4.3 Archive this child only after its requirements actually pass; leave parent changes open. Archived 2026-10-09 with all three added requirements applied to the living specification. CLI initially reported this self-referential archive task incomplete; it is checked only after observed archive success.
