# Registry commitments and short-parent evidence

Date: 9 October 2026. Candidate: `40138e1433b9f7ba782385124727dd2ea842f97f`. **Status: focused and full verification complete; J22/J32 narrow criteria closed and OpenSpec leaf archived.** Separate five-provider reassessment and source adjudication are complete, with four schema-eligible score sets from five returned answers. No production-readiness claim.

## Changes

- `0e71716`: public immutable `ReleaseRegistryV1.commitments()` and migration of composition, owner and route-store consumers.
- `0122660`: reject zero-byte records during complete byte preflight, before any envelope is parsed.
- `40138e1`: real-component tests for a two-second final observation phase, with UTC or monotonic time limiting it. No production timing change.

The projection contains only sorted exact tuple/string `(release_id, artifact_hash)` values. It validates actual current records, including type, positive size, count, aggregate size, ordering, canonical envelopes and identity. Owner checks still reject substitution before new claims, debt or business effects. Host composition still requires exactly one matching release. Stored canonical bytes and the existing registry digest recipe are unchanged.

The timing cases retain the original 120-second parent window. At real engine return, the test clock leaves UTC/monotonic residuals `(2,4)` or `(4,2)` seconds. Real image capture, route observation and claim persistence share one two-second context. Success records observed state; expiry before claim write retains a sealed claim, observed route, imported account and exactly one existing effect.

## Evidence and limits

| Evidence | Observed result |
| --- | --- |
| J22 absent-interface RED | 2 deliberate assertion failures before implementation |
| J22 broader focused runs | Other 87 tests passed; new test assertions were corrected to the existing absent-account/SQLite Row contracts |
| Corrected mutation case | 1 method, all 3 mutation subcases passed in 8.660 s |
| Independent J22 review fix | Later empty envelope initially reproduced wrong validation order; 3 focused commitment tests passed in 0.612 s after correction |
| J32 focused cases | 2 methods / 4 real-run subcases passed in 30.371 s |
| J32 sensitivity control | Deliberately generous five-second phase failed both explicit two-second assertions; not a production bug claim |
| Complete host-admission module | 38 tests passed in 164.894 s, unchanged restored production timing |
| Root complete runtime | 1,693 tests passed in 888.064 test seconds; zero errors/failures/skips; frozen HEAD and all 246 runtime files stable |
| Root fresh-process factory qualification | All 37 planned tests executed and passed; 246 source hashes stable; eight artifact hashes independently checked; non-v1 remains unavailable and staging remains `staged_simulation` |
| OpenSpec archival | [Only the J22/J32 leaf archived](../../openspec/changes/archive/2026-10-09-registry-commitments-and-short-parent-evidence/tasks.md); strict all-spec validation 6/6 passed; unfinished parents remain open |

Raw new candidate evidence is under `outputs/proofkey_runtime_panel_2026-10-09_r2/`. The full-suite receipt is `full-suite/receipt.json`; its raw stderr SHA-256 is `a2db2ecba8bfbca6de0a8ddd787edc8892817c03bdd7ab277d59ec0d8f2033d5`. The qualifier manifest is `qualification/manifest.json`, SHA-256 `88ade45391358687930486ee36e7acc22d9459059b0589a4018728a772c5432c`; independent readback is `qualification/independent-readback.json`. The suite wrapper elapsed 889.552 seconds; the test runner reported 888.064 seconds above.

Author reports and independent review records are preserved at [implementation-review](../../outputs/proofkey_runtime_panel_2026-10-09_r2/implementation-review/), moved intact from this plan's temporary SDD workspace. Failed test-authoring attempts are retained, not overwritten or presented as production failures.

Independent task reviews and the final approved-package architecture review found no remaining Critical/Important/Minor issue after the zero-byte fix. At review time the root full-suite/qualifier gate remained pending; it subsequently passed as recorded above. Maximum-envelope performance and wider product/provider/human readiness remain unestablished.

## Performance boundary

On-demand validation is measurable work: observed medians were 77.7 ms for one synthetic declaration, 156.1 ms for two, and 90.6 ms for one fixed-runtime declaration. These samples overlapped another local test process. They are neither isolated benchmarks nor an operational SLO. Worst-case 32-release/32-MiB throughput remains unmeasured. A stale cache that stops detecting substitution was not introduced.

## Assessment and remaining work

The new five-provider packet uses this tested candidate and unchanged eight rubric definitions. Its 327,124 bytes have SHA-256 `16544b8aba044168403910de948da22f04e1ef97493d2ce2a9b158da7def717c`. No old scores or verdicts are supplied. At the approximately 20:27 UTC dispatch checkpoint, Claude, AGY, Muse and separate Codex requests were submitted; the Grok CLI failed at its sandbox/Docker boundary and the separately approved Grok Web Expert request was submitted. All five seats subsequently returned answers. The [completed result and adjudication report](../../outputs/proofkey_runtime_panel_2026-10-09_r2/reports/ASSESSMENT.md) retains the failed transport and all raw answers.

| Seat | Eight-rubric /100 | Weighted R1–R5 /100 |
| --- | ---: | ---: |
| Claude | 62.5 | 67.0 |
| Grok Web Expert | 65.0 | 68.5 |
| AGY | Unavailable: schema-invalid | Unavailable: schema-invalid |
| Muse | 52.5 | 57.0 |
| Separate Codex session | 55.0 | 60.5 |

Four of five answers satisfy the declared aggregate schema. AGY returned object-keyed rubric scores and string-valued evidence rather than the required structure; its raw answer is preserved, not silently repaired or retried. All 30 findings were source-adjudicated in [Claude](../../outputs/proofkey_runtime_panel_2026-10-09_r2/reports/ADJUDICATION-claude.md), [Muse/AGY](../../outputs/proofkey_runtime_panel_2026-10-09_r2/reports/ADJUDICATION-muse-agy.md) and [Codex/Grok](../../outputs/proofkey_runtime_panel_2026-10-09_r2/reports/ADJUDICATION-codex-grok.md). No further J22/J32 defect was reproduced, so no second panel was warranted.

One bounded outer invocation per native client does not establish that its internal transport retries are disabled. Attempts/ceilings, unknown cost, identity uncertainty and failed seats remain visible. Weighted R1–R5 and unweighted eight-rubric results must be reported separately, with unavailable values left unavailable. These model opinions are not protected-holdout evidence or causal attribution to J22/J32.

J22/J32 verification criteria are closed and their OpenSpec leaf is archived. The register has eight closed and 24 open items. The broader program still has integration, installed packaging, process adaptation, recovery, multimodal processing, independent evaluation and human/provider gates. Passing local tests or receiving model reviews does not establish those outcomes, and neither J27/J30 nor the unfinished parent changes are closed by this leaf.
