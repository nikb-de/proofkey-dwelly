# Inbound communications — local integration harness

## What is implemented

Email/MIME, chat messages, supplied phone transcripts and call recordings share a durable inbox and case event pipeline. These are **local adapters**, not connected Gmail, WhatsApp or telephony accounts. No outbound messages or calls are sent.

```text
Email .eml / chat JSON / transcript / recording bytes
                  │
       Operator import OR signed local webhook
                  │
        Durable inbox + source provenance
                  │
       Configured conversation/contact mappings
                  │
        ┌─────────┴──────────┐
        │                    │
    Quarantine       Offline content validation
        │                    │
 Explicit retry      Atomic PostgreSQL commit
 after config fix    events + assets + receipt + outbox
                             │
                 Existing case / state controls
                             │
              Explicit model / ASR / image controls
```

Incoming evidence creates a new case revision, making old analysis stale. It does **not** dispatch a model, automatically transcribe a recording, grant consent or perform a delivery/payment action.

## Start locally

Use the existing PostgreSQL setup and add the configuration argument:

```bash
PYTHONPATH=.:tools:runtime/src python -m tools.dwelly_platform serve \
  --port 8095 --schema proofkey_platform_local --migrate \
  --channel-config tools/dwelly_channels/examples/channels.local.json
```

`PROOFKEY_PLATFORM_DATABASE_URL` must already be configured privately. Open the **Communications** screen. Create `case-1` first, with order `order-1`, customer `customer`, operator `operator`, participants `customer` and `operator`, language `en`. Example files use those IDs. No signing secret is needed for same-origin operator imports.

1. Select `chat-demo` and import `examples/chat-message.json`.
2. Select `mail-demo`, `.eml` mode, conversation `thread-1`, unique delivery ID, and `examples/customer-email.eml`.
3. Select `phone-demo` and import `examples/phone-transcript.json`.
4. A recording uses `format: media` with `kind: call_recording`, matching caller/recipient mappings, MIME, filename and base64 file bytes. It is stored as evidence; run **ASR** separately through the existing case media controls.

Paths above are relative to `tools/dwelly_channels/`. Samples are synthetic, not Dwelly production records. Reimporting a delivery ID with identical content returns the same receipt; changing the content under the same ID rejects it.

## Signed pseudo-provider API

For another local service to push deliveries, supply signing secrets (at least 32 UTF-8 bytes each) through environment variables named in the config, then add `--channel-port 8096`. Do not commit secrets or paste them into chats. These are webhook signing secrets, **not** OpenAI/Claude/Gemini API keys.

POST the envelope JSON bytes to `http://127.0.0.1:8096/webhooks/chat-demo` with:

- `Content-Type: application/json`
- `X-ProofKey-Timestamp`: current Unix seconds, within five minutes
- `X-ProofKey-Signature`: lowercase hex HMAC-SHA256 of `timestamp + '.' + exact_request_bytes`, keyed with that connector's secret

The listener verifies raw request bytes before JSON parsing or storage. Invalid authentication is rejected, not placed in the ordinary inbox. It rejects browser origins, public binding and Cloud Run execution. This is **our harness signature protocol**, not a native vendor webhook signature.

Operator API (existing local trust boundary) requires `X-ProofKey-Request: platform-v1` and `Idempotency-Key` for writes:

| Method / path | Meaning |
| --- | --- |
| GET `/api/platform/communications` | Safe connector summary and receipts; no raw payloads or secrets |
| POST `/api/platform/communications/import` | `{connector_id, envelope}` |
| POST `/api/platform/communications/{receipt_id}/retry` | `{}`; explicitly retry quarantine with current mappings |
| GET `/api/platform/cases/{case_id}` | Existing detail plus `communications` provenance |

## Contracts and storage

Config uses `proofkey-channel-config-v1`; envelope uses `proofkey-inbound-v1`. Exact examples are versioned beside the implementation. `routes` bind external conversation IDs to existing cases; `contacts` bind external addresses/speakers to already-declared participants. A mapping or valid connector signature does **not** verify an email sender, caller identity or consent. Sender and timestamp remain claims supplied by the source.

Receipts retain the original envelope as private DB content. `raw_sha256` is the SHA-256 of the canonical JSON envelope, not the original HTTP wire representation. An email's original RFC822 bytes remain in its base64 payload. Supplied transcripts are marked unverified, distinct from ASR results.

`accepted` means atomic persistence, **not** correct resolution. `quarantined` means no case mutation. Unknown routing/contact, malformed MIME, unsupported media, capacity limits and missing cases are bounded reasons. Fix mapping configuration, restart with it, and explicitly retry. Conflict under an existing delivery identity requires investigation, not overwrite.

Limits: 40 MiB envelope, 26 MiB raw email, 32 MIME parts/depth 8, 16 attachments, 4,096 characters per message, 128 canonical events per case, 1,024 retained receipts and 128 MiB raw inbox content per schema. Images/audio use existing offline validators. The initial email parser supports plain text, image attachments and optional ignored HTML alternatives. Email audio attachments, HTML-only messages, nested email, archives and other unsupported attachments are rejected; no URL is fetched. Audio and recordings use phone/chat media envelopes.

## What remains before live deployment

Choose a real provider, configure its account and use its official signature/API adapter; add production ingress authentication, authorization/tenant isolation, secret manager, retention controls, rate limiting and observability. Incoming provider IDs must map explicitly; do not expose the trusted-local platform server publicly. Configure real provider signing secrets separately from model credentials. Outbound communication remains a separate permissioned feature.
