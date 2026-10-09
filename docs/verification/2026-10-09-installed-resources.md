# Installed offline resources — verification

Status: package repair and initial installed execution verified; final frozen full suite and whole-change review pending. This report is updated from actual receipts, not used as a success flag by the runtime.

## Scope

Source repair `88022995c2906fce0a68327c98e2fb4d73464db1`: package-owned exact data, two built-in root corrections and a new current factory registration. No new business case, authority, live adapter, public server or full release verifier. The tested target is CPython 3.12.14 on macOS arm64.

## Completed evidence

- Fresh installed old baseline `52ada2f` reproduced the defect: all 13 resource members absent, installed profile loading failed. [Raw baseline receipt](../../outputs/proofkey-installation-2026-10-09/baseline-1/receipt.json).
- TDD: three new regression tests first failed, then passed; 169 focused existing tests passed in 246.117 seconds. Historical profile/fixture bytes, factory constants/vectors and host `_pinned` validation were preserved.
- All twenty exact wheels retained: sixteen cache copies and four approved downloads. [Artifact receipt](../../outputs/proofkey-installation-2026-10-09/dependencies/artifact-receipt.json). Actual bundled notices and metadata were inventoried separately; this is not legal clearance.
- Initial fixed wheel/sdist inspection and fresh outside-checkout installation passed. All eight declared positions (two cases × console/module/library/API) passed with exact verified effect counts, original request/journal readback, export hashes and owner closure. All installed site-packages files remained unchanged. [Build/install receipt](../../outputs/proofkey-installation-2026-10-09/fixed-1/receipt.json), [effect/readback receipt](../../outputs/proofkey-installation-2026-10-09/fixed-1/smoke/receipt.json).

The documentation-bearing candidate will be rebuilt and checked separately. Final artifacts and complete-suite results are not yet asserted here.

## Residual boundaries

J14 full release verification stays unavailable. Linux, Windows, protected assessment, unfamiliar-user adoption, actual human release approval, native/model participation and distribution-rights clearance remain separate. The data are fixed synthetic replay cases: return creation is not physical receipt, and no money moves.

One earlier diagnostic harness attempt (`baseline/`) failed because two backend hooks shared mutable process arguments; it is retained, excluded from product pass evidence, and was corrected by running each hook in a fresh process. No failed attempt has been overwritten.
