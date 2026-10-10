# Team integration contract v1 and local workbench

## Intent and authority

The user needs teammates to build UI, E2E and training/evals concurrently against the same contract, and explicitly requested review and completion of the supplied design's upload flow. Existing autonomous-work instructions are retained; this written design records the scope rather than adding another approval pause. It does not authorize deploying, publishing, paying providers or applying business actions.

## Design choice

Choose an additive versioned contract pack plus a separate local workbench. Do not retrofit arbitrary cases into the six scenario-specific simulator states or fabricate benchmark identifiers. Do not weaken the existing bearer/Origin boundary to make browser calls appear integrated. A full BFF, cloud object store and revision-analysis worker are subsequent implementations of the frozen target interfaces.

## Four independent lifecycles

1. **Case input, implemented:** absent → revision 0 on create; revision N → N+1 on valid append. Exact idempotent retries retain the original revision. Append order is the committed order; source timestamps never reorder history. There is no generic resolved case status in this input record.
2. **Media:** local selection → validating → ready or rejected/failed. Removing an unsubmitted selection deletes its browser-held bytes. A committed evidence reference is immutable; removal from a new draft cannot rewrite old snapshots. Extraction is separate: not_started/queued/running/completed/failed/unavailable. Stored bytes never imply model inspection.
3. **Analysis, target:** queued/running/completed/failed/cancelled/interrupted. Freshness is separately current/superseded against case ID, revision and snapshot hash. New revisions require an atomic analysis outbox when enabled; immutable input snapshots are never rewritten to show job progress. The current fixed-bundle worker remains separate.
4. **Operation, target integration:** draft/blocked/awaiting_approval/approved/rejected/superseded/dispatching/acknowledged/outcome_unknown/verified/proven_not_executed/unresolved. Acknowledged is not verified. New information before dispatch invalidates stale approval; after dispatch it never erases the original intent or permits blind retry. Only trusted identity, consent, owner and approved policy can authorize rescheduling.

## Storage and ownership

- Current local backend: CaseStore composes the service-owned private SQLite connection. case_heads, case_snapshots and case_requests hold exact canonical snapshots and retries. Existing jobs and their artifact directories remain independent.
- Workbench: a new versioned IndexedDB database stores browser-local cases, committed events and attachment Blobs. It is a local development adapter, not an authenticated CRM or shared backend. Do not reuse or reset the original simulator's localStorage key.
- Target backend: private blob storage is separate from relational metadata. Asset IDs are server-issued; server hashes, byte counts and MIME validation establish stored-byte identity. Never accept paths/URLs as fetch authority. Cloud deployments require durable relational/object-store adapters and explicit authentication; SQLite on ephemeral Cloud Run disk is not an approved deployment.
- Evaluations: decision inputs reference exact source revision/hash and only evidence visible then. Episode graph, labels and future events are evaluator-only records. Human-review status and provider identity remain explicit.

## Contract pack

Store human-readable architecture/state/ownership guidance and machine-readable JSON Schema/OpenAPI under contracts/v1. Existing route definitions are marked implemented; missing list/media/analysis/operation routes are explicitly target/unsupported. Freeze existing identifiers and zero-based revisions. New contracts use their own schema versions rather than changing closed existing schemas. Include positive and negative fixtures and executable checks against real CaseStore validation where applicable.

## Workbench behavior

- Separate intake.html linked from the entry/team/customer navigation. Original six workflows, state key, assets and fixtures remain unchanged.
- Create a case with existing backend-compatible declaration fields. Add text, photo, voice-message or call-recording evidence with the existing participant and event fields.
- Accept PNG/JPEG up to 10 MiB; audio MPEG/WAV/MP4/WebM up to 25 MiB. Read real selected bytes, verify image decoding, compute SHA-256 and display preview/status. Treat filenames and content as untrusted; render names with textContent and do not inject HTML or execute uploaded documents.
- Preserve cases and committed bytes after reload through IndexedDB transactions. Bound total browser storage and present explicit failure/retry rather than fake success. Unsupported types, empty/oversized/corrupt files do not become ready evidence.
- Present pending analysis, unverified authority and zero operational effects. Export backend-compatible declaration/event payloads and a separately labelled local manifest; no upload request or model result is fabricated.
- Do not claim compatibility between simulator revision 1 and backend revision 0; those are separate state models.

## Verification

Contract checks cover identifier/revision parity, closed fields, case hashes, typed transitions, evaluator/input separation and fixture validation. Browser tests exercise create, append, actual photo preview, reload persistence, rejected file types/size/corrupt bytes, removal, escaped filenames, keyboard flow and small-screen layout. Re-run the three supplied prototype suites in an isolated copy so historical producer screenshots/receipts are not overwritten in the source tree. No provider, carrier or cloud calls.
