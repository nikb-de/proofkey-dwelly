# Model-backed Dwelly decision and judge release

## Why
Replace the lexical-only pilot with an API-backed, evidence-cited next-action proposer and three independent provider judge calls. Ship runnable CLI and Docker source to the existing private repository within the user's 30-minute target. Model-only scores remain provisional because human review and new team cases are pending.

## What Changes
- Add a standalone standard-library package under `tools/dwelly_model`; do not modify the operational runtime.
- Add OpenAI, Anthropic and Gemini API transports, explicit model IDs, sanitized failures and bounded response parsing.
- Add snapshot-only proposals and eight-rubric independent judgments, retaining provider receipts and missing outputs.
- Add durable pre-call spend reservations capped at USD 25 per provider/model per experiment, no automatic retries, CLI preflight/dry-run/run, Docker and team intake instructions.

## Impact
Existing Dwelly data and baseline remain unchanged. Private GitHub publication is authorized. No actual messages, booking, refund, provider administration or private team document uploads are authorized. New team eval/live data remain pending; public cases are development data, not held-out evidence.
