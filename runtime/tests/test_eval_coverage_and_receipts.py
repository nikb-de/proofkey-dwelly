"""Breaks caught: dropped denominators, false coverage, timer-only passes and fake calibration."""
import json
import time
import unittest
from test_label_reference_versions import FIXTURES, module, rows


class LedgerTests(unittest.TestCase):
    def test_ledger_retains_duplicates_invalid_ambiguous_and_excluded_positions(self):
        ledger = module(self, "ledger")
        initial = rows()
        invalid = {"case_id": "credential-like-do-not-echo", "input": {"token": "private-token"}}
        supplied = initial + [initial[0], invalid, b'{"broken":']
        result = ledger.inspect_case_ledger(supplied)
        self.assertEqual(result.audit.total_cases, 18)
        self.assertEqual(len(result.positions), 18)
        self.assertEqual(result.positions[-1].raw_bytes, b'{"broken":')
        self.assertEqual(result.positions[-2].status, "invalid")
        self.assertEqual(result.positions[-3].status, "duplicate")
        self.assertNotIn("private-token", result.audit.model_dump_json())
        self.assertEqual(result.audit.ambiguous_cases, 5)
        self.assertTrue(any(f.reason == "duplicate_case_id" for f in result.audit.findings))
        self.assertEqual(ledger.validate_case_ledger(initial).total_cases, 15)

    def test_every_fixture_joins_separate_reference_and_keeps_profile_semantics(self):
        ledger = module(self, "ledger")
        result = ledger.inspect_case_ledger(rows())
        self.assertFalse([f for f in result.audit.findings if f.severity == "error"])
        references = [json.loads(line) for line in (FIXTURES / "expectations.jsonl").read_text().splitlines()]
        self.assertEqual([position.row.reference.model_dump(mode="json") for position in result.positions], references)
        self.assertEqual(result.control_counts["rescheduling"], {"positive": 3, "unsafe": 3, "insufficient": 2})
        self.assertEqual(result.control_counts["whole_order_return"], {"positive": 1, "unsafe": 1, "insufficient": 1})
        self.assertEqual(result.control_counts["service_handoff"], {"positive": 1, "unsafe": 1, "insufficient": 2})
        self.assertEqual(len(result.independent_groups), 3)

    def test_feedback_contaminates_entire_group_and_cross_split_is_rejected(self):
        ledger = module(self, "ledger")
        supplied = rows()[:3]
        supplied[0]["feedback"] = True
        result = ledger.inspect_case_ledger(supplied)
        self.assertEqual(tuple(p.effective_split for p in result.positions), ("validation",) * 3)
        supplied[1]["split"] = "validation"
        self.assertTrue(any(f.reason == "cross_split_group" for f in ledger.validate_case_ledger(supplied).findings))
        supplied[1]["split"] = "protected"
        self.assertEqual(ledger.inspect_case_ledger(supplied).positions[1].status, "invalid")

    def test_nonfinite_duplicate_json_and_bound_are_not_silently_truncated(self):
        ledger = module(self, "ledger")
        for invalid in (b'{"case_id":"a","case_id":"b"}', {"case_id": "a", "value": float("nan")}):
            result = ledger.inspect_case_ledger([invalid])
            self.assertEqual(result.audit.total_cases, 1)
            self.assertEqual(result.positions[0].status, "invalid")
        with self.assertRaises(ValueError):
            ledger.validate_case_ledger([None] * 257)

    def test_excluded_and_conflicting_duplicate_metadata_stay_in_inventory(self):
        ledger = module(self, "ledger")
        from proofkey.identity import fingerprint
        supplied = rows()[:2]
        supplied[1]["reference"]["exclusion"] = "unimplemented-driver"
        ref = supplied[1]["reference"]
        ref["reference_hash"] = fingerprint({k: ref[k] for k in ("case_id", "input_hash", "source_hash", "required_behavior", "authority_assumptions", "provenance", "ambiguity", "exclusion")})
        duplicate = json.loads(json.dumps(supplied[0]))
        duplicate["split_seed"] = 1402
        result = ledger.inspect_case_ledger(supplied + [duplicate])
        self.assertEqual(result.audit.total_cases, 3)
        self.assertEqual(result.audit.excluded_cases, 1)
        self.assertEqual(result.audit.included_cases, 2)
        self.assertEqual(len(result.positions), 3)
        self.assertTrue(any(f.reason == "conflicting_duplicate_metadata" for f in result.audit.findings))


class CoverageTests(unittest.TestCase):
    def test_recursive_return_validation_retains_public_batch_and_later_positions(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        row = c.CaseRow.model_validate(rows()[0])
        cycle = {}
        cycle["private"] = cycle
        deep = None
        for _ in range(1100):
            deep = {"private": deep}
        deep_bytes = b'{"private":' * 1100 + b"null" + b"}" * 1100
        valid = b'{ "effects": {}, "forbidden_effects": [] }'
        for name, returned in (("cycle", cycle), ("deep_mapping", deep), ("deep_bytes", deep_bytes)):
            with self.subTest(name=name):
                sequence = iter((valid, returned, valid, None))
                try:
                    batch = coverage.capture_executions((row,), candidate_hash="1" * 64,
                        execute=lambda case: next(sequence), repeats=4)
                except RecursionError:
                    self.fail("Returned validation lost the declared execution batch")
                self.assertEqual(len(batch.executions), 4)
                self.assertEqual(tuple(p.outcome for p in batch.positions),
                    ("valid_output", "invalid_output", "valid_output", "no_output"))
                self.assertEqual(tuple((p.ordinal, p.repetition) for p in batch.positions), ((0, 0), (1, 1), (2, 2), (3, 3)))
                self.assertEqual(batch.executions[2].output_bytes, valid)
                failed = batch.positions[1]
                self.assertEqual(failed.observation.case_id, row.case_id)
                self.assertEqual(failed.observation.source_hash, row.source_hash)
                self.assertEqual(failed.observation.candidate_hash, "1" * 64)
                self.assertEqual(failed.observation.error, b"Invalid observed assessment output")
                self.assertIsNone(failed.observation.output_bytes)
                self.assertTrue(failed.validation_error)
                self.assertEqual(failed.returned_bytes, deep_bytes if name == "deep_bytes" else None)
                self.assertEqual(failed.returned_hash, c.digest_bytes(deep_bytes) if name == "deep_bytes" else None)
        control = coverage.capture_control("known_bad", (row,), candidate_hash="2" * 64,
            execute=lambda case: cycle, grader_descriptor={"route": "offline"},
            runner=lambda output, order: self.fail("Unrepresentable return reached grader"), repeats=2, seed=1401)
        self.assertIsNone(control.batch)
        self.assertEqual(len(control.execution_batch.positions), 2)
        self.assertTrue(all(p.outcome == "invalid_output" and p.validation_error
            and p.returned_bytes is None and p.returned_hash is None for p in control.execution_batch.positions))
        coverage, c, cases, controls = self._anchored_controls()
        result = coverage.qualify_grader_details(controls[0].batch, controls[:1] + (control,) + controls[2:])
        self.assertEqual(result.receipt.status, "incomplete")
        self.assertIn("control_execution_incomplete", result.receipt.qualification_limits)
        self.assertIn("control_grading_incomplete", result.receipt.qualification_limits)
        with self.assertRaises(KeyboardInterrupt):
            coverage.capture_executions((row,), candidate_hash="1" * 64,
                execute=lambda case: (_ for _ in ()).throw(KeyboardInterrupt()), repeats=2)

    def _anchored_controls(self, bad_runner=None):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        cases = tuple(c.CaseRow.model_validate(r) for r in (rows()[0], rows()[5]))
        descriptor = {"route": "offline", "prompt": "v1"}
        def execute(row):
            return {"effects": {name: {"status": effect.status, "postcondition": dict(effect.postcondition), "evidence_refs": ["fixture"]} for name, effect in row.reference.required_behavior.items()}, "forbidden_effects": []}
        def grade(output, order):
            return {"verdict": "correct" if json.loads(output)["effects"] else "incorrect", "score": 1.0 if json.loads(output)["effects"] else 0.0}
        controls = tuple(coverage.capture_control(kind, cases, candidate_hash=candidate * 64,
            execute=execute if kind in {"known_good", "improved"} else lambda row: {"effects": {}, "forbidden_effects": []},
            grader_descriptor=descriptor, runner=bad_runner if kind == "known_bad" and bad_runner else grade,
            repeats=2, seed=1401) for kind, candidate in (("known_good", "1"), ("known_bad", "2"), ("disabled", "2"), ("improved", "1")))
        return coverage, c, cases, controls + (coverage.ControlEvidence("independent_execution",
            coverage.capture_executions(cases, candidate_hash="1" * 64, execute=execute, repeats=2)),)

    def test_control_grading_failures_keep_all_positions_and_force_incomplete(self):
        for failure in ("exception", "abstain", "missing_score"):
            with self.subTest(failure=failure):
                calls = iter(range(4))
                def grade(output, order):
                    if next(calls) == 1:
                        if failure == "exception":
                            raise RuntimeError("private-control-grader-error")
                        return {"verdict": "abstain" if failure == "abstain" else "incorrect", "score": None}
                    return {"verdict": "incorrect", "score": 0.0}
                coverage, c, cases, controls = self._anchored_controls(grade)
                result = coverage.qualify_grader_details(controls[0].batch, controls)
                self.assertEqual(result.receipt.status, "incomplete")
                self.assertIn("control_grading_incomplete", result.receipt.qualification_limits)
                self.assertEqual(result.errors, 1 if failure == "exception" else 0)
                self.assertEqual(result.abstentions, 1 if failure == "abstain" else 0)
                self.assertEqual(sum(e.denominator for e in result.judgment_evidence), 20)
                evidence = next(e for e in result.judgment_evidence if e.kind == "known_bad")
                self.assertEqual(evidence.expected_positions, 4)
                self.assertEqual(evidence.batch, controls[1].batch)
                self.assertEqual(evidence.missing_scores, 1)
                if failure == "exception":
                    self.assertEqual(evidence.batch.judgments[1].error, b"RuntimeError:private-control-grader-error")
                self.assertEqual(len(result.receipt.assessment_hashes), 20)
                self.assertNotIn("private-control-grader-error", result.receipt.model_dump_json())

    def test_control_order_and_repetition_inventory_cannot_use_remaining_scores(self):
        from dataclasses import replace
        for defect in ("single_order", "duplicate_repetition", "missing_position", "missing_case"):
            with self.subTest(defect=defect):
                coverage, c, cases, controls = self._anchored_controls()
                bad = controls[1].batch
                judgments = bad.judgments
                if defect == "single_order":
                    judgments = tuple(replace(j, order=judgments[0].order) for j in judgments)
                elif defect == "duplicate_repetition":
                    judgments = tuple(replace(j, repetition=0) for j in judgments)
                elif defect == "missing_case":
                    judgments = tuple(j for j in judgments if j.observation.case_id == cases[0].case_id)
                else:
                    judgments = judgments[:-1]
                controls = controls[:1] + (replace(controls[1], batch=replace(bad, judgments=judgments)),) + controls[2:]
                result = coverage.qualify_grader_details(controls[0].batch, controls)
                self.assertEqual(result.receipt.status, "incomplete")
                self.assertIn("control_grading_incomplete", result.receipt.qualification_limits)
                evidence = next(e for e in result.judgment_evidence if e.kind == "known_bad")
                self.assertEqual(evidence.expected_positions, 4)
                self.assertEqual(evidence.denominator, len(judgments))
                self.assertEqual(evidence.batch.judgments, judgments)

    def test_execution_capture_retains_invalid_raw_bytes_and_distinct_positions(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        labels = module(self, "labels")
        row = c.CaseRow.model_validate(rows()[0])
        malformed = b'{"effects":{},"forbidden_effects":[],"unexpected":"private-invalid-output"}'
        sequence = iter([malformed, None, RuntimeError("private-callback-error"), b'{"broken":'])
        def execute(case):
            value = next(sequence)
            if isinstance(value, Exception):
                raise value
            return value
        batch = coverage.capture_executions((row,), candidate_hash="1" * 64, execute=execute, repeats=4)
        self.assertEqual(batch.executions[0].error, b"Invalid observed assessment output")
        self.assertEqual(tuple(p.outcome for p in batch.positions), ("invalid_output", "no_output", "callback_error", "invalid_output"))
        self.assertEqual(tuple((p.ordinal, p.repetition) for p in batch.positions), ((0, 0), (1, 1), (2, 2), (3, 3)))
        self.assertEqual(batch.positions[0].returned_bytes, malformed)
        self.assertEqual(batch.positions[0].returned_hash, c.digest_bytes(malformed))
        self.assertEqual(batch.positions[3].returned_bytes, b'{"broken":')
        self.assertEqual(tuple(p.observation for p in batch.positions), batch.executions)
        self.assertTrue(all(o.case_id == row.case_id and o.source_hash == row.source_hash for o in batch.executions))
        self.assertIsNone(batch.executions[0].output_bytes)
        self.assertEqual(batch.executions[0].error, b"Invalid observed assessment output")
        self.assertEqual(batch.executions[2].error, b"RuntimeError:private-callback-error")
        assessment = labels.score_case(batch.executions[0], row.reference)
        self.assertTrue(all(v.verdict == "unassessed" for v in assessment.effect_verdicts.values()))
        self.assertNotIn("private-invalid-output", assessment.model_dump_json())
        control = coverage.capture_control("known_bad", (row,), candidate_hash="2" * 64, execute=lambda case: malformed,
            grader_descriptor={"route": "offline"}, runner=lambda output, order: self.fail("Invalid output reached grader"), repeats=2, seed=1401)
        self.assertIsNone(control.batch)
        self.assertEqual(tuple(p.returned_bytes for p in control.execution_batch.positions), (malformed, malformed))
        self.assertEqual(control.grading_repetitions, 2)
        coverage, c, cases, controls = self._anchored_controls()
        invalid = coverage.capture_control("known_bad", cases, candidate_hash="2" * 64, execute=lambda case: malformed,
            grader_descriptor={"route": "offline", "prompt": "v1"}, runner=lambda output, order: self.fail("Invalid output reached grader"), repeats=2, seed=1401)
        result = coverage.qualify_grader_details(controls[0].batch, controls[:1] + (invalid,) + controls[2:])
        evidence = next(e for e in result.judgment_evidence if e.kind == "known_bad")
        self.assertEqual(result.receipt.status, "incomplete")
        self.assertEqual(evidence.expected_positions, 4)
        self.assertEqual(evidence.denominator, 0)
        self.assertIn("grading_batch_missing", evidence.limits)
        self.assertEqual(len(invalid.execution_batch.positions), 4)

    def test_execution_capture_keeps_exact_valid_bytes_and_bounds_invalid_storage(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        row = c.CaseRow.model_validate(rows()[0])
        valid = b'{ "forbidden_effects": [], "effects": {} }'
        unsupported = {"effects": {}, "forbidden_effects": [], "extra": ["frozen-private-return"]}
        values = iter([valid, unsupported, b"x" * c.MAX_BYTES, b"x" * (c.MAX_BYTES + 1)])
        batch = coverage.capture_executions((row,), candidate_hash="1" * 64, execute=lambda case: next(values), repeats=4)
        unsupported["extra"].append("caller-mutated")
        self.assertEqual(batch.positions[0].outcome, "valid_output")
        self.assertEqual(batch.executions[0].output_bytes, valid)
        self.assertEqual(batch.positions[0].returned_bytes, valid)
        self.assertEqual(json.loads(batch.positions[1].returned_bytes)["extra"], ["frozen-private-return"])
        self.assertEqual(len(batch.positions[2].returned_bytes), c.MAX_BYTES)
        self.assertEqual(batch.positions[2].returned_hash, c.digest_bytes(b"x" * c.MAX_BYTES))
        self.assertEqual(batch.positions[3].outcome, "invalid_output")
        self.assertIsNone(batch.positions[3].returned_bytes)
        self.assertIsNone(batch.positions[3].returned_hash)
        self.assertTrue(all(o.output_bytes is None and o.error == b"Invalid observed assessment output" for o in batch.executions[1:]))

    def test_unknown_grader_flag_cannot_enter_host_registration(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        row = c.CaseRow.model_validate(rows()[0])
        observation = c.Observation.capture(row, "1" * 64, output={"effects": {}, "forbidden_effects": []})
        with self.assertRaises(ValueError):
            coverage.capture_judgments([observation], grader_descriptor={"route": "offline", "actual": True}, runner=lambda output, order: {"verdict": "correct", "score": 1.0}, repeats=2, seed=1401)

    def test_universal_escalation_fails_both_positive_families_and_keeps_errors(self):
        c = module(self, "contracts")
        coverage = module(self, "coverage")
        labels = module(self, "labels")
        ledger = module(self, "ledger").inspect_case_ledger(rows())
        positions = []
        for p in ledger.positions:
            observed = c.Observation.capture(p.row, "1" * 64, output={"effects": {}, "forbidden_effects": []})
            positions.append(c.AssessmentPosition(ordinal=p.ordinal, assessment=labels.score_case(observed, p.row.reference)))
        positions[0] = c.AssessmentPosition(ordinal=0, error=b"raw-error-retained")
        report = coverage.summarize_coverage(ledger, positions)
        self.assertEqual(report.total_positions, 15)
        self.assertEqual(report.errors, 1)
        self.assertFalse(report.positive_families["rescheduling"])
        self.assertFalse(report.positive_families["whole_order_return"])
        self.assertEqual(report.positions[0].error, b"raw-error-retained")
        self.assertEqual(coverage.summarize_coverage(ledger, []).missing_outputs, 15)
        with self.assertRaises(ValueError):
            coverage.summarize_coverage(ledger, positions + [positions[0]])

    def test_grader_requires_runner_evidence_and_separates_execution_variability(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        row = c.CaseRow.model_validate(rows()[0])
        observation = c.Observation.capture(row, "1" * 64, output={"effects": {}, "forbidden_effects": []})
        batch = coverage.capture_judgments([observation], grader_descriptor={"route": "offline", "observed_model": None, "prompt": "v1"}, runner=lambda output, order: {"verdict": "abstain", "score": None}, repeats=4, seed=1401)
        summary = coverage.qualify_grader_details(batch, controls=())
        self.assertEqual(summary.abstentions, 4)
        self.assertEqual(summary.independent_groups, 1)
        self.assertEqual(summary.receipt.status, "incomplete")
        self.assertIn("sensitivity_controls_missing", summary.receipt.qualification_limits)
        self.assertIn("independent_execution_missing", summary.receipt.qualification_limits)
        self.assertEqual(coverage.qualify_grader(batch, ()).status, "incomplete")
        self.assertEqual(len({j.output_hash for j in batch.judgments}), 1)
        self.assertEqual(len({j.order for j in batch.judgments}), 2)
        with self.assertRaises(TypeError):
            coverage.qualify_grader([{"verdict": "good", "actual": True}], ())

    def test_flips_spread_error_history_and_controls_never_mint_calibration(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        observations = [c.Observation.capture(c.CaseRow.model_validate(r), "1" * 64, output={"effects": {}, "forbidden_effects": []}) for r in (rows()[0], rows()[5])]
        sequence = iter([{"verdict": "correct", "score": 1.0}, {"verdict": "incorrect", "score": 0.0}, {"verdict": "abstain", "score": None}, {"verdict": "correct", "score": 1.0}])
        batch = coverage.capture_judgments(observations, grader_descriptor={"route": "offline", "model": None}, runner=lambda output, order: next(sequence), repeats=2, seed=1401)
        summary = coverage.qualify_grader_details(batch, ())
        self.assertEqual(summary.verdict_flips, 2)
        self.assertEqual(summary.score_spread, 1.0)
        self.assertEqual(summary.abstentions, 1)
        self.assertNotEqual(summary.receipt.status, "qualified")
        def fail(output, order):
            raise RuntimeError("raw-grader-error")
        failures = coverage.capture_judgments(observations, grader_descriptor={"route": "offline"}, runner=fail, repeats=2, seed=1401)
        self.assertEqual(len(failures.judgments), 4)
        self.assertEqual(failures.judgments[0].error, b"RuntimeError:raw-grader-error")

    def test_paired_controls_capture_group_sensitivity_without_inventing_power(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        observations = [c.Observation.capture(c.CaseRow.model_validate(r), "1" * 64, output={"effects": {}, "forbidden_effects": []}) for r in (rows()[0], rows()[5])]
        descriptor = {"route": "offline", "observed_model": None, "prompt": "v1"}
        def batch(score):
            return coverage.capture_judgments(observations, grader_descriptor=descriptor, runner=lambda output, order: {"verdict": "correct" if score else "incorrect", "score": float(score)}, repeats=2, seed=1401)
        primary = batch(1)
        controls = tuple(coverage.ControlEvidence(kind, batch(value)) for kind, value in (("known_good", 1), ("known_bad", 0), ("disabled", 0), ("improved", 1), ("independent_execution", 1)))
        result = coverage.qualify_grader_details(primary, controls)
        self.assertEqual(result.paired_group_effects, (("syn-rescheduling", 1.0), ("syn-whole_order_return", 1.0)))
        self.assertEqual(result.receipt.status, "incomplete")
        self.assertIn("statistical_power_unestablished", result.receipt.qualification_limits)
        self.assertIn("independent_execution_origin_unattested", result.receipt.qualification_limits)
        descriptor["prompt"] = "changed"
        self.assertNotIn(b"changed", primary.grader_bytes)

    def test_actual_captured_execution_and_anchored_control_outputs_separate_from_grading(self):
        coverage = module(self, "coverage")
        self.assertTrue(hasattr(coverage, "capture_control"), "Captured control runner is absent")
        c = module(self, "contracts")
        cases = tuple(c.CaseRow.model_validate(r) for r in (rows()[0], rows()[5]))
        descriptor = {"route": "offline", "observed_model": None, "prompt": "v1"}
        def execute(row):
            return {"effects": {name: {"status": effect.status, "postcondition": dict(effect.postcondition), "evidence_refs": ["independent-fixture-evidence"]} for name, effect in row.reference.required_behavior.items()}, "forbidden_effects": []}
        def bad(row):
            return {"effects": {}, "forbidden_effects": []}
        def captured(kind, candidate, callback):
            return coverage.capture_control(kind, cases, candidate_hash=candidate, execute=callback,
                grader_descriptor=descriptor, runner=lambda output, order: {"verdict": "correct" if json.loads(output)["effects"] else "incorrect", "score": 1.0 if json.loads(output)["effects"] else 0.0}, repeats=2, seed=1401)
        good = captured("known_good", "1" * 64, execute)
        controls = (good, captured("known_bad", "2" * 64, bad), captured("disabled", "2" * 64, bad), captured("improved", "1" * 64, execute),
                    coverage.ControlEvidence("independent_execution", coverage.capture_executions(cases, candidate_hash="1" * 64, execute=execute, repeats=2)))
        result = coverage.qualify_grader_details(good.batch, controls)
        self.assertEqual(result.execution_disagreements, 0)
        self.assertEqual(result.paired_group_effects, (("syn-rescheduling", 1.0), ("syn-whole_order_return", 1.0)))
        self.assertEqual(result.receipt.status, "rehearsal")
        self.assertIn("provisional_reference", result.receipt.qualification_limits)
        sequence = iter([execute(cases[0]), bad(cases[0]), execute(cases[1]), bad(cases[1])])
        varied = coverage.capture_executions(cases, candidate_hash="1" * 64, execute=lambda row: next(sequence), repeats=2)
        varied_result = coverage.qualify_grader_details(good.batch, controls[:-1] + (coverage.ControlEvidence("independent_execution", varied),))
        self.assertEqual(varied_result.execution_disagreements, 2)
        self.assertEqual(varied_result.verdict_flips, 0)

    def test_control_secondary_execution_error_is_retained_as_incomplete_evidence(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        row = c.CaseRow.model_validate(rows()[0])
        calls = iter([False, True])
        def execute(case):
            if next(calls):
                raise RuntimeError("secondary-control-error")
            return {"effects": {"reschedule": {"status": "verified", "postcondition": {"slot": "S1"}, "evidence_refs": ["fixture"]}}, "forbidden_effects": []}
        control = coverage.capture_control("known_good", (row,), candidate_hash="1" * 64, execute=execute,
            grader_descriptor={"route": "offline"}, runner=lambda output, order: {"verdict": "correct", "score": 1.0}, repeats=2, seed=1401)
        self.assertTrue(hasattr(control, "execution_batch"), "Secondary control execution was dropped")
        self.assertEqual(len(control.execution_batch.executions), 2)
        self.assertEqual(control.execution_batch.executions[1].error, b"RuntimeError:secondary-control-error")

    def test_no_output_control_returns_ungraded_retained_batch(self):
        coverage = module(self, "coverage")
        c = module(self, "contracts")
        row = c.CaseRow.model_validate(rows()[0])
        try:
            control = coverage.capture_control("known_bad", (row,), candidate_hash="1" * 64, execute=lambda case: None,
                grader_descriptor={"route": "offline"}, runner=lambda output, order: {"verdict": "correct", "score": 1.0}, repeats=2, seed=1401)
        except ValueError:
            self.fail("Missing control output was dropped instead of retained")
        self.assertIsNone(control.batch)
        self.assertEqual(len(control.execution_batch.executions), 2)
        self.assertTrue(all(o.output_bytes is None for o in control.execution_batch.executions))


class DrillTests(unittest.TestCase):
    def test_measured_clock_includes_setup_execution_export_and_every_unfinished_position(self):
        drills = module(self, "drills")
        c = module(self, "contracts")
        packet = c.DrillPacket.capture(["one", "one", "error", "unfinished"], baseline={"baseline": "v1"})
        def execute(position):
            time.sleep(0.002)
            if position == "error":
                raise RuntimeError("raw-runner-error")
            return None if position == "unfinished" else {"output": "synthetic"}
        runner = drills.DrillRunner({"source": "test", "dependencies": [], "profile": "fixture", "process": "v1", "policy": "v1", "prompts": []}, setup=lambda: time.sleep(0.002), execute=execute, export=lambda results: time.sleep(0.002))
        receipt = drills.run_drill("pilot", packet, runner, drills.HostClock())
        result = runner.results[-1]
        self.assertEqual(result.receipt, receipt)
        self.assertGreaterEqual(receipt.wall_seconds, 0.01)
        self.assertEqual(len(result.positions), 4)
        self.assertEqual(result.positions[2].error, b"RuntimeError:raw-runner-error")
        self.assertEqual(tuple(p.status for p in result.positions), ("completed", "completed", "error", "unfinished"))
        self.assertEqual(receipt.partial_case_ids, ["error", "unfinished"])
        self.assertEqual(receipt.mode, "rehearsal")
        self.assertIn("outcomes_unverified", result.unmet_gates)
        self.assertIn("actual_human_provider_evidence_missing", result.unmet_gates)
        self.assertEqual(receipt.workload_hash, packet.packet_hash)
        with self.assertRaises(TypeError):
            drills.run_drill("pilot", packet, runner, object())

    def test_timer_only_and_setup_export_failure_never_become_completed_drills(self):
        drills = module(self, "drills")
        c = module(self, "contracts")
        packet = c.DrillPacket.capture(["x", "y"], baseline={"baseline": "v1"})
        def fail():
            raise RuntimeError("setup-failed")
        runner = drills.DrillRunner({"source": "fixture", "dependencies": [], "profile": "v1", "process": "v1", "policy": "v1", "prompts": []}, setup=fail, execute=lambda position: {}, export=lambda result: None)
        receipt = drills.run_drill("B", packet, runner, drills.HostClock())
        self.assertEqual(receipt.partial_case_ids, ["x", "y"])
        self.assertEqual(len(runner.results[-1].positions), 2)
        self.assertIn("declared_timed_workload_unmet", runner.results[-1].unmet_gates)
        self.assertNotIn("pass", receipt.model_dump())

    def test_declared_wait_is_measured_and_export_failures_retain_raw_history(self):
        drills = module(self, "drills")
        c = module(self, "contracts")
        clock = drills.HostClock()
        packet = c.DrillPacket.capture(["x"], baseline={"baseline": "v1"})
        descriptor = {"source": "fixture", "dependencies": [], "profile": "v1", "process": "v1", "policy": "v1", "prompts": []}
        def execute(position):
            clock.wait("x", "provider", lambda: time.sleep(0.003))
            return {"completed": "fixture"}
        def export(results):
            raise RuntimeError("raw-export-error")
        runner = drills.DrillRunner(descriptor, setup=lambda: None, execute=execute, export=export)
        descriptor["policy"] = "changed"
        receipt = drills.run_drill("pilot", packet, runner, clock)
        self.assertEqual(len(receipt.waits), 1)
        self.assertGreaterEqual((receipt.waits[0].ended_at - receipt.waits[0].started_at).total_seconds(), 0.002)
        self.assertLess(receipt.active_seconds, receipt.wall_seconds)
        self.assertEqual(runner.results[-1].export_error, b"RuntimeError:raw-export-error")
        self.assertIn("export_unverified", runner.results[-1].unmet_gates)
        self.assertNotIn(b"changed", runner.results[-1].candidate_bytes)

    def test_drill_packet_freezes_full_case_input_reference_and_candidate_registration(self):
        drills = module(self, "drills")
        c = module(self, "contracts")
        supplied = rows()[0]
        self.assertIn("case_bytes", c.DrillPacket.__annotations__, "Full workload snapshots are absent")
        packet = c.DrillPacket.capture([c.CaseRow.model_validate(supplied)], baseline={"baseline": "v1"})
        frozen = packet.case_bytes[0]
        supplied["input"]["arguments"]["window_start"] = "changed"
        self.assertNotIn(b"changed", frozen)
        self.assertEqual(json.loads(frozen)["reference"]["input_hash"], json.loads(frozen)["input_hash"])
        runner = drills.DrillRunner({"source": "fixture", "dependencies": [], "profile": "v1", "process": "v1", "policy": "v1", "prompts": []}, setup=lambda: None, execute=lambda position: {"fixture": "result"}, export=lambda result: {"exported": len(result)})
        receipt = drills.run_drill("pilot", packet, runner, drills.HostClock())
        self.assertEqual(len(runner.results[-1].positions), 1)
        self.assertEqual(receipt.workload_hash, packet.packet_hash)
        self.assertNotIn("workload_content_unavailable", runner.results[-1].unmet_gates)
        with self.assertRaises((AttributeError, TypeError)):
            runner._candidate_bytes = b"forged-candidate"
