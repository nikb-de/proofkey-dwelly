"""Content-free receipt projection: independent outcomes and hostile boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from proofkey.bootstrap import CliReceiptV1
from proofkey.contracts import CaseResult, StopState, VerificationResult
from proofkey.host_contracts import (BatchInputV1, BatchPositionInventoryV1,
    BatchPositionReceiptV1, BatchRunReceiptV1, CommandReceiptV1)
from proofkey.identity import fingerprint
from proofkey.execution_trace import (TraceError, build_execution_trace,
    parse_cli_receipt, render_trace_json, render_trace_markdown, _bounded_output)
from test_batch_contracts import window, START
from test_cli import request


def batch_receipt(count=1, commands=None):
    positions = tuple(BatchPositionReceiptV1(inventory=BatchPositionInventoryV1(
        ordinal=i, supplied_id_shape="string", supplied_case_id=f"case-{i}")) for i in range(count))
    if commands is not None:
        positions = tuple(commands)
    run = BatchRunReceiptV1(run_id="a" * 32, input_outcome="admitted",
        input=BatchInputV1(encoding="canonical_json_array_v1", input_hash="b" * 64,
            input_bytes=2, position_count=count), position_count=count, positions=positions,
        release_id="registered", mode="synthetic_replay", clock_mode="synthetic_replay",
        window=window(), outcome="deadline_exceeded", started_at=START, finished_at=START,
        elapsed_seconds=0.0, publication_seconds=0.0, overrun_seconds=0.0)
    return CliReceiptV1(run=run)


def real_receipt(command="run", denied=False):
    """Actual offline executable, independent of another TestCase lifecycle."""
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "input.json"
        body = request()
        if denied:
            body["principal_id"] = "wrong-principal"
        source.write_text(json.dumps(body if command == "run" else [body, {}, 42]), encoding="utf-8")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        actual = subprocess.run([sys.executable, "-m", "proofkey.cli", command,
            "--input", str(source)], cwd=folder, env=env, capture_output=True, timeout=20)
        if actual.stderr:
            raise AssertionError(actual.stderr)
        return CliReceiptV1.model_validate_json(actual.stdout)


class ExecutionTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real = real_receipt()
        cls.denied = real_receipt(denied=True)
        cls.batch = real_receipt("batch")

    def wire(self, receipt):
        return json.loads(render_trace_json(build_execution_trace(receipt)))

    def invalid(self, receipt, code="invalid_receipt"):
        with self.assertRaises(TraceError) as caught:
            build_execution_trace(receipt)
        self.assertEqual(str(caught.exception), code)

    def test_bootstrap_failure_is_not_execution(self):
        wire = self.wire(CliReceiptV1(failure="invalid_input"))
        self.assertEqual(wire["provenance"], "unverified_receipt_projection")
        self.assertEqual(wire["transport_dispatch"], "unknown")
        self.assertEqual(wire["original_readback_observation"], "not_observed")
        self.assertIs(wire["publication_files_checked"], False)
        self.assertEqual(wire["positions"], [])
        self.assertEqual(wire["bootstrap_failure"], "invalid_input")
        self.assertIsNone(wire["shutdown"])

    def test_duplicate_keys_are_rejected_without_echo(self):
        with self.assertRaises(TraceError) as caught:
            parse_cli_receipt(b'{"failure":"invalid_input","failure":"SECRET"}')
        self.assertEqual(str(caught.exception), "invalid_receipt")

    def test_real_command_and_batch_preserve_all_positions_and_stages(self):
        wire = self.wire(self.real)
        self.assertEqual(wire["position_count"], 1)
        row = wire["positions"][0]
        self.assertEqual((row["ordinal"], row["case"], row["command"]), (0, "case-1", "command-1"))
        self.assertEqual((row["admission_status"], row["host_outcome"], row["host_started"],
            row["access_status"], row["export_outcome"]), ("joined", "result", True, "authorized", "written"))
        self.assertEqual(row["effects"], [{"effect": "effect-1", "status": "verified", "basis": "receipt_reported"}])
        self.assertEqual(wire["publication_status"], "committed")
        self.assertTrue(wire["shutdown"]["owner_closed"])
        batch = self.wire(self.batch)
        self.assertEqual(batch["position_count"], 3)
        self.assertEqual([r["ordinal"] for r in batch["positions"]], [0, 1, 2])
        self.assertEqual([r["execution_outcome"] for r in batch["positions"]], ["result", "invalid_request", "invalid_request"])
        self.assertEqual([r["access_status"] for r in batch["positions"]], ["authorized", "unknown", "unknown"])
        self.assertEqual([r["export_outcome"] for r in batch["positions"]], ["written", "not_attempted", "not_attempted"])
        self.assertEqual(self.wire(parse_cli_receipt(self.real.model_dump_json().encode())), wire)

    def test_started_denial_is_not_authorized_and_pending_is_not_success(self):
        denied = self.wire(self.denied)["positions"][0]
        self.assertTrue(denied["host_started"])
        self.assertEqual(denied["access_status"], "denied")
        self.assertEqual(denied["effects"], [])
        command = CommandReceiptV1(command_id="c" * 32, command_tag="run", release_id="registered",
            mode="synthetic_replay", clock_mode="synthetic_replay", outcome="started_pending",
            started_at=START, inventory_status="partial")
        # Pending/unresolved must be supplied together at construction to satisfy the real schema.
        base = batch_receipt(2).run
        fields = {name: getattr(base, name) for name in type(base).model_fields}
        fields.update(positions=(BatchPositionReceiptV1(inventory=BatchPositionInventoryV1(
            ordinal=0, supplied_id_shape="string", supplied_case_id="same"), command=command,
            execution_outcome="deadline_exceeded", admission_status="joined"),
            BatchPositionReceiptV1(inventory=BatchPositionInventoryV1(ordinal=1,
                supplied_id_shape="string", supplied_case_id="same"), admission_status="unresolved")),
            pending_command_ids=(command.command_id,), unresolved_admission_ordinals=(1,))
        wire = self.wire(CliReceiptV1(run=BatchRunReceiptV1(**fields)))
        self.assertEqual(wire["unresolved_ordinals"], [1])
        self.assertEqual(wire["pending_commands"], ["command-1"])
        self.assertEqual([r["case"] for r in wire["positions"]], ["case-1", "case-1"])
        self.assertEqual(wire["positions"][0]["access_status"], "unknown")
        self.assertEqual(wire["positions"][1]["admission_status"], "unresolved")

    def test_content_canaries_never_survive_either_renderer(self):
        data = json.loads(self.real.model_dump_json())
        result = data["run"]["command"]["result"]
        canary = 'SECRET-<script>[click](https://secret.invalid)'
        result["rationale"] = canary
        result["evidence_refs"] = [canary]
        result["policy_refs"] = [canary]
        old_effect = next(iter(result["effects"].values()))
        old_effect.update(object_id=canary, action_id=canary, evidence_refs=[canary],
            postcondition={canary: [canary]}, reason=canary)
        result["effects"] = {canary: old_effect}
        result["binding"].update(case_id=canary, object_id=canary, principal_id=canary,
            request_id=canary, generation=canary, request_revision=canary, consent_revision=canary)
        data["run"]["input"]["supplied_case_id"] = canary
        data["run"]["export"]["actual_receipt"].update(supplied_case_id=canary, output_name=canary)
        data["run"]["input"]["release_id"] = canary
        data["run"]["command"]["release_id"] = canary
        data["shutdown"]["cancelled_command_ids"] = [canary]
        receipt = parse_cli_receipt(json.dumps(data).encode())
        trace = build_execution_trace(receipt)
        for text in (render_trace_json(trace), render_trace_markdown(trace)):
            self.assertNotIn("SECRET", text)
            self.assertNotIn("https://", text)
            self.assertNotIn(result["fingerprint"], text)
        dict.__setitem__(receipt.run.command.result.effects, "new", old_effect)
        self.assertEqual(len(trace.positions[0].effects), 1)

    def test_typed_bypasses_subclasses_cycles_and_wrong_types_rejected(self):
        class SubReceipt(CliReceiptV1):
            pass
        self.invalid(SubReceipt())
        self.invalid({})
        for field, bad in (("rationale", "SECRET"), ("historical", True),
                           ("effects", {"SECRET": VerificationResult(status="pending")})):
            bad_result = CaseResult.model_construct(status="denied", correlation_id="case", reason="denied", **{field: bad})
            receipt = self.denied.model_copy(deep=True)
            object.__setattr__(receipt.run.command, "result", bad_result)
            self.invalid(receipt)
        for bad in (float("nan"), float("inf"), True, -1.0, "1"):
            receipt = self.real.model_copy(deep=True)
            object.__setattr__(receipt.run, "elapsed_seconds", bad)
            self.invalid(receipt)
        receipt = self.real.model_copy(deep=True)
        receipt.run.command.__dict__["SECRET"] = "SECRET"
        self.invalid(receipt)
        receipt = self.real.model_copy(deep=True)
        object.__setattr__(receipt.run.command, "release_id", "different")
        self.invalid(receipt)
        receipt = self.real.model_copy(deep=True)
        cycle = {}
        cycle["self"] = cycle
        object.__setattr__(receipt.run.command.result, "effects", cycle)
        self.invalid(receipt)

    def test_parser_bytes_utf8_nonfinite_depth_size_and_node_bounds(self):
        for value in ("{}", bytearray(b"{}"), b"\xff", b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e400}'):
            with self.subTest(value=type(value)), self.assertRaises(TraceError) as caught:
                parse_cli_receipt(value)
            self.assertEqual(str(caught.exception), "invalid_receipt")
        valid = b'{"failure":"invalid_input"}'
        self.assertEqual(parse_cli_receipt(valid + b" " * (1048576 - len(valid))).failure, "invalid_input")
        for payload in (valid + b" " * (1048577 - len(valid)), b"[" * 65 + b"]" * 65,
                        b"[" + b"0," * 50000 + b"0]"):
            with self.assertRaises(TraceError) as caught:
                parse_cli_receipt(payload)
            self.assertEqual(str(caught.exception), "trace_limit_exceeded")
        # Depth 64 is accepted by the guard and reaches schema validation.
        with self.assertRaises(TraceError) as caught:
            parse_cli_receipt(b"[" * 64 + b"]" * 64)
        self.assertEqual(str(caught.exception), "invalid_receipt")

    def test_node_and_typed_depth_exact_boundaries(self):
        # root + key + array + 49,997 scalars = exactly 50,000 visited nodes.
        for count, expected in ((49997, "invalid_receipt"), (49998, "trace_limit_exceeded")):
            data = b'{"x":[' + b"0," * (count - 1) + b"0]}"
            with self.assertRaises(TraceError) as caught:
                parse_cli_receipt(data)
            self.assertEqual(str(caught.exception), expected)
        for count, accepted in ((57, True), (58, False)):
            nested = 0
            for _ in range(count):
                nested = [nested]
            receipt = self.real.model_copy(deep=True)
            effect = VerificationResult(status="pending", postcondition={"SECRET": nested})
            object.__setattr__(receipt.run.command.result, "effects", {"SECRET": effect})
            if accepted:
                self.assertEqual(self.wire(receipt)["positions"][0]["effects"][0]["status"], "pending")
            else:
                self.invalid(receipt, "trace_limit_exceeded")

    def many_effects(self, total):
        positions = []
        for index, offset in enumerate(range(0, total, 256)):
            case_id = f"case-{index}"
            source = self.real.run.command
            result = source.result.model_copy(update={
                "binding": source.result.binding.model_copy(update={"case_id": case_id}),
                "effects": {f"effect-{i}": VerificationResult(status="pending")
                    for i in range(min(256, total - offset))}})
            command = source.model_copy(update={"command_id": f"{index:032x}", "result": result})
            positions.append(BatchPositionReceiptV1(inventory=BatchPositionInventoryV1(
                ordinal=index, supplied_id_shape="string", supplied_case_id=case_id),
                command=command, admission_status="joined", execution_outcome="result",
                result_hash=fingerprint(result.model_dump(mode="json"))))
        base = batch_receipt(len(positions)).run
        fields = {name: getattr(base, name) for name in type(base).model_fields}
        fields.update(positions=tuple(positions), release_id=source.release_id)
        return CliReceiptV1(run=BatchRunReceiptV1(**fields))

    def test_total_effects_and_output_exact_limits(self):
        trace = build_execution_trace(self.many_effects(4096))
        self.assertEqual(sum(len(p.effects) for p in trace.positions), 4096)
        # The complete JSON is over its own bound even though input limits pass.
        with self.assertRaises(TraceError) as caught:
            render_trace_json(trace)
        self.assertEqual(str(caught.exception), "trace_limit_exceeded")
        self.invalid(self.many_effects(4097), "trace_limit_exceeded")
        # Isolate the byte-boundary helper; never use impossible alias payloads.
        text = "é" * 131072
        self.assertEqual(len(_bounded_output(text).encode("utf-8")), 262144)
        with self.assertRaises(TraceError) as caught:
            _bounded_output(text + "a")
        self.assertEqual(str(caught.exception), "trace_limit_exceeded")

    def test_renderers_reject_numeric_secrets_and_impossible_counter_shapes(self):
        base = build_execution_trace(self.real)
        row = base.positions[0]
        probes = [
            base.model_copy(update={"run": "run-4111111111111111"}),
            base.model_copy(update={"release": "release-2"}),
            base.model_copy(update={"position_count": 999999999}),
            base.model_copy(update={"position_count": 0}),
            base.model_copy(update={"position_count": None}),
            base.model_copy(update={"unresolved_ordinals": (999999999,)}),
            base.model_copy(update={"unresolved_ordinals": (0,)}),
            base.model_copy(update={"positions": (row.model_copy(update={"ordinal": 999999999}),)}),
            base.model_copy(update={"positions": (row.model_copy(update={"case": "case-2"}),)}),
            base.model_copy(update={"positions": (row.model_copy(update={"command": "command-2"}),)}),
            base.model_copy(update={"positions": (row.model_copy(update={"effects": (
                row.effects[0].model_copy(update={"effect": "effect-2"}),)}),)}),
            base.model_copy(update={"pending_commands": ("command-2",)}),
            base.model_copy(update={"position_count": 2, "positions": (row,
                row.model_copy(update={"ordinal": 1}))}),
            base.model_copy(update={"shutdown": base.shutdown.model_copy(update={"pending_count": 999999999})}),
        ]
        review_probe = type(base).model_construct(run="run-4111111111111111",
            position_count=999999999, unresolved_ordinals=(999999999,))
        probes.append(review_probe)
        for index, probe in enumerate(probes):
            for renderer in (render_trace_json, render_trace_markdown):
                with self.subTest(probe=index, renderer=renderer.__name__):
                    with self.assertRaises(TraceError) as caught:
                        renderer(probe)
                    self.assertEqual(str(caught.exception), "invalid_receipt")

    def test_shutdown_aliases_continue_counters_and_reuse_existing_identities(self):
        receipt = self.real.model_copy(deep=True)
        object.__setattr__(receipt, "shutdown", receipt.shutdown.model_copy(update={
            "pending_command_ids": (receipt.run.command.command_id, "private-new-id"),
            "cancelled_command_ids": ("private-new-id", "private-third-id")}))
        trace = build_execution_trace(receipt)
        wire = json.loads(render_trace_json(trace))
        self.assertEqual(wire["shutdown"]["pending_commands"], ["command-1", "command-2"])
        self.assertEqual(wire["shutdown"]["cancelled_commands"], ["command-2", "command-3"])
        self.assertNotIn("private", render_trace_markdown(trace))
        bad = trace.model_copy(update={"shutdown": trace.shutdown.model_copy(update={
            "pending_commands": ("command-1", "command-3")})})
        for renderer in (render_trace_json, render_trace_markdown):
            with self.assertRaises(TraceError) as caught:
                renderer(bad)
            self.assertEqual(str(caught.exception), "invalid_receipt")

    def test_position_and_effect_limits_and_forged_renderer_inputs(self):
        self.assertEqual(len(self.wire(batch_receipt(128))["positions"]), 128)
        self.invalid(batch_receipt(129), "trace_limit_exceeded")
        for count, accepted in ((256, True), (257, False)):
            receipt = self.real.model_copy(deep=True)
            effect = next(iter(receipt.run.command.result.effects.values()))
            object.__setattr__(receipt.run.command.result, "effects", {str(i): effect for i in range(count)})
            if accepted:
                self.assertEqual(len(self.wire(receipt)["positions"][0]["effects"]), 256)
            else:
                self.invalid(receipt, "trace_limit_exceeded")
        trace = build_execution_trace(CliReceiptV1())
        for field, value in (("provenance", "SECRET"), ("publication_files_checked", True),
                             ("pending_commands", ("SECRET",))):
            bad = type(trace).model_construct(**{**trace.__dict__, field: value})
            for renderer in (render_trace_json, render_trace_markdown):
                with self.assertRaises(TraceError) as caught:
                    renderer(bad)
                self.assertEqual(str(caught.exception), "invalid_receipt")

    def test_typed_models_cannot_hide_in_json_or_be_replaced_by_raw_dicts(self):
        receipt = self.real.model_copy(deep=True)
        object.__setattr__(receipt.run.command, "result", receipt.run.command.result.model_dump())
        self.invalid(receipt)
        receipt = self.real.model_copy(deep=True)
        effect = VerificationResult(status="pending")
        object.__setattr__(effect, "postcondition", {"SECRET": VerificationResult(status="pending")})
        object.__setattr__(receipt.run.command.result, "effects", {"operation": effect})
        self.invalid(receipt)

    def test_batch_configuration_and_duplicate_command_joins_are_rejected(self):
        valid = self.many_effects(257)
        for field, bad in (("release_id", "other"), ("mode", "offline_synthetic"),
                           ("clock_mode", "system_utc"),
                           ("command_id", valid.run.positions[0].command.command_id)):
            receipt = valid.model_copy(deep=True)
            object.__setattr__(receipt.run.positions[1].command, field, bad)
            self.invalid(receipt)

    def test_result_history_wait_handoff_media_and_stop_are_independent_facts(self):
        receipt = self.real.model_copy(deep=True)
        object.__setattr__(receipt.run.command, "result", receipt.run.command.result.model_copy(update={
            "historical": True, "wait_status": "pending", "handoff_status": "outcome_unknown",
            "media_status": "failed", "stop": StopState(requested=True, reason="SECRET")}))
        row = self.wire(receipt)["positions"][0]
        self.assertEqual((row["historical"], row["wait_status"], row["handoff_status"],
            row["media_status"], row["stop_requested"]), (True, "pending", "outcome_unknown", "failed", True))
        self.assertEqual(row["effects"][0]["status"], "verified")
        self.assertEqual(row["export_outcome"], "written")


if __name__ == "__main__":
    unittest.main()
