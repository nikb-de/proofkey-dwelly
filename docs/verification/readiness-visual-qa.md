# Readiness visual verification — 10 October 2026

Delivered the original 1600 × 1160 architecture graphic in [`proofkey-readiness-2026-10-10.svg`](../architecture/proofkey-readiness-2026-10-10.svg) with a matching [PNG preview](../architecture/proofkey-readiness-2026-10-10.png). The local architecture stays pinned to source revision `3d08cd3`; private cloud-pilot acceptance is updated separately below. The rendering checks themselves are not runtime, cloud or model acceptance tests.

## Evidence and meaning

The local storage/export path and remaining boundaries were checked against:

- [`postgres-case-backend.md`](../architecture/postgres-case-backend.md), [`postgres-integration-report.md`](postgres-integration-report.md), [`postgres-deploy-report.md`](postgres-deploy-report.md) and [`postgres-export-report.md`](postgres-export-report.md).
- [`INTAKE-README.md`](../../design/right-ontime/prototype/INTAKE-README.md) for browser-local IndexedDB, media previews and absent server upload.
- [`tools/dwelly_model/README.md`](../../tools/dwelly_model/README.md), [`tools/dwelly_service/server.py`](../../tools/dwelly_service/server.py), [`runtime/README.md`](../../runtime/README.md) and [`datasets/team-handoff-v1/README.md`](../../datasets/team-handoff-v1/README.md) for separate legacy model, simulated runtime and draft-dataset paths.
- [`production-readiness.md`](../../deploy/cloud-run/production-readiness.md), the coordinator's live preflight and acceptance reports, and [`cloud-case-pilot-2026-10-10.md`](cloud-case-pilot-2026-10-10.md) for the confirmed `genaide` / `europe-west2` / £200 per month constraint and current cloud status.

Four solid green links describe the existing local chain: trusted CLI → case API → PostgreSQL → pinned export → decision-input JSON. Two additional solid links now describe the accepted private cloud path: IAM → Cloud Run → Cloud SQL. Secret Manager is provisioned and supplies versioned credentials; no additional network connector is drawn. The outbox has no consumer. No connection is asserted from the browser to the API, exported inputs to the legacy model runner, or simulated runtime to real operations.

The user restored login, and the coordinator verified authentication, active project/billing and required APIs. The initial empty regional inventory was followed by explicit resource creation. The final coordinator acceptance report records regional-HA Cloud SQL `proofkey-case-pg` as runnable, a successful migration job, eight live runtime database-permission checks, and **100 passing HTTPS checks on one synthetic case** across five 20-check runs: initial revision-2 candidate, revision-2 default route, fresh revision-3 candidate, revision-3 default route, and rollback to revision 2. Those checks include create/retry/append/history/two pending outbox intents and IAM 403, app-auth 401 and browser-Origin 403 denials. Cloud Run `proofkey-case-api` revision `00002` is the accepted revision with 100% traffic; revision `00003` retains a zero-traffic tag after rollback. `Ready=True` and `RoutesReady=True` were confirmed at `2026-10-10T12:17:05Z`. Access requires IAM (no `allUsers` grant). The image digest is `sha256:9e53394d896b6db76e61597d973b91afc851c705f61639ae1682a3500e1f032e`.

The visual now reads **PRIVATE PILOT LIVE**, scoped to case storage and pending analysis intents, with redeployment to a fresh revision and revision rollback checked. These are not crash or database-restart tests. It explicitly states **Full product not ready** and **DR restore untested**. The £200 per month budget has alert thresholds; it is not a hard cap. On-demand backup `1791634467660` succeeded at `12:15:58Z`, but no restore or failover drill is claimed. No live model, operational runtime, real integration or full-product deployment is implied. Cloud state updates do not rewrite the `3d08cd3` local architecture baseline.

The **375 tests + 487 subtests** and **45 Docker checks** remain historical local verification receipts, not checks rerun while creating the graphic. Their Docker evidence is Linux ARM64. New release verification reported by the coordinator is **411 tests + 647 subtests**, including **17 offline cloud-smoke unit tests**; the eight live database-permission checks and the 100 synthetic HTTPS checks are reported separately from those local tests. The five live runs reuse one synthetic case and are not 100 independent cases. Dataset status is 9 assistant-authored draft rows and 0 human-reviewed eligible rows; the graphic makes no gold-label or accuracy claim.

## Fresh artifact checks

Used bundled Node.js with Sharp for SVG rasterization and Playwright for Chromium geometry checks. Playwright's default expected Chromium build was absent; the installed headless Chromium executable was selected explicitly. No browser download or package change was needed.

| Check | Observed result |
| --- | --- |
| Chromium XML load | Root `svg`; no parser error |
| Canvas / raster | 1600 × 1160 PNG, 234,061 bytes |
| Text geometry | 68 text elements; 0 outside the canvas; 0 overlapping text pairs |
| Component geometry | 14 bounded groups; 0 labels outside component bounds, including 9 px horizontal and 7 px vertical inset |
| Minimum text size | 16 px at the native 1600 px width |
| Links | Exactly 4 solid local edges and 2 solid accepted-cloud edges; no other connectors |
| Required semantics | All source, private-pilot, passed-redeploy/rollback, one-synthetic-case, full-product-not-ready, DR-restore-untested, dataset, simulated-adapter and historical-verification phrases present; obsolete not-deployed and restart claims absent from the SVG |
| Portability | 0 external image, script or stylesheet references |
| Raster inspection | PNG viewed at native dimensions; labels, arrowheads, icons and cloud boundary readable without clipping |
| Whitespace | Direct source/receipt check: 0 trailing-whitespace lines, final newline present, 0 merge markers; no whitespace diagnostics from `git diff --no-index --check` |

Chromium version: `153.0.8010.12`. The artifact checks assess the graphic and its stated boundaries; they do not establish current application, provider or deployment readiness.

## Artifact hashes

| File | SHA-256 |
| --- | --- |
| SVG | `aecc87f5bbc3e1232ebe4ae916b3505579984bf613d9ad00e7e9b6315b45eca8` |
| PNG | `b301e495861e440201c8c075afdd00bfb492e38950d0d6ff24a43aee789cf3b7` |
