# Rights and distribution status

This is a readable scope/status inventory, not proof of ownership, a populated `SourceReleaseContextV1`, legal clearance or permission to publish. The approved project intent and [pyproject.toml](pyproject.toml) select Apache-2.0 for **actually owned new application code**. [LICENSE](LICENSE) contains the standard terms. No copyright holder, employer ownership or contributor grant is inferred here. The standard bracketed appendix in LICENSE is an example, not an identified project owner.

| Material | Current boundary |
| --- | --- |
| New runtime application code | Intended Apache-2.0 scope, subject to actual ownership/contribution evidence for selected files |
| Development fixtures | Individual origin, rights, hash and required notice joins remain necessary; a synthetic-looking filename is not a grant |
| Generated media | [Provenance](fixtures/development/media/provenance.json) declares synthetic sources and Apache-2.0; semantic readiness is false and each selected file still needs an evidence join |
| Third-party packages/tools | Their own licenses/notices apply; see [NOTICE](NOTICE) and the dependency records below |
| Provider SDKs, services, models and outputs | Separate code, service, model, data and output terms; no inherited application license or live-use permission |
| Private originals and protected references | Excluded from public source preparation; preserve privately |

Private attachments, chats, recordings, raw documents, archives, organizer/customer/provider sources and protected evaluation material are not relicensed. Redaction, possession, hashes, public URLs, nearby license declarations or true rights flags do not establish a grant. Derived material needs its own authorized scope and lineage. Preserve original evidence privately rather than copying it into a public package.

Source preparation must enumerate exact allowed files with actual origin/custody/evidence, hashes and required notices. Do not copy the parent workspace recursively. Private evidence, credentials, run outputs/ANSWERS, databases/WAL/SHM, virtual environments, installed trees, binaries, build/cache files and Git metadata are excluded by default. [.gitignore](.gitignore) is a convenience for local generated files; it neither deletes existing material nor defines the release allowlist.

## Dependency evidence is incomplete

- [requirements.lock](requirements.lock): eight version pins, including setuptools 84.0.0 as build backend, with no artifact hashes.
- [requirements-api.lock](requirements-api.lock): nineteen historical wheel pins observed on CPython3.12/macOS-arm64 for runtime/API/API-test dependencies; excludes setuptools and unselected extras. It is not a wheelhouse, offline-install receipt or all-platform closure.
- [DEPENDENCIES.json](DEPENDENCIES.json): older metadata still marks API packages deferred/unavailable. Preserve that historical scope; it is not the current complete dependency inventory.

Join each selected distribution/version to its exact artifact/platform/hash, installer record, actual license/notice bytes and packaged notice entry. The setuptools build artifact needs a separate join. Certifi remains separately MPL-2.0; httpx's actual notice-file join is unresolved. Check additional notices bundled in selected wheels. Fixture-only ffmpeg 8.1.1 is recorded as GPL-3.0-or-later generation tooling, not a runtime dependency or redistributed binary; generator/native-codec notices need their own scoped assessment.

No source ownership, third-party clearance, clean no-index installation, packaged tests, video/native playback, provider/model participation, protected isolation, activation, timed drills or event eligibility is certified by these files. Actual release preparation and independent reproduction/review remain separate work.
