# Local case/event pseudo API

This is a local development input service, not a CRM integration or a production-authorized action path. It extends the existing model service: JSON in → immutable case revision → **analysis pending**. The fixed-bundle model worker is not automatically connected to these new cases.

## Configuration

An ignored private `.env` and tracked `.env.example` live at the repository root. The CLIs do not load dotenv automatically. Fill the private file locally, then load only that trusted file:

```sh
set -a
source ./.env
set +a
```

`PROOFKEY_SERVICE_TOKEN` is consumed by the local service. Provider keys are consumed only by explicitly enabled model calls. Fill or remove blank assignments before loading: they overwrite existing environment values and are not valid credentials. Cloud project, region, service name and identity are reserved configuration; no cloud deployment consumes them yet. Existing private credentials have not been copied into this file.

Start the service using the bundle/config/state flags in [the service guide](model-service.md#run-locally). Keep its default loopback bind and omit `--allow-live` for this demo. The same startup-fixed imported bundle is still required, even when only testing the new input routes.

## Create a local case

```sh
curl --fail-with-body http://127.0.0.1:8080/v1/cases \
  -H "Authorization: Bearer $PROOFKEY_SERVICE_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-create-1' \
  --data '{"case_id":"demo-1","links":{"order_id":"order-1","customer_id":"customer-1","operator_id":"operator-1"},"participants":["customer-1","operator-1","courier-1"],"language":"en"}'
```

These relationships are declared test input, not verified customer identity or authority. Initial revision is 0. One configured bearer token represents the local operator; it is not a multi-tenant identity system.

## Add information and inspect history

```sh
curl --fail-with-body http://127.0.0.1:8080/v1/cases/demo-1/events \
  -H "Authorization: Bearer $PROOFKEY_SERVICE_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-event-1' \
  --data '{"expected_revision":0,"event":{"event_id":"event-1","occurred_at":"2026-10-10T10:00:00Z","channel":"chat","sender_id":"customer-1","recipient_ids":["operator-1"],"kind":"message","text":"Please move my delivery to tomorrow.","media":null}}'

curl --fail-with-body http://127.0.0.1:8080/v1/cases/demo-1 \
  -H "Authorization: Bearer $PROOFKEY_SERVICE_TOKEN"

curl --fail-with-body 'http://127.0.0.1:8080/v1/cases/demo-1?revision=0' \
  -H "Authorization: Bearer $PROOFKEY_SERVICE_TOKEN"
```

Use the latest revision for the next append. Exact retries with the same key and body return the original snapshot, even after newer events. Changed retry bodies, stale revisions and duplicate event IDs under new keys conflict. Received order determines revisions; an event's source timestamp is not proof of arrival time.

The response contains an immutable snapshot hash and previous hash, `needs_analysis:true`, `analysis_status:pending_not_started`, `runtime_binding:null`, `authorization:unverified`, and `operational_effects:0`. This does not assert that the model ran, a delivery moved, or a customer consented.

## Media boundary

Kinds are `message`, `photo`, `voice_message`, `call_recording`. Photos accept PNG/JPEG metadata up to 10 MiB; audio accepts MPEG/WAV/MP4/WebM metadata up to 25 MiB. Media fields are `asset_id`, `sha256`, `mime_type`, `size_bytes`. The service does not fetch, upload, inspect or transcribe those bytes. English is an input declaration, not detected language. No URLs, local paths or inline bytes are accepted.

## Next steps and decisions

These are planned, not implemented by this intake increment:

1. Add a separate revision-analysis job type and transactional outbox. The existing worker processes its startup benchmark bundle; do not fabricate benchmark IDs or conversation stages to route local events through it. Keep job status outside immutable case snapshots.
2. Bind each analysis to `case_id`, `revision`, `snapshot_hash` and analysis configuration. Retain late results as historical if the case head advances; never publish an older answer as current. Intake-only mode remains the default until analysis is explicitly enabled.
3. Produce a typed, non-executing reschedule preview with evidence references, requested window, missing facts and approval requirements. Unknown slot availability, consent, identity or policy must stay unknown. A local scheduling fixture and explicit timezone are needed before normalizing dates such as “tomorrow”.
4. Only then connect a trusted sandbox host to the existing deterministic policy gate. Recheck the current revision, identity, consent, ownership and approved policy before an action; verify original-effect readback before reporting success. Process actual authorized English media through a bounded asset store with source hashes and extraction receipts, separately from metadata intake.

Training examples may generate policy candidates. The designated human owner approves a version before it becomes policy; neither examples nor LLM judges grant execution rights. No additional user decision is needed to keep developing the local stand. Real system credentials, actual policy approvals and cloud target remain future inputs.
