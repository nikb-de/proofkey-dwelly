# Delivery terms coordination v1

This API records a delivery-coordination workflow in the local PostgreSQL sandbox. It never sends cancellation or booking messages to a carrier. `booking_confirmed` means a local operator recorded a correlated readback; every aggregate retains `mode: "local_sandbox"`, `external_effects: 0`, and `physical_delivery: "not_confirmed"`.

## HTTP contract

| Method | Route | Successful response |
| --- | --- | --- |
| GET | `/api/platform/cases/{case_id}/coordination` | `200 {"coordination": null}` before initialization, otherwise the latest persisted aggregate |
| POST | `/api/platform/cases/{case_id}/coordination` | `200 {"coordination": {...}}`, including the accepted command's aggregate |
| GET | `/api/platform/cases/{case_id}` | `200 {"case": {...}}`, including the current canonical `snapshot`, coordination aggregate, and projected freshness |

An unknown case returns `404`. Use the existing same-origin platform boundary. POST requires `Content-Type: application/json`, `X-ProofKey-Request: platform-v1`, and `Idempotency-Key`. A missing request marker returns `403 missing_request_marker`; the marker is not an authentication credential. Keys contain 1–128 ASCII letters, digits, `.`, `_`, `:`, or `-`.

Every command has exactly these common fields plus the command-specific fields below, and optionally the paired advisory model fields described later:

```json
{
  "command": "request_booking",
  "expected_revision": 12,
  "snapshot_hash": "<current canonical snapshot hash>",
  "expected_workflow_version": 5,
  "offer_id": "<current offer ID>",
  "terms_hash": "<current offer terms hash>"
}
```

`expected_revision` and `expected_workflow_version` are integers, not booleans. Bind the first two preconditions to the current canonical case head and the third to the current coordination version. Workflow version is `0` before initialization; the first accepted command creates version `1`. Unknown fields, including clock overrides, are rejected. JSON bodies are limited to 16 KiB.

## Commands and transitions

`evidence_event_ids` always means a nonempty list of up to 128 unique existing event IDs. The complete canonical audit message must also fit within 4,096 characters; otherwise the command is rejected atomically with `400 coordination_audit_too_large`. Use a smaller relevant evidence set, not truncated or silently discarded evidence. Evidence must be a non-internal `message` addressed to the case's linked operator. Declared sender IDs and recipient routing are checked; they do not authenticate people or organizations.

| Command | Exact additional fields | Allowed phase → resulting phase | Evidence and binding |
| --- | --- | --- | --- |
| `initialize` | `dispatch_actor_id`, `original_booking` | Uninitialized → `booked` | Dispatch must be a declared participant distinct from the linked customer and operator. `original_booking` has exactly `booking_id` and `terms`; the ID is 1–64 letters, digits, `_`, or `-`, beginning with a letter or digit. |
| `request_cancellation` | `evidence_event_ids` | `booked` → `cancellation_pending` | Customer message; creates a local pending cancellation request. |
| `confirm_cancellation` | `request_id`, `evidence_event_ids` | `cancellation_pending` → `awaiting_terms` | Dispatch message received after the pending request's `created_revision`; exact current request ID in both command and message text. |
| `record_offer` | `terms`, `evidence_event_ids` | `awaiting_terms`, `awaiting_consent`, or `ready_to_book` → `awaiting_consent` | Dispatch message; creates a new offer ID and clears consent. Not allowed while booking is pending. |
| `record_consent` | `offer_id`, `terms_hash`, `evidence_event_ids` | `awaiting_consent` or `ready_to_book` → `ready_to_book` | Customer message received after the current offer's `created_revision`; binds the exact current offer ID and hash. |
| `record_local_acceptance` | `offer_id`, `terms_hash`, `acknowledged: true` | `awaiting_consent` → `ready_to_book` | Operator-assisted local preview only: atomically creates explicitly simulated customer evidence and the consent audit. This is not authenticated customer consent. |
| `request_booking` | `offer_id`, `terms_hash` | `ready_to_book` → `booking_pending` | Requires current consent for the offer, no intervening canonical event since that consent's audit, and a still-future slot. Creates a local pending booking request. |
| `confirm_booking` | `request_id`, `terms_hash`, `evidence_event_ids` | `booking_pending` → `booking_confirmed` | New Dispatch message after the request's `created_revision`; exact request ID and pending terms hash in the command and message text. |
| `escalate` | `reason`, `evidence_event_ids` | Any initialized nonterminal phase → `escalated` | Nonblank reason of at most 2,048 characters; qualifying evidence addressed to the operator. |

`booking_confirmed` and `escalated` are terminal for this command set. Correlation tokens in confirmation text must be complete tokens, not substrings of larger identifiers. An old message with an old occurrence timestamp is ordered by its canonical receipt revision, not by a claimed timestamp. Evidence already consumed by an earlier workflow command cannot be reused for cancellation, offers, consent, or confirmations; escalation can refer back to existing evidence.

## Terms and consent

Every `terms` object has exactly this structure:

```json
{
  "slot_start": "2030-06-03T10:00:00+00:00",
  "slot_end": "2030-06-03T12:00:00+00:00",
  "handover": "recipient_only",
  "recipient_present": true,
  "charge": {"amount_minor": 0, "currency": null}
}
```

Dates are examples, not a clock override. Both timestamps must carry an offset. Duration must be positive and at most eight hours. New offers and booking requests must have a future start according to the database clock. Historical original-booking slots may be past, but remain subject to aware timestamps and the duration bound.

For offered terms, `handover` is `recipient_only` with `recipient_present: true`, or `concierge_allowed` with `recipient_present: false`. Here presence means required attendance, not observed physical presence. Charges require a nonnegative integer `amount_minor` (not a boolean). Positive amounts require a three-letter uppercase currency; zero may use a three-letter uppercase currency or `null` when the source states no charge without naming a currency.

Only `initialize.original_booking.terms` may retain unknown source facts as `handover: "unspecified"`, `recipient_present: null`, or `charge: {"amount_minor": null, "currency": null}`. Unknowns are not silently filled with assumed carrier terms. Known original values still obey the corresponding consistency rules.

The server computes `terms_hash` as SHA-256 of the complete canonical JSON terms object. Every `record_offer` creates a new `offer_id`, even for identical terms, and clears consent. Use the returned hash; do not omit charge or handover when identifying an offer. Consent records its offer ID, hash, evidence, and audit revision. Any new canonical event after that revision makes a new booking request fail with `consent_stale`, including a late-arriving message with an earlier occurrence time. Refresh and obtain current acceptance evidence before trying again.

### Advisory model context

Any command except `initialize` and `record_local_acceptance` may include both `model_run_id` and a nonblank `model_review_note` of at most 1,000 characters. The run must be succeeded and bound to the exact current case revision, canonical snapshot hash, projected input hash and validated candidate. Label/reference data is not accepted. Every selected command evidence ID must also appear in the model candidate's `evidence_event_ids`; the normal source/actor/correlation checks still apply independently.

The generic model output proposes a next step; it does not supply typed booking terms or authorize an operation. The operator chooses the command and verifies its complete structured fields. A compact `model_context` containing the run ID, source/input hashes, candidate hash and review note is persisted in the audit. No command is executed merely because a model job succeeds, a proposal is selected, a page renders or a status poll completes.

Context is resolved inside the command transaction after idempotency replay and current-version checks. A historical successful replay does not depend on the model job being available again. `400 invalid_model_context` rejects malformed context, invalid candidates or unsupported field combinations; `409 model_context_unavailable` rejects absent/unfinished/failed runs, and `409 model_context_stale` rejects source mismatches. Unknown resolver errors are sanitized.

### Local preview acceptance

The customer preview can explicitly acknowledge the exact current offer using `record_local_acceptance`. This adds exactly two canonical events in one transaction: an explicitly labelled simulated customer message, then the normal coordination audit. Its consent includes `mode: "local_preview_simulation"` and `authenticated: false`; `consent.created_revision` equals the final audit revision. A database or validation failure leaves neither event behind. It does not request a booking or contact a carrier.

The preview displays full slot/offset, handover, required attendance and charge. A stale or replaced offer cannot be accepted. A timeout retains the identical request body and idempotency key for explicit retry. A post-save refresh must contain the saved receipt or a verifiable later audit history; an older response is not presented as the current outcome.

## Reading state and freshness

The aggregate contains `case_id`, `version`, `phase`, `revision`, `snapshot_hash`, `dispatch_actor_id`, `original_booking`, `offer`, `consent`, `pending_request`, `operation_receipts`, and `audit_history`; escalation additionally records its reason and evidence. `revision` and `snapshot_hash` identify the canonical head immediately after that aggregate's audit event, not necessarily the current head after later source messages.

Case detail projects `states.coordination` as the stored phase and `states.coordination_freshness` as `not_initialized`, `current`, or `stale`. `current` requires both aggregate revision and hash to match the current case snapshot. A stale aggregate does not advance or disappear on read. Without a separate current decision, stale coordination projects lifecycle `in_review`; current coordination maps to the corresponding review/wait/approval/ready state, with `booking_confirmed` mapping to `resolved`. That lifecycle label still does not establish physical delivery.

Pending requests have `status: "pending_local_readback"`, `request_id`, `kind`, `created_revision`, and sandbox metadata; booking requests also have `terms_hash`. Confirmations append a receipt with `status: "confirmed_locally"`, evidence IDs and confirmation time, then clear the pending request. A pending request is a local record, not evidence of successful transmission.

## Client recipe and retries

1. Fetch case detail and inspect its current `snapshot`, aggregate version, phase and freshness.
2. Build one exact command from that head, the current offer/request identifiers, and qualifying source evidence. Choose a new idempotency key for this intended command.
3. POST with all required headers. Keep the exact body and key until the outcome is known.
4. After a timeout or lost response, retry the same body and key. Exact replay returns the originally persisted result without another audit, even if newer case events now exist. Fetch case detail afterward if current state is needed.
5. On `409`, fetch current case detail and reconsider the action and evidence. Do not blindly retry a changed body under the same key, or merely replace stale preconditions to bypass a business conflict. A newly intended command needs a new key.

Errors use `{"error":{"code":"..."}}`. `400` covers malformed fields/terms and missing evidence (`invalid_coordination_request`, `invalid_terms`, `invalid_case_request`, `invalid_platform_request`, `evidence_not_found`, plus HTTP JSON errors). `409` covers canonical binding, replay and workflow conflicts (`revision_conflict`, `snapshot_conflict`, `idempotency_conflict`, `workflow_conflict`, `coordination_not_initialized`, `coordination_already_initialized`, `coordination_transition_blocked`), evidence conflicts (`evidence_actor_mismatch`, `evidence_stale`, `evidence_correlation_mismatch`), and offer/consent conflicts (`offer_mismatch`, `consent_required`, `consent_stale`). Storage failures return `503 platform_unavailable`, without exposing database details.

## Persistence and local evidence boundary

Each accepted command atomically writes a new aggregate, a clearly labelled internal canonical-case audit event, and its body-bound replay result. The audit binds the preceding source revision/hash and the configured local operator principal. Failures roll back all three and the canonical head. The operator principal is an attribution label, not customer or carrier authentication.

`record_local_acceptance` additionally appends its simulated source event inside that same transaction. No schema migration is needed for these additive command/audit fields; the existing version-2 aggregate table stores them.

Additive migration `tools/dwelly_platform/migrations/002_coordination.sql` creates `platform_coordination` with a sequence primary key, case foreign key, positive version, JSON record stored as text, and unique `(case_id, version)`. Existing case data and legacy rescheduling records remain available; running the platform migrator upgrades version 1 storage to version 2 without resetting it.

## Frozen-source demonstration

`prepare_terms_demo` reads `docs/demos/2026-10-10-case-001-terms/source.case-001-terms.json` and verifies frozen SHA-256 `fc1f55e8258346b53f77b5cce03ae6fb7e0b227433daab19894caa4da8d160cf` from source commit `15ec6c7faa1d48b0bd6ac9093936d2cc8f69a53c`. The adapter retains original source facts and message IDs `001`–`011`, adds labelled source context, and records provenance. It shifts the source anchor `2026-02-02` to the chosen date, applying the same day offset to timestamps, ISO dates and the prose date while preserving UTC times. The original file is not rewritten.

Dispatch routing configuration and the original local booking ID are explicitly synthetic configuration, not original source facts. Authored expected states are excluded from inference input. Append messages stepwise; do not supply future messages, future derived terms, or the provenance packet to earlier inference cutoffs.

With a running local platform and a fresh case ID, run:

```sh
python -m tools.dwelly_platform.terms_demo \
  --base-url http://127.0.0.1:8091 \
  --case-id terms-demo-fresh \
  --anchor-date 2030-06-01
```

Use the actual platform port and an anchor leaving the offered slot in the future. All three flags are required. The CLI accepts loopback HTTP only, disables redirects and proxies, checks sandbox capabilities, rejects an existing case ID, and prints a JSON receipt with provenance, phase trace and HTTP steps. It adds two explicitly labelled synthetic Dispatch readbacks to correlate original messages `003`/`011` with locally generated request IDs and the booking hash. It does not modify those original messages or send real messages.

This is a scripted local operator replay: `model_calls: 0`, `external_effects: 0`, and physical delivery unconfirmed. A passing replay is backend workflow evidence, not proof of live LLM reasoning, provider availability, genuine customer consent, carrier participation, or real delivery.
