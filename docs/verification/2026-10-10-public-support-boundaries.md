# Public support boundaries — J08

Status: **documentation, controller checks and independent whole-leaf review complete**. This is a documentation-only qualification of the support map, not new runtime, installation, provider or user-research evidence.

The documentation candidate is `14bdde49316eb32c60ba13c4a0cc10b82bb4c27e`. It changes only the [runtime README](../../runtime/README.md#support-and-evidence-map), [detailed dated matrix](judge-remediation-2026-10-09/support-matrix.md) and a dated addendum in [integration discovery](judge-remediation-2026-10-09/integration-discovery.md). The historical investigation body is byte-identical after removing the new addendum.

## What the map distinguishes

- J13 `5bc38c8`: recorded eight installed fixed-case positions on CPython 3.12.14/macOS arm64.
- J06 `80e0d6f`: final four positive and seven negative installed trusted-case positions, retaining the full five-attempt history in its report.
- Trace `7b4c6e2`: source-only captures and receipt projection; final regression was pending at this documentation checkpoint.
- Other command routing, registered v1 run-only behavior, unqualified stop-v2 development, and six simulated interfaces are separate rows rather than implied positive integrations.

The table keeps dispatch unknown, original readback unobserved and publication files unchecked for the renderer. It does not equate return initiation with receipt/payment, queued handoff with operator acceptance, or syntax and HTTP/process success with business success.

## Checks performed

The author checked 19 added local links/anchors, seven table rows and required candidate/boundary phrases. The controller independently checked the exact committed documentation, not a later working-tree version, using a retained Ruby script with `git show` and read-only local link resolution:

```text
candidate 14bdde49316eb32c60ba13c4a0cc10b82bb4c27e
local links / anchors: 19 checked, 0 errors
table rows: 7
missing required claim phrases: 0
historical integration body preserved: true
exit: 0
```

`git diff --check` passed. Independent task/whole-leaf review approved exact candidate `14bdde4` for specification compliance and documentation quality with C0/I0/M0. The reviewer independently checked all 19 new links and preserved historical content. Its first local Ruby checker invocation failed on interpreter syntax compatibility; the corrected read-only check passed, and the reviewer report records both attempts. No runtime test, fresh acceptance, installation, network call, provider call or external publication was performed by this leaf. Link existence and phrase checks are not artifact authenticity or runtime correctness checks.

## Exact documentation bytes

| File | SHA-256 |
| --- | --- |
| runtime README | `232d330b3d18306bcee3efecfeaa2e2cdf965ba0a5668535c17cb031a7c22c2b` |
| Detailed support matrix | `dd41bc7898b2b5b6501ffd77a1e9a0ab9639796a64e2ef35e00759b48f6eed14` |
| Integration discovery with dated addendum | `59fbf3e619b90f29369f3f3c0ef7475e866bc5a8b9f7b4ef198d621d0b69ec14` |

J08 is complete only for this bounded public documentation. J07 implementation, J21 unfamiliar-engineer validation, J27 security/source audit and other unfulfilled requirements remain open. Combined parent task 4.5 still depends on the separate trace leaf's closure.

Strict prearchive validation passed, and OpenSpec archived this child under its UTC date as [2026-10-09-public-support-boundaries](../../openspec/changes/archive/2026-10-09-public-support-boundaries/tasks.md), adding three requirements to the [living specification](../../openspec/specs/public-support-boundaries/spec.md). The controller check receipt SHA-256 is `0fa7dea14be1e998922e1ad42f4097c095c6d78f35bc8bcb29b208affcdb74a9`. Review reports, exact diff and the reusable read-only check are retained in [the local evidence pack](../../outputs/proofkey-public-support-20261010/).

Postarchive `openspec validate --all --strict --json` passed all 11 items (seven living specifications and four open changes), zero failures. The existing informational long-requirement note in the registry specification remains; it is not a new failure or a warning-free claim.
