# Design completeness and integration review

Source reviewed: supplied Right onTime v4.1, commit/hash recorded in [import provenance](IMPORT-PROVENANCE.md). Scope: case creation, evidence intake and a shared contract for parallel engineering. This is not a clinical/security certification or full accessibility audit.

## What the original design covered

The five organiser snapshots plus one synthetic scenario form an internally coherent offline workflow demonstration. The screens distinguish preparation, proposals, requests, correlated responses, uncertain outcomes, bounded waits and operator intervention. The selected Forest identity is retained.

The original design did **not** support arbitrary new cases or actual uploaded evidence. All five source snapshots had empty attachment lists; no file picker, byte reading, image/audio preview or attachment storage existed. Original test receipts cover the predefined simulation, not these missing paths.

## Delivered extension and remaining boundary

| Area | Local extension | Still outside this release |
|---|---|---|
| Case intake | Separate creation/list/detail workspace | Shared CRM, authenticated identity and per-case access |
| Source events | Append-only local revisions and exact API-shaped export | Automatic ingestion from external messaging/calls |
| Images/audio | Real selected bytes, validation, hash, local preview and IndexedDB | Server object storage, malware scanning and retention policy |
| Reload/failure | Local persistence and explicit storage/validation failures | Cross-device sync or durable cloud backup |
| Analysis | Explicit not-started state | OCR/ASR/vision and revision-driven model worker |
| Business actions | Zero effects; no fabricated booking | Real carrier scheduling/returns/refunds and operator receipts |
| Team contracts | Versioned schemas, API availability and separate lifecycle definitions | Target endpoint implementation |

The extension deliberately does not push untrusted data into the hardcoded six-scenario simulator. That simulator interpolates trusted literals and lacks arbitrary-case workflow mappings. Local data is rendered separately with text-safe DOM operations; the original scenario state is not reset or migrated.

## Integration handoff

Open [local intake](prototype/intake.html). Use [team contract v1](../../contracts/v1/README.md) for backend/E2E/evaluation work and [architecture](../../docs/architecture/team-contract-v1.md) for ownership/state transitions. JSON export contains API-shaped metadata, not file bytes or an authenticated backend snapshot. Opening an original Team/Customer demo does not run a real workflow for a newly created local case.

The current service rejects all browser `Origin` headers and has no byte-upload endpoint. A later authenticated BFF and private asset service must implement the frozen target boundary; the workbench must not gain a browser-visible service token or disable these protections.

Fresh results, limits and screenshots are recorded separately in [verification](../../docs/verification/team-contract-workbench-2026-10-10.md). Supplied `manifest.json` and `prototype/evidence/` remain historical v4.1 receipts.
