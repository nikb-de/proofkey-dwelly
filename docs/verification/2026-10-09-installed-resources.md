# Installed offline resources — verification

Status: **J13 complete** for the bounded target. Package repair, final installed execution, full regression suite, current-code factory qualification and independent review passed. The [OpenSpec child is archived](../../openspec/changes/archive/2026-10-09-installed-offline-resources/tasks.md), with its three requirements in the [living specification](../../openspec/specs/installed-offline-resources/spec.md). J14 and the wider program remain open. This report is evidence, not a success flag consumed by the runtime.

## Scope

Source repair `88022995c2906fce0a68327c98e2fb4d73464db1`: package-owned exact data, two built-in root corrections and a new current factory registration. No new business case, authority, live adapter, public server or full release verifier. The tested target is CPython 3.12.14 on macOS arm64.

## Completed evidence

- Fresh installed old baseline `52ada2f` reproduced the defect: all 13 resource members absent, installed profile loading failed. [Raw baseline receipt](../../outputs/proofkey-installation-2026-10-09/baseline-1/receipt.json).
- TDD: three new regression tests first failed, then passed; 169 focused existing tests passed in 246.117 seconds. Historical profile/fixture bytes, factory constants/vectors and host `_pinned` validation were preserved.
- All twenty exact wheels retained: sixteen cache copies and four approved downloads. [Artifact receipt](../../outputs/proofkey-installation-2026-10-09/dependencies/artifact-receipt.json). Actual bundled notices and metadata were inventoried separately; this is not legal clearance.
- Initial fixed wheel/sdist inspection and fresh outside-checkout installation passed; retained as intermediate evidence in `fixed-1/`. The final candidate evidence below supersedes that intermediate attempt for completion.

Candidate `8e655ec` passed a separate fresh build/install in `fixed-2/`, then the complete regression suite. Final candidate **`5bc38c8824f425acae699aed940f028a283f7df1`** corrects only two stale README paragraphs; all other 259 runtime files, including code, tests, resources and pins, are byte-identical to the full-tested tree. The [source bridge](../../outputs/proofkey-installation-2026-10-09/source-bridge.json) records the sole README delta.

That final candidate was rebuilt and installed again in a fresh outside-checkout environment. All **8/8** public positions passed, all 55 loaded ProofKey module origins were in the installed environment, and all 1,732 site-packages files were unchanged. [Final build/install receipt](../../outputs/proofkey-installation-2026-10-09/fixed-3/receipt.json), [final effect/readback receipt](../../outputs/proofkey-installation-2026-10-09/fixed-3/smoke/receipt.json). The build invocation used symbolic `HEAD`; [source resolution](../../outputs/proofkey-installation-2026-10-09/fixed-3/source-resolution.json) binds its preserved source-tar hash to the concrete commit above through an independently matching `git archive`. No original receipt was rewritten.

For each position, checks cover the exact original request, persisted journal/checkpoint and verified intents, expected effects (one reschedule or one refusal plus one return), exports and successful owner closure. Raw synthetic state and exports are retained as 189 byte-identical files under [retained-state](../../outputs/proofkey-installation-2026-10-09/fixed-3/retained-state), with original-path mapping and per-file hashes in the [retention manifest](../../outputs/proofkey-installation-2026-10-09/fixed-3/retained-state-manifest.json). Original receipts still record the original temporary paths; copying did not rewrite those receipts. Intermediate `fixed-2/` state is also preserved.

The current-source synthetic factory qualifier passed **37/37 planned tests**, with no errors, failures, skips or expected/unexpected failures. Root independently checked all eight artifact hashes and exact equality of its 260-file before/after inventory to the frozen full-suite input. Its [manifest](../../outputs/proofkey-installation-2026-10-09/factory-qualification/manifest.json) SHA-256 is `c68da440b70b6519d44bf4e10d7d2a8a95c3922f7a995f5d1304a6695d1ab2d7`. Registration is `synthetic-factory-installed-resources-v1`; staging/approval remain simulated and non-v1 execution remains unavailable.

| Artifact | SHA-256 |
| --- | --- |
| [Wheel](../../outputs/proofkey-installation-2026-10-09/fixed-3/artifacts/proofkey_runtime-0.1.0-py3-none-any.whl) | `a81921092ef861d4051f4825327e9962911c6482d4d68559315b828a1d35965f` |
| [Source distribution](../../outputs/proofkey-installation-2026-10-09/fixed-3/artifacts/proofkey_runtime-0.1.0.tar.gz) | `a41b565ca8d5e2ba8b995d59736cdbe143110c113057556b62d7c65951f18f8d` |

The wheel rebuilt from that source distribution has the same SHA-256 as the wheel above. Exact inventories contain 102 wheel files and 113 source-distribution files, with thirteen committed resources and no tests, databases, environments or private source material. This observed equality is not a guarantee that every future build is byte-reproducible.

Final build/install receipt SHA-256: `a6c309103c1d1a3e6780d37120a6aaed2f867b6b70ab8d062a949789aadf496a`. Final effect/readback receipt SHA-256: `2e221db1a5cbcf9d2dc844e6bf459357fc1947447ad4bc6c89db295c89b80caf`.

## Complete regression and review

The full suite passed **1,696 tests in 888.324 seconds**, with no failures, errors or skips. HEAD `8e655ec` and all 260 runtime files were unchanged across that execution. Root checked the terminal `OK`, all 1,696 successful test lines, raw log hashes and both source inventories. [Full-suite receipt](../../outputs/proofkey-installation-2026-10-09/full-suite/receipt.json), SHA-256 `74ecc895751f3b46dc009b5ea23d53ce992999de0a5a05ecdeb44b837b6e8c07`.

The later README-only correction was not passed off as a new full-suite run: the source bridge proves executable/test/resource equality, and final installed evidence was regenerated. [Independent whole-change review](../../outputs/proofkey-installation-2026-10-09/implementation-review/final-review.md) approved the bounded change with **0 Critical / 0 Important / 0 Minor outstanding findings**. It checked the implementation, raw full-suite evidence, archives, exact dependencies and all eight persisted outcomes without rerunning the product. The reviewer explicitly records the initial missed stale README caveat and its verified correction.

Strict OpenSpec validation passed **7/7** after archival: five living specs and two unfinished parent changes. The only informational message concerns the length of an existing, unrelated registry requirement. The archive command initially counted its own not-yet-performed archive task as incomplete; it was marked complete only after the command succeeded. No broader parent was archived.

## Residual boundaries

J14 full release verification stays unavailable. Linux, Windows, protected assessment, unfamiliar-user adoption, actual human release approval, native/model participation and distribution-rights clearance remain separate. The data are fixed synthetic replay cases: return creation is not physical receipt, and no money moves.

One earlier diagnostic harness attempt (`baseline/`) failed because two backend hooks shared mutable process arguments; it is retained, excluded from product pass evidence, and was corrected by running each hook in a fresh process. An initial qualifier invocation used a relative output path and was rejected by argument parsing before execution; its logs are retained separately from the corrected absolute-path invocation. No failed attempt has been overwritten.
