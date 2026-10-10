# Inbound Communications Implementation Plan

**Goal:** email, chat, supplied call transcripts and recordings enter the existing platform through one safe, durable local ingress.
**Spec:** `openspec/changes/archive/2026-10-10-inbound-communication-channels/`; living contract `openspec/specs/inbound-communications/spec.md`.
**Global constraints:** no outbound/provider calls, no secrets logged/stored in receipts, unchanged canonical v1, no untrusted routing or authority, real PostgreSQL transactional tests, English UI, user drafts untouched.

### Task 1: Normalization
Own `tools/dwelly_channels/contracts.py`, `__init__.py`, `tests/test_contracts.py`. Tests first. Implement `load_config(value)` (dict or path), returning validated config dict; `normalize(envelope, channel)` returning `{events: [...], provenance: {...}}`. Draft events use `sender`, `recipients`, `occurred_at`, `kind`, `text`, `asset` (None or `{filename,mime_type,data:bytes}`). Preserve source claims; IDs derived by service. Raise `ValueError` with bounded known codes for invalid content. No DB or network. Use design limits. Strict unknown-field rejection. Export `MAX_ENVELOPE_BYTES`, `NORMALIZER_VERSION`. Validate MIME and offline media fully. Report red/green evidence.

### Task 2: Durable inbox
Own `tools/dwelly_channels/service.py`, `tests/test_service.py`, connection-aware refactors in `tools/dwelly_service/cases.py` and `tools/dwelly_platform/store.py`. Tests first with real PG. `migrate_channels(store)`; `ChannelService(store, config)`: `.capabilities()` -> safe connector list with configured routes/contacts counts, no secrets or raw addresses; `.list()` -> newest public receipt list; `.ingest(connector_id, envelope, source='operator_import')` -> public receipt; `.retry(receipt_id)` -> receipt; `.provenance(case_id)` -> public accepted receipts. Receipt fields `receipt_id,connector_id,delivery_id,channel,status,reason,case_id,event_ids,revision,raw_sha256,received_at,source,provenance`; statuses `accepted|quarantined`, accepted reason null. Strict ID+hash conflict; explicit retry only quarantined; bounds1024 receipts/128MiB retainedraw. Mapping must include all senders and recipients in declared participants, missing case -> quarantine. Atomic multi-event/assets append+outbox+receipt. Extract `_append(connection, case_id, key, body)` and `_put_asset(connection,...)` rather than nesting transactions; public existing methods keep behavior. Recognized failures quarantine with savepoints, unexpected errors roll back. No model/provider/effect calls. Report red/green evidence.

### Task 3: Transport and CLI (coordinator)
Own `tools/dwelly_channels/server.py`, `tests/test_server.py`, platform `server.py` and `__main__.py`. Add `--channel-config`, `--channel-port` (optional signed separate listener, default off). Operator endpoints GET `/api/platform/communications`, POST `/api/platform/communications/import` body `{connector_id,envelope}`, POST `/api/platform/communications/{receipt_id}/retry` body `{}`. Return `{receipt:...}` / GET `{connectors: [...],receipts:[...],provider_connections:false}`. Capabilities add `communications`, messaging mode local_ingress/provider_connectionsfalse. Case detail add `communications` provenance. Signed listener POST `/webhooks/{connector_id}` with `X-ProofKey-Timestamp`, `X-ProofKey-Signature` sha256hex; verify timestamp+'.'+raw before strict JSON. 40MiB body and no chunked/ambiguous headers. HMAC rejects before storage, no browser origins or cloud/nonloopback use.

### Task 4: UI
Own platform-ui files and browser test/fixture files only. Communications nav and section loadsGET, renders safe text statuses, config/provider boundaries, import normalized JSON or .eml with connector/conversation/delivery fields, explicit retry. Use `POST` marker/key and refresh cases after acceptance. Case provenance renders alongside existing evidence. No config editor/secret entry. All English; no innerHTML with user content. Fixture-driven real browser+PG E2E preferred, no paid calls. Server API from Task3. Report test evidence.

### Task 5: Integrate and verify
Cross-review task1/2/3/4, run focused and project regression, record limitations and actual receipts. Document copyable local setup and examples. Archive OpenSpec. No push/deploy.

## Rulings
- Continue autonomously under repeated user authorization; no new design-approval pause for this conservative local extension. Wrong assumption costs local rework, never external action.
- Parallelize independent ownership per explicit user request; reused available agent slots. Shared contracts are frozen here before dispatch. No worker commits or subdelegation.
- Keep live-provider auth and public deployment out of scope until provider/account is known. Cost: live traffic still needs a native provider adapter and production authentication review.
- Initial MIME imports plain text and images only; audio uses phone/chat envelopes. This resolves contradictory design wording without broadening the parser. Cost: emailed audio is quarantined until that format is explicitly added.
