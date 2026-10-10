# Main/platform integration

## Global constraints
Preserve main-only files and current authored case bytes. Preserve legacy source fixture hashes and IDs. No real provider calls, production deployment or operational effects. Keep GitHub-library and model-analysis API envelopes separate. Use apply_patch; no commits by workers during the pending merge.

Spec: openspec/changes/main-platform-integration/specs/team-platform-integration/spec.md.

## Task 1: Widget integration
Own only case-state-widget common conflict files (HANDOFF.md, README.md, app.js, index.html, package.json, schema.json, viewer.js), plus widget tests if needed. Preserve main GitHub catalog UI/server behavior and all tests; preserve hardened feature validation. Restore copy_to actor-reference checks and rendering and limits validation. Retain all feature test commands and main start command. Keep legacy examples accessible and link to platform only via explicit separate URL, never model API under the library server. Add regression tests first, run Node suite. Do not change source cases or server implementation without coordinator approval. Stage owned conflict resolutions. Report to .superpowers/sdd/2026-10-10-main-platform-integration/task-1-report.md.

## Task 2: Python team-case integration
Own tools/dwelly_analysis (including tests), tools/dwelly_bridge evidence projection as needed, and new datasets/team-widget-v1 manifest/docs. Keep existing datasets/case-state-widget-v1 manifest byte-for-byte and original three IDs/default cutoff behavior. Add pinned source cases case-state-widget/cases/001.json, 002.json, 002-N4.json under IDs team-001, team-002, team-002-n4, source commit da1d17b322bf18a2d522e1061cb02fe0729639cb. load_catalog exposes both groups; get_document accepts namespaced IDs. Validate copy_to list of known actor IDs and limits shape using main schema semantics. Carry copied recipient context and author limits into safe observed input only; do not leak future state or ground-truth labels, or treat limits as trusted policy. Ensure legacy default E2E selections remain unchanged. Add regression tests before implementation. Run relevant Python tests using /tmp/proofkey-postgres-tests-20261010/bin/python with PYTHONPATH=.:tools:runtime/src:runtime/tests. Do not commit. Report to .superpowers/sdd/2026-10-10-main-platform-integration/task-2-report.md.

Upstream addendum: main advanced to 4fa3f4d0196db82e0816909590d176b0eb0c4e5e during verification. Preserve and pin all 51 current team documents (286 cutoffs), retain first three namespaced IDs and append team-003 through team-050. Export selectors legacy/team/all yield 16/286/302 cutoffs. Incoming messages explicitly copied to our actor are valid; those addressed neither directly nor by copy remain invalid. Step lookup must revalidate its selected source without walking unrelated documents or caching mutable file content. Regression tests cover unrelated-source corruption, selected-source rejection and absent-case behavior.

## Task 3: Preserve remaining product surfaces
Coordinator resolves .gitignore, root/docs README, prototype app/index and model runner/CLI conflicts, retaining features from both sides. Inspect diffs explicitly; preserve current prototype intake links and feature concurrency controls. Record every intentional difference from main. Never modify old worktree drafts.

## Task 4: Verify and review
Run project Python suites, all widget/platform Node suites and scripted browser E2E on isolated PostgreSQL schemas. Compare main-only files and authored JSON hashes to main. Independently review resolved conflicts and integration behavior. Fix blocking findings, archive OpenSpec, commit the two-parent merge, fetch main again and only publish/merge if no unreviewed drift.
