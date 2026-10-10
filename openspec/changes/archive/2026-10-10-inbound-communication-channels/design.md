# Design

## Boundary and decisions
This is a local integration harness, not a claim of Gmail, WhatsApp or Twilio connectivity. A separate signed loopback webhook listener and same-origin operator import converge on one durable inbox. Existing platform authentication remains trusted-local-operator only; neither listener is production network ready.

Configuration `proofkey-channel-config-v1` contains connectors with `id`, `channel` (`email|chat|phone`), `secret_env`, `routes` (external conversation ID to existing case ID) and `contacts` (external identity to existing participant ID). No credentials are stored in config, receipts or UI. The route and contact mappings are operator configuration; content never chooses its own case or grants execution permission. A configured mapping is not sender identity verification.

Envelope `proofkey-inbound-v1` has exactly `schema_version`, `delivery_id`, `conversation_id`, `format`, `payload`. Formats: `message` and `transcript` payloads contain `sender`, `recipients`, `occurred_at`, `text`; `media` additionally replaces text with `kind`, `filename`, `mime_type`, `data_base64`; `email` contains only `raw_base64`. Transcripts are phone-only, raw email email-only; audio must be phone/chat, images email/chat. No URL retrieval. Identifiers are bounded strings, text is never truncated.

MIME only imports supported plain-text bodies and image attachments. Audio/recordings enter through phone/chat media envelopes; email audio attachments are currently unsupported. HTML-only, nested RFC822, archives, malformed encodings, oversized or ambiguous content fail closed into quarantine. Maximum envelope 40 MiB, raw email 26 MiB, 32 MIME parts, depth 8, 16 attachments, 4096 characters per message, 128 events per case. Media goes through existing signature and offline decoding validation before promotion; no ASR or image model is called.

Inbox receipts retain original envelope, raw hash, connector, normalization version, status/reason and resulting case/revision/event IDs. Public lists omit raw content. Unique `(connector_id, delivery_id)` deduplicates exact source identity/content, returning original receipt; changed content rejects with conflict. Unknown route/contact or invalid content is quarantined, and explicit retry after corrected trusted config re-evaluates it. A missing case is quarantined. Capacity is bounded to 1024 inbox receipts and 128 MiB retained raw per schema.

Promotion inserts validated assets, canonical events, snapshots, analysis-outbox entries and final receipt in one PostgreSQL transaction. Shared connection-aware append/asset helpers preserve existing validation/idempotency. Failure rolls back all partial case writes. Ingress only marks analysis stale/pending; it never dispatches an LLM or operational effect.

Signed listener verifies HMAC-SHA256 over `timestamp + '.' + raw_body`, five-minute timestamp window, constant-time comparison and configured secret of at least 32 bytes before JSON parsing or storage. It binds loopback, rejects browser Origin and nonlocal Host, and cannot run in Cloud Run. It is a generic harness protocol, not a native provider signature implementation.

## UI
Communications shows configured channels and provider-disconnected status, durable receipt statuses, bounded reasons, import JSON / .eml (explicit conversation and delivery IDs) and explicit quarantine retry. Accepted imports refresh cases. Case details show source provenance. Uploaded media remains unprocessed until an operator chooses existing controls.

## Exclusions
No automatic mailbox poll, SMS/WhatsApp login, public webhook deployment, outgoing email/message/call, identity proof, automatic ASR/model dispatch, or participant/case creation from untrusted content.
