## 1. Review and implementation planning

- [x] 1.1 Review the shadow-only scope, trusted mapping ownership and source receipt contract; record approval or adjustments.
- [x] 1.2 Produce the Superpowers implementation plan in docs/superpowers/plans/ from this specification, with exact files and focused tests.

## 2. Shadow bridge

- [x] 2.1 Write failing tests for source/binding hashes, provenance, case-scoped citations, unsupported mappings and unchanged contact drafts.
- [x] 2.2 Implement strict bounded input contracts and trusted mapping validation in an optional companion package.
- [x] 2.3 Write failing tests and implement atomic idempotent shadow records, conflict detection and safe artifact-root access.
- [x] 2.4 Implement an opt-in local CLI with shadow_recorded, unmapped and rejected results; do not change service default behavior.

## 3. Safety and delivery

- [x] 3.1 Use spies and before/after state hashes to prove zero provider, workflow, gateway, adapter, checkpoint, budget and ownership mutations.
- [x] 3.2 Demonstrate valid imports plus mismatched identity, stale generation, missing receipt, invalid citation and malicious-path rejection.
- [x] 3.3 Run focused tests, independent review and a local no-network smoke; document exact limitations and reproduction commands.
- [x] 3.4 Archive only this implemented and verified scope into living OpenSpec documentation.

## Follow-on work outside this change

The design describes separate milestones for typed runtime proposals and real-processing admission, native connectors, media processing and cloud deployment. They are not completion criteria for this preparatory shadow-import change, and completing this change does not establish readiness in any of those areas.
