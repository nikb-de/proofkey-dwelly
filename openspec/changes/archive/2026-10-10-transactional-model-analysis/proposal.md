# Transactional model analysis

## Why
The state-analysis UI is presently a deterministic local baseline. The team needs actual model proposals with visible provider receipts and durable, retry-safe request tracking. Models must not read author labels, determine their own authority or cause operational effects.

## What Changes
- Add server-owned OpenAI, Anthropic and Gemini profiles and a closed step-analysis candidate contract.
- Add PostgreSQL jobs with atomic idempotency and conservative budget reservations, fenced attempts, durable responses and results.
- Connect the existing UI to asynchronous model jobs and transaction details while preserving offline compatibility.
- Verify with local PostgreSQL, mocked providers, browser QA and bounded live canaries when configured credentials are available.

## Boundaries
No automatic provider retry, business action, changes to existing case-intake contracts or deployment to Cloud Run. The existing cloud case outbox remains separate. Existing authorization permits autonomous implementation and at most USD25 per model per experiment; this new surface uses its own explicit budget scope and opt-in startup. A budget reservation is local admission accounting, not a provider billing cap.
