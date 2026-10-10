# Independent code review

Scope: coordination review backend, Team controls, Customer acceptance/readback, and related contracts/tests, based on commit `87f34a3`. Unrelated dirty provider changes were excluded.

Initial material findings and resolution:

1. Model evidence field mismatch (`evidence_refs` versus canonical `evidence_event_ids`). Corrected and covered by tests.
2. Team lost the original idempotency key after successful POST and failed follow-up GET. Controller now preserves/restores the identical key and body. Regression test verifies replay behavior.
3. Customer accepted an older post-save GET as current. Readback now checks saved receipt revision/hash and later matching audit history; cached receipt is distinguished from verified current state.
4. Customer status refresh did not enter a coordination workflow initialized after first load. Shared refresh path now detects and switches; independent browser reproduction passes with GETs only.
5. Model context resolution borrowed a second case-store connection while holding the write transaction. A dedicated persisted-job resolver avoids pool starvation; source validation still happens against the locked snapshot. The one-connection real HTTP regression failed before the fix and passed afterward.

Final reviewer verdict: approved within scope; no residual P1/P2 findings. The last scoped review ran 32 PostgreSQL/HTTP tests, 20 JavaScript tests and the Team browser regression, including the single-connection pool fix.

Declined-to-judge areas: unrelated provider/OpenSpec edits; live model quality or paid inference; production deployment; authentic customer identity/consent; real carrier effects; physical delivery; final archival/commit completeness. These exclusions remain explicit limitations, not implied passes.
