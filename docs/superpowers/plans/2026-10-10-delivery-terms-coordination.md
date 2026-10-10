# Delivery Terms Coordination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Use TDD and independent file ownership.

**Goal:** Make the principal changed-terms case executable against a local, transactional backend without pretending to contact a real carrier.

**Architecture:** Add a strict coordination aggregate and append canonical internal audit events atomically. Use explicit source-bound local attestations for offers/consent/readbacks. Keep existing rescheduling and historical model jobs unchanged.

**Tech Stack:** Python, PostgreSQL/psycopg, existing local HTTP BFF, pytest.

**Spec:** openspec/changes/delivery-terms-coordination/specs/delivery-terms-coordination/spec.md

## Global Constraints
- English machine states and copy; zero external business effects; no paid model calls in verification.
- Preserve unrelated uncommitted provider changes, original case source, old rescheduling API and stored jobs.
- Every command takes expected_revision, snapshot_hash, expected_workflow_version; no permissive clock override.

## Review Focus
- Changed source after acceptance must block a new booking request.
- Wrong actor, old event or wrong request/terms hash must not confirm a result.
- Command/audit failure must roll back both tables and canonical head.
- Existing databases must migrate additively and existing services must not be destructively reset.
- Seeded source facts and configured actor directory are labelled evidence, never authority or leaked expected actions.

## Task 1: Coordination domain and store
Files: tools/dwelly_platform/coordination.py; tools/dwelly_platform/tests/test_coordination.py.
Interface: CoordinationMixin.coordination_command(case_id,key,body) and coordination_detail(case_id). _coordination_detail(connection,case_id) is safe inside PlatformStore._detail. Use existing _request, _history, _append, _now and operator_identity. Table platform_coordination(sequence bigserial,case_id,version,record), unique(case_id,version).
Commands: initialize {dispatch_actor_id,original_booking:{booking_id,terms}}, request_cancellation {evidence_event_ids}, confirm_cancellation {request_id,evidence_event_ids}, record_offer {terms,evidence_event_ids}, record_consent {offer_id,terms_hash,evidence_event_ids}, request_booking {offer_id,terms_hash}, confirm_booking {request_id,terms_hash,evidence_event_ids}, escalate {reason,evidence_event_ids}. All nested payloads strict; common command field plus source/workflow preconditions. Version 0 before initialization; first command version 1.
- [x] Write failing tests for initialization, state transitions, stale/cross-actor/changed-offer rejection.
- [x] Implement pure validation and mixin, audit each successful command via _append within the same transaction with a clearly labelled internal event.
- [x] Test replay, concurrent writes, rollback, restart and zero external effects using real PostgreSQL.

## Task 2: Source-only main-case adapter
Files: tools/dwelly_platform/scenarios.py; tools/dwelly_platform/tests/test_scenarios.py.
Interface: prepare_terms_demo(case_id,anchor_date) returns declaration, events, provenance. Read frozen docs/demos/2026-10-10-case-001-terms/source.case-001-terms.json. Preserve original text with explicitly documented transformed ISO dates for executable copies. Add internal case-context event containing source facts; declare dispatch through separately labelled scenario directory, never copied back as original source. Do not include expected agent_state, result or success criteria in inference events. Future callers append source messages stepwise, not all before first decision.
- [x] Failing tests for 11 original event IDs, chronological dates, context, no label leakage and unchanged source bytes.
- [x] Implement pure adapter and passing tests.

## Task 3: Integrate HTTP and schema
Files: store.py, migrations/002_coordination.sql, server.py, tests/test_coordination_http.py.
- [x] Write failing HTTP tests for POST/GET /api/platform/cases/{id}/coordination, full workflow and rejection codes.
- [x] Add migration version 2, mixin inheritance, case-detail coordination field and routes. Map strict errors to 400/404/409 without leaking internals.
- [x] Verify end-to-end using source-only inputs and explicit sandbox operator attestations; assert no model call and no external effect.

## Task 4: Model candidates
Files: new model-profiles.current.json and documentation/tests; preserve historical model-profiles.example.json.
- [x] Verify exact current model IDs/prices from official sources; validate via existing loader without API dispatch.
- [x] Do not switch paid service silently. Expose explicit candidate config selection and distinguish configuration validity from account availability.

## Task 5: Review and complete
- [x] Run platform, analysis and model regression tests with scoped roots and importlib; run frontend tests if response changes affect them.
- [x] Independent review; fix material issues and rerun focused/full checks.
- [x] Update operations/docs, archive OpenSpec and record exact tests and remaining UI/live-provider work. No push or cloud deployment performed; existing local service restarted after checking it had no active model jobs.
