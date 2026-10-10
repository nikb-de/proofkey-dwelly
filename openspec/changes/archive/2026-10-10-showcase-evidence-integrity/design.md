## Context

The builder consumes completed local capture reports. Its existing checks compare model input IDs and copied hash fields, and only bind the final coordination record to a snapshot. Review probes showed that changed model bodies and final coordination copied into an early scene are accepted. Actual captures legitimately retain older coordination while new source messages arrive.

## Goals / Non-Goals

**Goals:** Reject inconsistent evidence before export, preserve valid historical coordination, and keep both existing bundles byte-identical when rebuilt.

**Non-Goals:** Change runtime coordination, contact a provider, evaluate model semantics, or regenerate capture artifacts.

## Decisions

- Reuse the pure `project_snapshot` and canonical hashing helpers. Comparing the full projection also protects message order, body, sender, timestamp, recipient and non-message context; comparing IDs alone does not.
- Verify snapshot content hashes and consistent historical prefixes. Bind each coordination revision and hash to a captured snapshot at or before the scene cutoff, rather than requiring it to equal the scene revision.
- Bound retained nested records and evidence to the coordination snapshot, and verify offer terms against their recorded hash. Preserve the existing output shape and authoritative source records.
- Keep tests offline with realistic canonical fixtures and negative mutations. Run the original captures through the builder and compare serialized bytes with existing bundles.

## Risks / Trade-offs

- Previously tolerated inconsistent reports will fail closed. Regression tests cover the rejection and real captures cover compatibility.
- Hash consistency establishes internal integrity, not authenticity or model quality. Existing sandbox qualifications remain unchanged.

## Migration Plan

No data migration. Update the pure validator and rerun offline tests and byte comparisons. Existing UI assets remain untouched.
