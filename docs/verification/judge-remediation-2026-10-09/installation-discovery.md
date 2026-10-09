# Installation discovery — 2026-10-09

Status: read-only diagnosis and proposed bounded repair. No build, install, dependency download, test run or runtime-code change was performed for this discovery. Three independent local agents examined packaging, resource safety and dependency artifacts at `bf83ed92c3209b6b1d10819370f1ed9be9d74e57`; their findings were reconciled with source inspection.

## Confirmed source facts

| Area | Observation | Consequence |
| --- | --- | --- |
| `runtime/pyproject.toml` | Package discovery only; no explicit package data / sdist manifest | Required non-Python data inclusion is not declared |
| `profiles.py` | Built-in files resolve from `Path(__file__).resolve().parents[2] / "profiles"` | Ordinary installed layout points outside the package |
| `host.py` | Same external root for one profile and two fixtures | Both built-in replay registrations retain checkout assumptions |
| `journal.py` | Reads sibling `schema.sql` | Correct package-relative path, but distribution inclusion must be explicit |
| `host_files.py` | Component no-follow and bounded stable regular-file reads | Keep these controls; resource convenience must not replace them |
| Current factory registration | Includes `profiles.py` hash | Changed source needs a new current registration identity; preserve historical vectors |

These are static findings, not a recorded wheel-install failure. Fresh installation remains unverified.

## Exact resource anchors

| Resource | SHA-256 |
| --- | --- |
| `src/proofkey/schema.sql` | `1ce7f4a5c234c9a93223f9c1f1a3c048b71f6b9958fa9c4783a0d7aecc04f4f8` |
| `profiles/flat-v1.3.json` | `8fcd07924f5518ffa6e8b7cfcb3d773e8ba9f10d48458031132f8749c177a940` |
| `fixtures/development/packet-world-v1.json` | `cb9a2c3b8bcf77ee1f400cac7921b52b52f2468180c0b043b8f35f01058a0c59` |
| `fixtures/development/host-goods-world-v1.json` | `e3ec67bfd42fb4e6e26394eb9e22fb0c822194768a4eb8eec2ba63b32a27973f` |

## Dependency observations

The existing API environment is CPython 3.12.14 and has all 19 API-lock package versions. It lacks setuptools, an installed `proofkey-runtime` distribution and a `proofkey` console script. It is suitable for existing source-level tests, not evidence of clean installation.

Sixteen of nineteen locked wheel bodies were found in the inspected local pip HTTP cache and matched their recorded SHA-256. The exact target wheels for Pillow 12.3.0, pypdf 6.10.0 and pydantic-core 2.46.5 were absent; a cached CPython 3.13 pydantic-core wheel is incompatible. The pinned build backend setuptools 84.0.0 was also absent. Cache bodies must be staged and verified before they become an offline wheelhouse. Installed files are not substitute original wheel artifacts.

No automatic dependency upgrade, download, or reuse of an incompatible artifact is authorized by this report. The requested acquisition boundary is exactly these four missing pinned artifacts, with no live-provider operation.

## Next child

[Proposed design](../../../openspec/changes/installed-offline-resources/design.md) and [tasks](../../../openspec/changes/installed-offline-resources/tasks.md). Design approval is pending. J13 remains open. J14's unavailable full-release verifier and Linux/rights/provider/human qualification gates are unchanged.
