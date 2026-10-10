# Design

The existing coordination aggregate remains authoritative. Add optional paired `model_run_id` and `model_review_note` fields to non-initialization, non-local-acceptance commands. Resolve the run inside the transaction after idempotency replay and version checks. Require succeeded status, exact case/revision/hash/input binding, no reference labels, a validated candidate and evidence contained in the frozen snapshot. Persist compact provenance in the audit. Human-selected command fields and source evidence remain independently validated.

Use a dedicated persisted-job resolver without a nested case-store read. The coordination transaction already owns the canonical snapshot and performs full source validation; borrowing a second case connection would exhaust a one-connection or busy pool. Ordinary model GET retains its existing independent binding check.

Add `record_local_acceptance {offer_id, terms_hash, acknowledged:true}`. This is an operator-assisted local preview, not real customer authentication. Append a labelled local customer-message simulation and the consent audit in one database transaction; a failure rolls back both. The state may then become `ready_to_book`, but no booking is executed. Reject old offer IDs, stale snapshots and unacknowledged submissions.

Team uses a dedicated coordination card and existing PlatformSession mutation/reload mechanics. Customer uses a separate pure projection/session and preserves the old decision-based path for cases without coordination. Both show the complete slot, handover, attendance requirement and charge. No source/model prose is inserted as HTML. No render or polling causes a write. All display states are English. Display confirmed local booking separately from physical delivery.

Independent file ownership: backend agent owns coordination.py and new domain tests; Team agent owns app/index/product and new Team assets/tests; Customer agent owns customer files and new customer assets/tests; controller owns server routing, HTTP tests, specifications and integration.
