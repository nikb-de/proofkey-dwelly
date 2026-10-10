# Integrate the platform with team main

## Why
The platform and team main have unrelated roots. Both contain required work: the platform runtime and the team's current authored cases and GitHub library. Integrating by replacing either tree would lose functionality.

## What changes
- Preserve all main-only files and the unchanged authored case bytes.
- Merge the widget catalog, recipient-copy and limits semantics with hardened validation.
- Make the team's current cases available to the platform analysis catalog without relabeling legacy fixtures or changing their hashes.
- Preserve the platform runtime, communications, media controls, model concurrency and deterministic gates.

## Scope
Local integration, offline tests, reviewed merge. No provider spend, production deployment or external operational effects.
