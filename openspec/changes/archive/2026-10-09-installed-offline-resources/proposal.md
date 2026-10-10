# Package the existing offline runtime resources

## Status

The user approved the linked bounded fix and four missing pinned artifacts with “работай над фиксом” on 2026-10-09. Read-only discovery and independent design review are complete; implementation and verification are tracked in tasks.md. This is a bounded J13 child, not approval or completion of J14 release reproduction.

## Why

The declared `proofkey` distribution has source-checkout resource assumptions: built-in profiles and host fixtures resolve outside the Python package, and package data is not explicitly declared. The installed CLI/library/API therefore lack a demonstrated portable resource contract. Static inspection identifies the defects; a built-wheel failure has not yet been observed.

## What Changes

- Include exact copies of all ten supported built-in profiles and the two fixed synthetic host fixtures under the Python package. Include the existing package-relative SQL schema.
- Resolve built-in resources inside that package, preserving trusted explicit profile paths, existing host byte/hash validation, release identities and writable-state boundaries.
- Refresh current factory implementation registration for changed source bytes without altering historical registrations or vectors.
- Verify wheel and sdist inventories and execute the installed CLI/module/library/API from an unrelated directory using a fresh target-specific environment.

## Capabilities

### New Capabilities

- `installed-offline-resources`: exact data inclusion and package-relative loading for the existing offline surface.

### Modified Capabilities

None. Existing authorization, process and outcome semantics remain unchanged.

## Impact

Expected code scope: `runtime/pyproject.toml`, an explicit sdist manifest, package data, built-in path selection in `profiles.py` and `host.py`, focused distribution tests, and current factory-registration evidence. Documentation will distinguish installation evidence from qualification. No live adapters, new public admission route, arbitrary resource selection, dependency upgrade, public server, provider call, publication or submission.

Fresh offline build/install is currently unavailable: the inspected local cache lacks the pinned backend and three target-compatible runtime wheels. Download permission is requested separately; absence of permission does not authorize substitution.
