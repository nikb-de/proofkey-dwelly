from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import unittest

from proofkey.assessment.audit import (
    AuditInputError, CandidateAuditRequestV1, RequiredDriverPositionV1,
    audit_candidate_evidence,
)
from proofkey.assessment.driver_contracts import (
    DriverManifest, RunnerReceipt, canonical_bytes, digest_bytes,
)


def synthetic_fixture():
    # All bytes below are declared fixture data, not a runtime execution.
    source = canonical_bytes({
        "version": "candidate-source-v1", "kind": "fixture-only",
        "files": {"fixture.py": sha256(b"synthetic source").hexdigest(),
                  "src/proofkey/schema.sql": sha256(b"synthetic schema").hexdigest()},
    })
    expectations = (
        canonical_bytes({"version": "driver-expectation-v1", "expectation_version": "audit-test-v1",
            "predicates": [{"id": "one-reschedule", "event_tag": "physical",
                "field_path": ["reschedule"], "operation": "equals", "expected": 1}]}),
        canonical_bytes({"version": "driver-expectation-v1", "expectation_version": "audit-test-v1",
            "predicates": [{"id": "one-refusal", "event_tag": "physical",
                "field_path": ["refusal"], "operation": "equals", "expected": 1}]}),
        canonical_bytes({"version": "driver-expectation-v1", "expectation_version": "audit-test-v1",
            "predicates": [{"id": "zero-replay-effect", "event_tag": "physical",
                "field_path": ["replay_effects"], "operation": "equals", "expected": 0}]}),
    )
    manifests = tuple(DriverManifest(
        version="runtime-driver-v1", driver_id=driver, obligation=obligation,
        variant="fixture-only", case_id=case, independence_group=group,
        case_bytes_hash=sha256(case.encode()).hexdigest(),
        scenario_hash=sha256(b"synthetic scenario").hexdigest(),
        driver_code_hash=sha256(b"synthetic driver").hexdigest(),
        candidate_manifest_hash=digest_bytes(source), profile_name="synthetic-profile",
        profile_hash=sha256(b"synthetic profile").hexdigest(),
        process_hash=sha256(b"synthetic process").hexdigest(),
        policy_hash=sha256(b"synthetic policy").hexdigest(),
        expectation_version="audit-test-v1", expectation_hash=digest_bytes(expectation),
        execution_kind="public_sequence", dependency_ids=("synthetic-runtime",))
        for driver, obligation, case, group, expectation in (
            ("window", "R01", "C1", "window-family", expectations[0]),
            ("goods", "R05", "C2", "goods-family", expectations[1]),
            ("saved", "R15", "C3", "window-family", expectations[2]),
        ))
    request = CandidateAuditRequestV1(
        source_manifest_bytes=source,
        required_source_paths=("fixture.py", "src/proofkey/schema.sql"),
        positions=tuple(RequiredDriverPositionV1(
            ordinal=index, repetition=0, manifest_bytes=manifest.to_bytes(),
            expectation_bytes=expectations[index],
            required_predicate_ids=(("one-reschedule",), ("one-refusal",),
                                    ("zero-replay-effect",))[index])
            for index, manifest in enumerate(manifests)),
        audited_at=datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc))
    first_bytes = manifests[0].to_bytes()
    positive = RunnerReceipt(
        manifest_bytes=first_bytes, manifest_hash=digest_bytes(first_bytes),
        ordinal=0, repetition=0, status="completed",
        raw_event_bytes=(b'{"event_tag":"physical","reschedule":1}',),
        raw_output_bytes=b'{}', raw_output_hash=digest_bytes(b'{}'),
        elapsed_seconds=0.25, source_pre_manifest_bytes=source,
        source_post_manifest_bytes=source)
    second_bytes = manifests[1].to_bytes()
    unavailable = RunnerReceipt(
        manifest_bytes=second_bytes, manifest_hash=digest_bytes(second_bytes),
        ordinal=1, repetition=0, status="not_started",
        dependency_limits=("dependency_unavailable",),
        error_bytes=b"private synthetic diagnostic: not public audit text")
    return request, positive, unavailable


class CandidateEvidenceAuditTests(unittest.TestCase):
    def test_partial_fixture_preserves_required_and_supplied_denominators(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (positive, unavailable))
        self.assertEqual((audit.required_count, audit.supplied_count,
                          audit.joined_count, audit.missing_count), (3, 2, 2, 1))
        self.assertEqual(tuple(position.status for position in audit.positions),
                         ("captured", "captured", "missing"))
        self.assertEqual(tuple(position.capture_status for position in audit.positions),
                         ("completed", "not_started", None))
        self.assertEqual(tuple(position.assessment_status for position in audit.positions),
                         ("passed", "ungraded", None))
        self.assertEqual(audit.passed_variants, (("window", "fixture-only", "R01"),))
        self.assertEqual(audit.scope_status, "unqualified")
        self.assertIn("fixture_only_source", audit.limitations)
        states = {item.requirement_id: item.status for item in audit.implementation.requirements}
        self.assertEqual(states["R01"], "missing")  # One variant is not all of R01.
        self.assertEqual(states["actual_content_roles"], "missing")
        self.assertEqual(states["protected_isolation"], "missing")
        self.assertNotIn("private synthetic diagnostic", audit.implementation.model_dump_json())
        self.assertEqual(len(audit.supplied), 2)

    def test_duplicate_and_wrong_manifest_cannot_replace_missing_required_work(self):
        request, positive, unavailable = synthetic_fixture()
        wrong_manifest = replace(positive, ordinal=1)
        audit = audit_candidate_evidence(request, (positive, positive, wrong_manifest))
        self.assertEqual((audit.required_count, audit.supplied_count,
                          audit.joined_count, audit.missing_count), (3, 3, 0, 1))
        self.assertEqual(tuple(position.status for position in audit.positions),
                         ("invalid", "invalid", "missing"))
        self.assertEqual(audit.positions[0].supplied_indexes, (0, 1))
        self.assertEqual(audit.positions[1].supplied_indexes, (2,))
        self.assertEqual((audit.invalid_required_count, audit.invalid_supplied_count), (2, 3))
        self.assertEqual(audit.passed_variants, ())
        self.assertEqual(len(audit.supplied), 3)
        states = {item.requirement_id: item.status for item in audit.implementation.requirements}
        self.assertEqual(states["driver_inventory_join"], "invalid")
        with self.assertRaises(AuditInputError):
            audit_candidate_evidence({"complete": True, "actual_roles": True}, ())
from dataclasses import FrozenInstanceError
from unittest.mock import patch


class CandidateAuditRefinementTests(unittest.TestCase):
    def test_safe_source_inventory_mismatch_retains_all_denominators(self):
        request, positive, unavailable = synthetic_fixture()
        incomplete = replace(request, required_source_paths=(
            "fixture.py", "missing.py", "src/proofkey/schema.sql"))
        audit = audit_candidate_evidence(incomplete, (positive, unavailable))
        self.assertEqual(audit.source_scope_status, "incomplete")
        self.assertEqual((audit.required_count, audit.supplied_count,
                          audit.joined_count, audit.missing_count), (3, 2, 2, 1))
        self.assertEqual(audit.position_counts,
                         (("captured", 2), ("missing", 1), ("invalid", 0)))
        self.assertEqual(audit.capture_counts,
            (("completed", 1), ("failed", 0), ("invalid_output", 0),
             ("no_output", 0), ("not_started", 1), ("none", 1)))
        self.assertEqual(audit.passed_variants, ())
        self.assertIn("source_scope_incomplete", audit.limitations)

    def test_not_started_is_joined_without_inventing_source_observation(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (positive, unavailable))
        observed = audit.positions[1]
        self.assertEqual(observed.status, "captured")
        self.assertEqual(observed.capture_status, "not_started")
        self.assertEqual(observed.assessment_status, "ungraded")
        self.assertEqual(observed.source_observation, "missing")
        self.assertEqual(observed.reasons,
                         ("source_observation_missing", "capture_not_completed"))
        self.assertEqual(audit.joined_count, 2)
        self.assertEqual(audit.invalid_required_count, 0)
        self.assertEqual(audit.supplied[1].status, "matched")

    def test_wrong_present_noncompleted_source_differs_from_missing_source(self):
        request, positive, unavailable = synthetic_fixture()
        wrong_source = canonical_bytes({
            "version": "candidate-source-v1", "kind": "fixture-only",
            "files": {"fixture.py": sha256(b"different synthetic source").hexdigest(),
                      "src/proofkey/schema.sql": sha256(b"synthetic schema").hexdigest()},
        })
        failed = replace(unavailable, status="failed",
                         source_pre_manifest_bytes=wrong_source,
                         source_post_manifest_bytes=None)
        audit = audit_candidate_evidence(request, (positive, failed))
        self.assertEqual(audit.positions[1].status, "captured")
        self.assertEqual(audit.positions[1].source_observation, "mismatched")
        self.assertEqual(audit.positions[1].reasons,
                         ("source_snapshot_mismatch", "capture_not_completed"))
        self.assertEqual(audit.positions[1].assessment_status, "ungraded")
        self.assertEqual(audit.capture_counts,
            (("completed", 1), ("failed", 1), ("invalid_output", 0),
             ("no_output", 0), ("not_started", 0), ("none", 1)))
        self.assertEqual(audit.joined_count, 2)

    def test_global_shape_and_budget_preflight_finishes_before_grading(self):
        request, positive, unavailable = synthetic_fixture()
        large = replace(unavailable, error_bytes=b"x" * 1_048_576)
        with patch("proofkey.assessment.audit.assess_driver") as grade:
            with self.assertRaisesRegex(AuditInputError, "^unsafe_supplied_shape$"):
                audit_candidate_evidence(request, [positive])
            with self.assertRaisesRegex(AuditInputError, "^input_limit_exceeded$"):
                audit_candidate_evidence(request, (large,) * 33)
            grade.assert_not_called()

    def test_safe_semantic_tampering_is_indexed_not_a_dropped_position(self):
        request, positive, unavailable = synthetic_fixture()
        tampered = replace(unavailable)
        object.__setattr__(tampered, "status", "invented-status")
        audit = audit_candidate_evidence(request, (positive, tampered))
        self.assertEqual((audit.required_count, audit.supplied_count,
                          audit.joined_count, audit.missing_count,
                          audit.invalid_required_count, audit.invalid_supplied_count),
                         (3, 2, 1, 1, 1, 1))
        self.assertEqual(audit.positions[1].status, "invalid")
        self.assertIsNone(audit.positions[1].capture_status)
        self.assertEqual(audit.supplied[1].index, 1)
        self.assertEqual(audit.supplied[1].status, "invalid")
        self.assertEqual(audit.supplied[1].reasons, ("invalid_receipt_semantics",))
        self.assertNotIn("invented-status", audit.implementation.model_dump_json())

    def test_output_is_detached_and_whole_candidate_requirements_stay_missing(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (positive, unavailable))
        with self.assertRaises(FrozenInstanceError):
            audit.joined_count = 99
        with self.assertRaises(FrozenInstanceError):
            audit.positions[0].status = "missing"
        with self.assertRaises((AttributeError, TypeError)):
            audit.implementation.requirements.append("caller-green")
        fixed = {"whole_candidate_closure", "actual_content_roles", "development_activation",
                 "calibrated_labels", "protected_isolation", "timed_drills",
                 "clean_reproduction", "source_rights", "independent_whole_branch_review",
                 "official_eligibility"} | {f"R{i:02}" for i in range(1, 16)}
        rows = {row.requirement_id: row for row in audit.implementation.requirements}
        self.assertTrue(fixed <= rows.keys())
        self.assertTrue(all(rows[name].status == "missing" and not rows[name].evidence_refs
                            for name in fixed))
        self.assertEqual(audit.scope_status, "unqualified")

class CandidateAuditBoundaryTests(unittest.TestCase):
    def test_failed_and_missing_trace_never_count_as_passed_variants(self):
        request, positive, unavailable = synthetic_fixture()
        failed = replace(positive, raw_event_bytes=(b'{"event_tag":"physical","reschedule":0}',))
        insufficient = replace(positive, raw_event_bytes=())
        for receipt, expected in ((failed, "failed"), (insufficient, "insufficient")):
            with self.subTest(expected=expected):
                audit = audit_candidate_evidence(request, (receipt, unavailable))
                self.assertEqual(audit.positions[0].assessment_status, expected)
                self.assertEqual(audit.positions[0].capture_status, "completed")
                self.assertEqual(audit.passed_variants, ())
                self.assertEqual(audit.required_count, 3)

    def test_safe_unexpected_and_invalid_duplicates_keep_supplied_inventory(self):
        request, positive, unavailable = synthetic_fixture()
        outside = replace(positive, ordinal=3)
        invalid = replace(positive)
        object.__setattr__(invalid, "status", "invented-status")
        audit = audit_candidate_evidence(request, (positive, invalid, unavailable, outside))
        self.assertEqual(tuple(row.status for row in audit.supplied),
                         ("duplicate", "duplicate", "matched", "unexpected"))
        self.assertEqual(audit.positions[0].supplied_indexes, (0, 1))
        self.assertIn("invalid_receipt_semantics", audit.supplied[1].reasons)
        self.assertEqual((audit.required_count, audit.supplied_count, audit.joined_count,
                          audit.missing_count, audit.invalid_required_count,
                          audit.invalid_supplied_count), (3, 4, 1, 1, 1, 3))

    def test_unsafe_receipt_shapes_and_frozen_request_bypass_reject_before_grade(self):
        request, positive, unavailable = synthetic_fixture()
        from unittest.mock import patch
        for field, value in (("elapsed_seconds", float("nan")),
                             ("ordinal", True), ("raw_event_bytes", [])):
            tampered = replace(unavailable)
            object.__setattr__(tampered, field, value)
            with self.subTest(field=field), patch("proofkey.assessment.audit.assess_driver") as grade:
                with self.assertRaisesRegex(AuditInputError, "^unsafe_supplied_shape$"):
                    audit_candidate_evidence(request, (positive, tampered))
                grade.assert_not_called()
        broken = replace(request)
        object.__setattr__(broken, "positions", [])
        with patch("proofkey.assessment.audit.assess_driver") as grade:
            with self.assertRaises(AuditInputError):
                audit_candidate_evidence(broken, (positive,))
            grade.assert_not_called()

    def test_projection_counts_groups_and_passed_variants_are_recomputed(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (positive, unavailable))
        for changes in ({"joined_count": 99}, {"independent_groups": ("ghost",)},
                        {"passed_variants": (("ghost", "fixture-only", "R01"),)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(audit, **changes)
        with self.assertRaises(ValueError):
            replace(audit.positions[0], required_predicate_ids=("ghost",))

    def test_empty_supplied_inventory_is_three_missing_not_success(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, ())
        self.assertEqual((audit.required_count, audit.supplied_count, audit.joined_count,
                          audit.missing_count), (3, 0, 0, 3))
        self.assertEqual(audit.passed_variants, ())
        self.assertEqual(audit.scope_status, "unqualified")
        with self.assertRaises(AuditInputError):
            replace(request, positions=())


class CandidateAuditFocusedTests(unittest.TestCase):
    # These cases catch loss of bounded invalid evidence, missing revalidation,
    # false source success, and output objects that can contradict their roster.
    def test_safe_missing_extra_and_unsafe_source_paths(self):
        request, positive, unavailable = synthetic_fixture()
        for paths in (("fixture.py",), ("fixture.py", "safe_extra.py", "src/proofkey/schema.sql")):
            audit = audit_candidate_evidence(replace(request, required_source_paths=paths), (positive,))
            self.assertEqual(audit.source_scope_status, "incomplete")
            self.assertEqual(audit.joined_count, 1)
            self.assertEqual(audit.passed_variants, ())
        for paths in (("../escape",), ("/absolute",), ("a\\b",), ("a//b",),
                      ("a/./b",), ("C:drive",), ("A", "a")):
            with self.subTest(paths=paths), self.assertRaises(AuditInputError):
                replace(request, required_source_paths=paths)
        bad_source = canonical_bytes({"version": "candidate-source-v1", "kind": "fixture-only",
                                      "files": {"../escape": "a" * 64}})
        with self.assertRaises(AuditInputError):
            replace(request, source_manifest_bytes=bad_source)

    def test_noncompleted_matching_pre_missing_post_and_wrong_completed(self):
        request, positive, unavailable = synthetic_fixture()
        failed = replace(unavailable, status="failed", source_pre_manifest_bytes=request.source_manifest_bytes)
        audit = audit_candidate_evidence(request, (failed,))
        self.assertEqual(audit.positions[1].source_observation, "missing")
        self.assertEqual(audit.positions[1].reasons, ("source_observation_missing", "capture_not_completed"))
        wrong = canonical_bytes({"version": "candidate-source-v1", "kind": "fixture-only",
                                 "files": {"fixture.py": "a" * 64}})
        tampered = replace(positive)
        object.__setattr__(tampered, "source_pre_manifest_bytes", wrong)
        object.__setattr__(tampered, "source_post_manifest_bytes", wrong)
        audit = audit_candidate_evidence(request, (tampered,))
        self.assertEqual(audit.positions[0].status, "invalid")
        self.assertEqual(audit.positions[0].reasons, ("invalid_receipt_semantics",))
        self.assertEqual(audit.passed_variants, ())

    def test_expectation_joins_and_grammar_reject_without_grading(self):
        from proofkey.assessment.driver_contracts import strict_loads
        request, positive, unavailable = synthetic_fixture()
        position = request.positions[0]
        cases = []
        base = strict_loads(position.expectation_bytes)
        for field, value in (("expectation_version", "other"), ("version", "other")):
            cases.append({**base, field: value})
        for changes in ({"id": "unsafe/id"}, {"field_path": [True]}, {"field_path": [4096]},
                        {"operation": "count_equals", "field_path": [], "expected": True},
                        {"operation": "count_equals", "expected": 1}, {"event_tag": ""}):
            cases.append({**base, "predicates": [{**base["predicates"][0], **changes}]})
        for data in cases:
            raw = canonical_bytes(data)
            manifest = DriverManifest.from_bytes(position.manifest_bytes)
            # Update the hash so grammar, not merely the hash mismatch, is exercised.
            manifest = replace(manifest, expectation_hash=digest_bytes(raw))
            with self.subTest(data=data), patch("proofkey.assessment.audit.assess_driver") as grade:
                with self.assertRaises(AuditInputError):
                    replace(position, manifest_bytes=manifest.to_bytes(), expectation_bytes=raw)
                grade.assert_not_called()
        with self.assertRaises(AuditInputError):
            replace(position, required_predicate_ids=("different",))
        with self.assertRaises(AuditInputError):
            replace(position, expectation_bytes=canonical_bytes({**base, "unexpected": 1}))

    def test_source_kind_and_complete_declared_roster_never_green_whole_candidate(self):
        request, positive, unavailable = synthetic_fixture()
        one = replace(request, positions=(request.positions[0],))
        audit = audit_candidate_evidence(one, (positive,))
        self.assertEqual(tuple(r.status for r in audit.implementation.requirements[:3]),
                         ("satisfied", "satisfied", "satisfied"))
        self.assertTrue(all(r.status == "missing" for r in audit.implementation.requirements[3:]))
        source = canonical_bytes({"version": "candidate-source-v1", "kind": "filesystem",
            "files": {"fixture.py": "a" * 64, "src/proofkey/schema.sql": "b" * 64}})
        manifest = replace(DriverManifest.from_bytes(positive.manifest_bytes), candidate_manifest_hash=digest_bytes(source))
        raw = manifest.to_bytes()
        one = replace(one, source_manifest_bytes=source,
                      positions=(replace(one.positions[0], manifest_bytes=raw),))
        receipt = replace(positive, manifest_bytes=raw, manifest_hash=digest_bytes(raw),
                          source_pre_manifest_bytes=source, source_post_manifest_bytes=source)
        audit = audit_candidate_evidence(one, (receipt,))
        self.assertEqual(audit.source_kind, "filesystem")
        self.assertNotIn("fixture_only_source", audit.limitations)
        self.assertEqual(audit.scope_status, "unqualified")

    def test_numeric_aliases_and_safe_unexpected_invalid_inventory(self):
        request, positive, unavailable = synthetic_fixture()
        for field, value in (("ordinal", False), ("repetition", True), ("process_exit", True),
                             ("elapsed_seconds", float("inf")), ("ordinal", 2**63),
                             ("status", "\ud800"), ("raw_event_bytes", (bytearray(b"x"),))):
            bad = replace(unavailable)
            object.__setattr__(bad, field, value)
            with self.subTest(field=field, value=value), self.assertRaisesRegex(AuditInputError, "^unsafe_supplied_shape$"):
                audit_candidate_evidence(request, (bad,))
        for field, value in (("ordinal", 999), ("process_exit", 2**40), ("elapsed_seconds", -1),
                             ("manifest_hash", "z" * 64), ("status", "unknown")):
            bad = replace(unavailable)
            object.__setattr__(bad, field, value)
            audit = audit_candidate_evidence(request, (bad,))
            self.assertEqual(audit.supplied[0].status, "invalid")
            self.assertEqual(audit.supplied[0].reasons, ("invalid_receipt_semantics",))
            self.assertEqual(audit.joined_count, 0)
        outside = replace(unavailable, ordinal=7)
        object.__setattr__(outside, "status", "unknown")
        audit = audit_candidate_evidence(request, (outside,))
        self.assertIsNone(audit.supplied[0].required_index)
        self.assertEqual(audit.supplied[0].status, "invalid")
        self.assertEqual(audit.missing_count, 3)

    def test_detaches_custom_timezone_and_revalidates_frozen_nested_inputs(self):
        from datetime import timedelta, tzinfo
        class MutableZone(tzinfo):
            hours = 2
            def utcoffset(self, dt):
                return timedelta(hours=self.hours)
        zone = MutableZone()
        request, positive, unavailable = synthetic_fixture()
        request = replace(request, audited_at=datetime(2026, 10, 9, 14, tzinfo=zone))
        zone.hours = 9
        audit = audit_candidate_evidence(request, (positive,))
        self.assertIs(request.audited_at.tzinfo, timezone.utc)
        self.assertIs(audit.implementation.audited_at.tzinfo, timezone.utc)
        self.assertEqual(audit.implementation.audited_at.hour, 12)
        for stamp in (datetime(2026, 10, 9), True, 0):
            with self.assertRaises(AuditInputError):
                replace(request, audited_at=stamp)
        position = replace(request.positions[0])
        object.__setattr__(position, "required_predicate_ids", ["one-reschedule"])
        object.__setattr__(request, "positions", (position,))
        with patch("proofkey.assessment.audit.assess_driver") as grade:
            with self.assertRaises(AuditInputError):
                audit_candidate_evidence(request, (positive,))
            grade.assert_not_called()

    def test_output_rejects_status_table_cross_reference_and_fixed_requirement_tampering(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (positive, unavailable))
        for changes in ({"capture_counts": (("completed", True),)},
                        {"supplied": (replace(audit.supplied[0], index=2), audit.supplied[1])},
                        {"positions": (replace(audit.positions[0], supplied_indexes=(1,)),) + audit.positions[1:]},
                        {"scope_status": "qualified"}, {"limitations": ()}, {"required_count": True}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "^invalid_audit_projection$"):
                replace(audit, **changes)
        data = audit.implementation.model_dump()
        data["requirements"][3]["status"] = "satisfied"
        from proofkey.contracts import ImplementationAudit
        with self.assertRaisesRegex(ValueError, "^invalid_audit_projection$"):
            replace(audit, implementation=ImplementationAudit.model_validate(data))
        nested = replace(audit.positions[0])
        object.__setattr__(nested, "predicates", [])
        with self.assertRaisesRegex(ValueError, "^invalid_audit_projection$"):
            replace(audit, positions=(nested,) + audit.positions[1:])

    def test_missing_slot_bypass_rejects_with_closed_error_before_grading(self):
        request, positive, unavailable = synthetic_fixture()
        object.__delattr__(unavailable, "error_bytes")
        with patch("proofkey.assessment.audit.assess_driver") as grade:
            with self.assertRaisesRegex(AuditInputError, "^unsafe_supplied_shape$"):
                audit_candidate_evidence(request, (positive, unavailable))
            grade.assert_not_called()

    def test_output_missing_nested_slot_is_sanitized(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (positive,))
        object.__delattr__(audit.positions[0], "status")
        with self.assertRaisesRegex(ValueError, "^invalid_audit_projection$"):
            replace(audit)

    def test_projection_invalid_manifest_reason_must_agree_with_available_hash(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (positive, unavailable))
        from proofkey.assessment.audit import SuppliedAuditV1
        bad = SuppliedAuditV1(0, 0, 0, 0, audit.positions[0].manifest_hash,
            "invalid", "completed", "not_checked", ("manifest_mismatch",))
        position = replace(audit.positions[0], status="invalid", capture_status=None,
            assessment_status=None, predicates=(), source_observation="not_checked",
            reasons=("manifest_mismatch",))
        data = audit.implementation.model_dump()
        for row in data["requirements"][1:3]:
            row["status"] = "invalid"
            row["reason"] = "invalid_driver_join"
        data["missing_evidence"] = ["R%02d" % n for n in range(1, 16)] + [
            "whole_candidate_closure", "actual_content_roles", "development_activation",
            "calibrated_labels", "protected_isolation", "timed_drills", "clean_reproduction",
            "source_rights", "independent_whole_branch_review", "official_eligibility"]
        data["invalid_evidence"] = ["driver_inventory_join", "declared_driver_results"]
        from proofkey.contracts import ImplementationAudit
        with self.assertRaisesRegex(ValueError, "^invalid_audit_projection$"):
            replace(audit, positions=(position,) + audit.positions[1:], supplied=(bad,) + audit.supplied[1:],
                joined_count=1, invalid_required_count=1, invalid_supplied_count=1,
                position_counts=(("captured", 1), ("missing", 1), ("invalid", 1)),
                capture_counts=(("completed", 0), ("failed", 0), ("invalid_output", 0),
                                ("no_output", 0), ("not_started", 1), ("none", 2)),
                assessment_counts=(("passed", 0), ("failed", 0), ("insufficient", 0),
                                   ("ungraded", 1), ("none", 2)),
                supplied_counts=(("matched", 1), ("duplicate", 0), ("unexpected", 0), ("invalid", 1)),
                independent_groups=("goods-family",), passed_variants=(),
                implementation=ImplementationAudit.model_validate(data))

    def test_supplied_invalid_constructor_rejects_match_only_reasons(self):
        from proofkey.assessment.audit import SuppliedAuditV1
        # A row with known valid hash identity cannot claim only a source failure
        # while retaining a successful source observation.
        errors = []
        for changes in ({"required_index": None, "reasons": ("manifest_mismatch",)},
                        {"required_index": 0, "reasons": ("manifest_mismatch", "source_snapshot_mismatch")}):
            try:
                SuppliedAuditV1(index=0, ordinal=0, repetition=0, manifest_hash="a" * 64,
                    status="invalid", capture_status="completed", source_observation="not_checked", **changes)
            except ValueError:
                errors.append("rejected")
            else:
                errors.append("accepted")
        self.assertEqual(errors, ["rejected", "rejected"])

    def test_each_resource_ceiling_precedes_any_grading(self):
        request, positive, unavailable = synthetic_fixture()
        variants = []
        for changes in ({"error_bytes": b"x" * (1_048_576 + 1)},
                        {"raw_event_bytes": (b"{}",) * 65},
                        {"raw_event_bytes": (b"x" * 1_048_576,) * 8}):
            bad = replace(unavailable)
            for key, value in changes.items():
                object.__setattr__(bad, key, value)
            variants.append((positive, bad))
        variants.append((unavailable,) * 257)
        for supplied in variants:
            with self.subTest(count=len(supplied)), patch("proofkey.assessment.audit.assess_driver") as grade:
                with self.assertRaisesRegex(AuditInputError, "^input_limit_exceeded$"):
                    audit_candidate_evidence(request, supplied)
                grade.assert_not_called()

    def test_noncompleted_matched_source_represents_group_without_passing(self):
        request, positive, unavailable = synthetic_fixture()
        record = replace(unavailable, source_pre_manifest_bytes=request.source_manifest_bytes,
                         source_post_manifest_bytes=request.source_manifest_bytes)
        audit = audit_candidate_evidence(request, (record,))
        self.assertEqual(audit.independent_groups, ("goods-family",))
        self.assertEqual(audit.positions[1].source_observation, "matched")
        self.assertEqual(audit.positions[1].assessment_status, "ungraded")
        self.assertEqual(audit.passed_variants, ())

    def test_request_identity_alias_duplicate_and_wrong_source_rejected(self):
        request, positive, unavailable = synthetic_fixture()
        for positions in ((request.positions[0], request.positions[0]),
                          (request.positions[0], replace(request.positions[0], ordinal=7))):
            with self.assertRaisesRegex(AuditInputError, "^invalid_request_identity$"):
                replace(request, positions=positions)
        manifest = replace(DriverManifest.from_bytes(request.positions[0].manifest_bytes),
                           candidate_manifest_hash="a" * 64)
        with self.assertRaisesRegex(AuditInputError, "^invalid_request_identity$"):
            replace(request, positions=(replace(request.positions[0], manifest_bytes=manifest.to_bytes()),))
        with self.assertRaises(AuditInputError):
            replace(request.positions[0], ordinal=True)

    def test_request_resource_counts_have_closed_limit_error(self):
        request, positive, unavailable = synthetic_fixture()
        with self.assertRaisesRegex(AuditInputError, "^input_limit_exceeded$"):
            replace(request, positions=(request.positions[0],) * 257)
        with self.assertRaisesRegex(AuditInputError, "^input_limit_exceeded$"):
            replace(request, required_source_paths=("fixture.py",) * 4097)
        with self.assertRaisesRegex(AuditInputError, "^input_limit_exceeded$"):
            replace(request.positions[0], required_predicate_ids=("one-reschedule",) * 65)


class CandidateAuditIdentityFixTests(unittest.TestCase):
    def test_unexpected_constructor_rejects_removed_valid_capture_identity(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (replace(positive, ordinal=7),))
        row = audit.supplied[0]
        self.assertEqual((row.status, row.ordinal, row.repetition, row.capture_status),
                         ("unexpected", 7, 0, "completed"))
        for changes in ({"ordinal": None}, {"repetition": None},
                        {"ordinal": None, "repetition": None}):
            with self.subTest(changes=changes), self.assertRaisesRegex(
                    ValueError, "^invalid_audit_projection$"):
                replace(row, **changes)

    def test_aggregate_revalidates_frozen_unexpected_capture_identity(self):
        request, positive, unavailable = synthetic_fixture()
        audit = audit_candidate_evidence(request, (replace(positive, ordinal=7),))
        for changes in ({"ordinal": None}, {"repetition": None},
                        {"ordinal": None, "repetition": None}):
            row = replace(audit.supplied[0])
            for field, value in changes.items():
                object.__setattr__(row, field, value)
            with self.subTest(changes=changes), self.assertRaisesRegex(
                    ValueError, "^invalid_audit_projection$"):
                replace(audit, supplied=(row,))

    def test_each_noncompleted_unexpected_capture_requires_valid_identity(self):
        request, positive, unavailable = synthetic_fixture()
        for capture in ("failed", "invalid_output", "no_output", "not_started"):
            receipt = replace(unavailable, ordinal=7, status=capture)
            audit = audit_candidate_evidence(request, (receipt,))
            self.assertEqual(audit.supplied[0].capture_status, capture)
            for changes in ({"ordinal": None}, {"repetition": None},
                            {"ordinal": None, "repetition": None}):
                with self.subTest(capture=capture, changes=changes), self.assertRaisesRegex(
                        ValueError, "^invalid_audit_projection$"):
                    replace(audit.supplied[0], **changes)

    def test_matched_duplicate_and_invalid_valid_captures_require_identity(self):
        request, positive, unavailable = synthetic_fixture()
        samples = (
            ("matched", (positive,)),
            ("duplicate", (positive, positive)),
            ("invalid", (replace(positive, ordinal=1),)),
        )
        for expected, receipts in samples:
            audit = audit_candidate_evidence(request, receipts)
            row = audit.supplied[0]
            self.assertEqual((row.status, row.capture_status), (expected, "completed"))
            for changes in ({"ordinal": None}, {"repetition": None},
                            {"ordinal": None, "repetition": None}):
                with self.subTest(status=expected, changes=changes), self.assertRaisesRegex(
                        ValueError, "^invalid_audit_projection$"):
                    replace(row, **changes)

    def test_out_of_range_semantic_invalid_identity_still_projects_none(self):
        request, positive, unavailable = synthetic_fixture()
        for changes, expected in (({"ordinal": 256}, (None, 0)),
                                  ({"repetition": 16}, (1, None)),
                                  ({"ordinal": 256, "repetition": 16}, (None, None))):
            receipt = replace(unavailable)
            for field, value in changes.items():
                object.__setattr__(receipt, field, value)
            with self.subTest(changes=changes):
                audit = audit_candidate_evidence(request, (receipt,))
                row = audit.supplied[0]
                self.assertEqual((row.ordinal, row.repetition), expected)
                self.assertEqual((row.status, row.capture_status, row.required_index),
                                 ("invalid", None, None))
                self.assertEqual(row.reasons, ("invalid_receipt_semantics",))
                self.assertEqual((audit.required_count, audit.supplied_count,
                                  audit.joined_count, audit.missing_count), (3, 1, 0, 3))
                self.assertEqual(replace(audit).supplied, (replace(row),))
