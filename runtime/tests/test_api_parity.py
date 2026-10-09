"""API/library positives in independent owned roots, not native participation."""
from hashlib import sha256
from datetime import timedelta
import json
from pathlib import Path
import threading


from proofkey.batch import run_command
from proofkey.execution import ExecutionContext
from proofkey.host import HostDispatcher, ProfileRegistry
from proofkey.host_contracts import CommandRunReceiptV1, HostLimitsV1

from test_api_boundary import ApiFixture, ObservedFactory, TestClient, canonical


class ApiParityTests(ApiFixture):
    def test_actual_window_and_goods_match_library_journal_source_and_export(self):
        for kind, release, operations in (("reschedule_window", "host-window-replay-v1", ("reschedule",)),
                ("goods_refusal", "host-goods-replay-v1", ("register_goods_refusal", "create_return"))):
            with self.subTest(kind=kind):
                api_factory, lib_factory = ObservedFactory(), ObservedFactory()
                command = {"tag": "run", "release_id": release, "request": canonical(kind).model_dump(mode="json")}
                app = self.app(runtime_factory=api_factory, release_id=release,
                    profile_registry=ProfileRegistry.builtin(self.base / (kind + "-api-resources")))
                with TestClient(app) as client:
                    response = client.post("/v1/commands", json=command, headers=self.headers)
                    self.assertEqual(response.status_code, 200)
                    api_receipt = CommandRunReceiptV1.model_validate_json(response.content)
                dispatcher = HostDispatcher(lib_factory, self.resolver,
                    ProfileRegistry.builtin(self.base / (kind + "-lib-resources")), self.clock,
                    self.base / (kind + "-lib-inventory"), HostLimitsV1(), release_id=release)
                execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=4), self.clock)
                lib_output = self.base / (kind + "-lib-output")
                try:
                    lib_receipt = run_command(command, dispatcher, self.resolver.handle("user"), execution,
                        publication_deadline=execution.deadline + timedelta(seconds=1),
                        publication_reserve_seconds=1.0, output_root=lib_output,
                        limits=self.options["interface_limits"], clock=self.clock)
                finally:
                    dispatcher.close(self.clock.now() + timedelta(seconds=0.3))
                self.assertEqual(api_receipt.command.result.status, "authorized")
                self.assertEqual(lib_receipt.command.result.status, "authorized")
                def normalized(result):
                    value = result.model_dump(mode="json")
                    value.pop("as_of", None)
                    for effect in value["effects"].values():
                        effect.pop("as_of", None)
                    return value
                self.assertEqual(normalized(api_receipt.command.result), normalized(lib_receipt.command.result))
                api_cp, api_intents, api_calls, api_effects, api_original = api_factory.snapshots[-1]
                lib_cp, lib_intents, lib_calls, lib_effects, lib_original = lib_factory.snapshots[-1]
                self.assertEqual(api_original, canonical(kind))
                self.assertEqual(api_original, lib_original)
                self.assertEqual(api_cp.binding, lib_cp.binding)
                self.assertEqual(api_cp.phase, lib_cp.phase)
                self.assertEqual(api_cp.budget.planner_calls, 0)
                self.assertEqual(lib_cp.budget.planner_calls, 0)
                self.assertEqual(api_cp.budget.tool_calls, len(api_calls))
                self.assertEqual(lib_cp.budget.tool_calls, len(lib_calls))
                self.assertGreater(api_cp.budget.active_seconds, 0)
                self.assertGreater(lib_cp.budget.active_seconds, 0)
                self.assertEqual(api_effects, lib_effects)
                for operation in operations:
                    self.assertEqual(api_effects[operation], 1)
                    self.assertEqual(api_receipt.command.result.effects[operation].status, "verified")
                self.assertEqual([(x.operation, x.purpose) for x in api_calls], [(x.operation, x.purpose) for x in lib_calls])
                def original_intents(records, context):
                    values = []
                    for record in records:
                        self.assertLessEqual(record.intent.deadline, context.deadline)
                        self.assertGreater(record.intent.deadline, context.captured_at)
                        value = record.intent.model_dump(mode="json")
                        value.pop("deadline")
                        values.append(value)
                    return values
                self.assertEqual(original_intents(api_intents, api_factory.contexts[0]),
                                 original_intents(lib_intents, execution))
                api_output = next(root for root in self.output.iterdir()
                    if (root / "ANSWERS/C1/ANSWER.md").exists()
                    and sha256((root / "ANSWERS/C1/ANSWER.md").read_bytes()).hexdigest()
                        == dict(api_receipt.export.actual_file_hashes)["ANSWER.md"])
                # Independent actual source timestamps make ANSWER bytes differ.
                # Both exact exports must validate their own factual byte hashes;
                # stable public rationale bytes must match across the two roots.
                self.assertEqual(dict(api_receipt.export.actual_file_hashes)["REASONING.md"],
                                 dict(lib_receipt.export.actual_file_hashes)["REASONING.md"])
                for factory in (api_factory, lib_factory):
                    self.assertEqual(set(factory.owners), set(factory.closed))
                    self.assertEqual(len(set(factory.owners)), 1)
                    self.assertNotIn(threading.get_ident(), factory.owners)
                for name, digest in lib_receipt.export.actual_file_hashes:
                    self.assertEqual(sha256((lib_output / "ANSWERS/C1" / name).read_bytes()).hexdigest(), digest)
                for name, digest in api_receipt.export.actual_file_hashes:
                    self.assertEqual(sha256((api_output / "ANSWERS/C1" / name).read_bytes()).hexdigest(), digest)
                print("API-POSITIVE " + json.dumps({"kind": kind, "effects": api_effects,
                    "calls": len(api_calls), "api_active": api_cp.budget.active_seconds,
                    "library_active": lib_cp.budget.active_seconds,
                    "api_hashes": dict(api_receipt.export.actual_file_hashes),
                    "library_hashes": dict(lib_receipt.export.actual_file_hashes)}, sort_keys=True))
