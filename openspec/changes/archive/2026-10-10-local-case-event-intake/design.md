## Decisions confirmed by the user

Local pseudo API; JSON relationships; rescheduling first; one review owner; reanalysis after new information; photos, voice messages and call recordings in English; external media processing permitted; cloud configured through environment variables.

Training examples may suggest policy candidates. They do not establish customer identity, consent, operator authority, or a published policy. A reviewed policy version and runtime gate remain prerequisites to action. External-media permission is not a new unlimited spending authorization.

## This increment

Use the existing bearer-authenticated local HTTP service and its single-owner `JobStore`. Add `cases.py` for strict contracts and snapshot construction; `CaseStore` composes the existing store's connection context and ownership rather than opening another database owner. Its tables live in the same private database. Case writes never create queue jobs.

### Input contracts

`POST /v1/cases`, with `Idempotency-Key`:

```json
{"case_id":"demo-1","links":{"order_id":"order-1","customer_id":"customer-1","operator_id":"operator-1"},"participants":["customer-1","operator-1","courier-1"],"language":"en"}
```

`POST /v1/cases/demo-1/events`, with `Idempotency-Key`:

```json
{"expected_revision":0,"event":{"event_id":"event-1","occurred_at":"2026-10-10T10:00:00Z","channel":"chat","sender_id":"customer-1","recipient_ids":["operator-1"],"kind":"message","text":"Please move my delivery to tomorrow.","media":null}}
```

`GET /v1/cases/demo-1` returns current; `?revision=0` returns the immutable prior snapshot. Creation starts at revision 0. Each new event increments once. Same key and exact original body returns the original snapshot even after later revisions; changed key body conflicts. Event ID is unique within case; reuse under another key conflicts, preventing disguised duplicate appends. Revision comparison occurs in the same `BEGIN IMMEDIATE` transaction as append. Both concurrent writes with the same expected revision cannot succeed.

IDs match `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`. Links are exactly order/customer/operator; participants contain unique IDs including the distinct customer and operator. Sender and recipients must be declared participants; this validates consistency only, not authenticity. Creation/events use closed field sets and finite JSON. Timestamps require an aware ISO value; occurrence time is a source claim and does not control received order. Channels: `chat`, `email`, `phone`, `internal`. Message requires nonempty text and null media. `photo`, `voice_message`, `call_recording` require media metadata `{asset_id,sha256,mime_type,size_bytes}`; text may be null or a bounded source caption, not a fabricated transcript. PNG/JPEG photo max10MiB, MPEG/WAV/MP4/WebM audio max25MiB. No file paths, URLs, base64 or bytes accepted. English is caller-declared, not language detection.

Bounds: existing16KiB HTTP request, max256cases,128events/case,16participants,16recipients,4096characters/text. Current snapshot size bounded by these limits. Return explicit capacity errors without writes. Store also enforces request-size and recursive depth limits for direct calls. Returned snapshots include `schema_version`, `source_mode:local_fixture`, case/links/participants/language/revision/events, `previous_snapshot_hash` (null at0), `snapshot_hash`, `runtime_binding:null`, `needs_analysis:true`, `analysis_status:pending_not_started`, `authorization:unverified`, `operational_effects:0`. Hash canonical core including previous hash; response metadata is stable and non-authorizing.

Validate persisted snapshots on every read (closed shape, hash, event count/revision consistency and references); malformed storage fails closed with a sanitized storage error. Reopening preserves revisions/idempotency. No mutable approval or completed-analysis field exists to accidentally carry forward.

## Not included

- Analysis worker consumes only the existing fixed bundle. New cases remain pending; no new paid call.
- No actual media upload/extraction; metadata never becomes evidence that media was understood.
- No sandbox reschedule dispatch yet; next step is typed proposal + existing PolicyGate preview, then explicitly qualified simulated transport.
- No automatic policy activation, real customer authentication, cloud service, native integrations, money movement or customer messages.

## Follow-on sequence

1. Snapshot-to-analysis job contract, invalidation and stale-result rejection.
2. Typed reschedule/clarify/escalate proposals; reuse existing policy gate and exact consent/ownership checks.
3. Sandbox scheduling intent, idempotency and verified readback.
4. Actual English media extraction with source/derivative hashes and provider receipts; semantic evaluation.
5. Reviewed policy candidates and adaptable connector profiles; external durable cloud queue/storage later.
