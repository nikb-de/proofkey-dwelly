# Bounded installation repair

## Intent and classification

The user prioritizes easy integration, rapid adaptation and reliable resolution, and has requested faster execution of the remediation program. This bounded repair addresses only the already-declared installation entry point. The user approved the linked design and acquisition of the four exact missing pinned artifacts on 2026-10-09 by requesting execution of the fix. Existing autonomous subagent execution continues; the implementation plan must remain within this design.

## Selected design

Use ordinary filesystem-installed Python packages on the observed macOS arm64 / CPython 3.12 target. Place byte-identical profile and fixture copies under `src/proofkey/resources/`; keep `src/proofkey/schema.sql` in place. Declare package data and a deliberate source-distribution manifest. Do not add a generic resource-provider interface or zip extraction.

Change the two existing built-in path roots locally rather than introducing an unnecessary executable module. The ten-name profile allowlist remains identical. Caller-selected trusted profile paths retain their existing behavior. Host profile/fixture reads continue through `_pinned`, including directory-component no-follow, regular-file, single-link, bounded-read, stable-file and SHA-256 checks. Writable state remains under the caller's separate resource/state root; never under installed package data.

An unpacked-wheel requirement is deliberate: executable registration already verifies filesystem `.py` paths. Zipped/frozen execution and Windows support are not claimed. Linux execution remains a separate evidence obligation.

## Identity and data preservation

The original `runtime/profiles/` and `runtime/fixtures/development/` files remain canonical development sources. Tests compare every packaged copy byte-for-byte and pin their inventory. No JSON reformatting is permitted.

`profiles.py` is a current factory implementation pin. Changing it requires a new current registration identifier and updated current registration fixture/qualifier references. Preserve `REGISTERED_IMPLEMENTATIONS` historical constants and legacy serialization vectors unchanged. Do not widen registered-admission implementation coverage or process authority.

## Alternatives rejected

1. Copy resources beside site-packages: preserves the faulty external layout and risks unrelated package collisions.
2. Move canonical fixtures: unnecessary churn across existing tests and preserved evidence.
3. Generic resource loader / archive extraction: expands the interface and lifetime/security surface without serving the two-demo installation goal.

## Verification contract

1. RED: package-data and relocated-package tests expose missing data or source-layout assumptions. A relocation test is a regression check, not an installed-environment receipt.
2. GREEN: minimal packaging/path repair; all ten names, trusted explicit paths, fresh journal creation, missing/tampered assets and CWD shadow rejection checked.
3. Inspect wheel and sdist exact members and resource hashes; reject private outputs, runtime state and unplanned data.
4. Install using a fresh venv and a fully staged exact local wheelhouse, with user site disabled, `PYTHONPATH` cleared and no dependency resolution/download during installation. Verify module origins outside the checkout.
5. Execute console, module, library and explicitly composed API for the existing window/goods cases; retain raw exit/output/effect/readback/export evidence. No public listener is required for API `TestClient` checks.
6. Independently review the diff, run the relevant existing regression suites and one frozen full suite, then qualify current factory registration.

Do not label J13 closed before actual installed execution. J14's `verify_release` remains unavailable, and the broad release, rights, human, provider and assessment gates remain open.

## Dependency boundary

Installed source-test dependencies match the 19-entry historical API lock. The existing environment lacks setuptools and is not an installed ProofKey environment. Sixteen matching cached wheel bodies exist, but they are not a staged wheelhouse. Missing exact artifacts are `setuptools==84.0.0`, `pillow==12.3.0`, `pypdf==6.10.0`, and CPython 3.12/macOS arm64 `pydantic-core==2.46.5`. Do not use a cached CPython 3.13 wheel or upgrade versions. If acquisition is approved, retain URLs, artifact hashes, target tags and lock joins before using them. If unavailable, report a partial repair and keep installed verification open.
