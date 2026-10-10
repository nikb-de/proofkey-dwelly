# Production readiness and architecture snapshot

## Why
The user requests a production deployment and a ByteByteGo-style view of what is ready. Deployment cannot proceed while the configured Google identity fails token refresh and project, region and infrastructure budget remain unconfirmed. A truthful visual must not portray separately implemented systems as one working production path.

## What Changes
- Add a concise current-state architecture graphic, distinguishing local connections, disconnected components and production gaps.
- Record the live read-only cloud preflight failure and a gated production handoff.
- Correct stale documentation that says the separate synthetic runtime source is absent.
- Do not change application guards, create cloud resources or expose a public endpoint.

## Capabilities
### New Capabilities
- `production-readiness-visual`: evidence-linked current-state architecture and deployment handoff.

## Impact
Documentation and locally rendered vector/raster assets only. The requested deployment remains blocked, not completed.
