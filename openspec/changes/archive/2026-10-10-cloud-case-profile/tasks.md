## 1. Case profile
- [x] 1.1 Add failing tests for marker/profile matrix, cloud hosts and retained auth guards.
- [x] 1.2 Implement isolated explicit profile without changing model/server guards.
- [x] 1.3 Run focused and related-source regression and independent review.

## 2. Release preparation
- [x] 2.1 Prepare private service/migration templates and release gates.
- [x] 2.2 Verify templates and AMD64 build locally.
- [x] 2.3 Record the initial credential block, subsequent successful checks and authorized private pilot acceptance; archive the completed configuration increment without claiming full-product readiness.

Local evidence is recorded in `deploy/cloud-run/case-release.md`: focused tests, independent source/template reviews and a source-matching Linux AMD64 image. The final related-source run passed 411 tests and 647 subtests. `docs/verification/cloud-case-pilot-2026-10-10.md` records live migration, IAM, database-role checks, five synthetic smoke runs, fresh-revision persistence, rollback and backup. No model worker, media processing or real operational integration is claimed.
