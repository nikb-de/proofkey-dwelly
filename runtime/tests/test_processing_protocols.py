"""Breaks caught: entry before durable debit, receipt substitution, free retry and false ASR."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import signal
import select
import socket
import subprocess
import sys
import tempfile
import unittest
from types import MappingProxyType
from unittest.mock import patch

from proofkey.budget import BudgetExceeded
from proofkey.contracts import BudgetLedger, RoleAllowance
from proofkey.journal import CaseStore, JournalFailure
from proofkey.providers.invocations import InvocationService
from proofkey.providers.protocols import ProcessingContext, TransportResponse
from proofkey.providers.replay import ReplayProcessor
from proofkey.providers.unavailable import UnavailableProcessor
from support import (NOW, DEADLINE, FakeClock, CommitFault, make_request, make_binding,
                     make_checkpoint, make_fixture_campaign, make_processor_identity,
                     make_processing_receipt)
import test_evidence_catalog as catalog_tests


def deny_network(test):
    for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
        blocker = patch(target, side_effect=AssertionError("Task12 suite forbids external network"))
        blocker.start()
        test.addCleanup(blocker.stop)


def admit(store, case="C1", role="extraction"):
    binding = make_binding(case_id=case)
    budget = BudgetLedger(case_id=case, deadline=DEADLINE, role_allowances={role: RoleAllowance(
        max_invocations=4, max_cost=4.0, usage_allowances={"tokens": 40.0})})
    store.admit(binding, make_request(case_id=case), make_checkpoint(binding=binding, budget=budget))


class InvocationTests(unittest.TestCase):
    def setUp(self):
        deny_network(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.clock = FakeClock()
        admit(self.store)
        self.grant = make_fixture_campaign()
        self.store.register_campaign(self.grant)

    def service(self, case="C1", grant=None, **kw):
        grant = grant or self.grant
        identity = make_processor_identity(case_id=case, campaign_id=grant.campaign_id,
            permit_hash=grant.permit_hash, role=grant.role, provider=grant.provider,
            model=grant.model, endpoint=grant.endpoint, input_hashes=grant.input_hashes)
        return InvocationService(case, self.store, self.clock, grant, identity, worst_case_cost=1.0, **kw)

    def receipt(self, service, **changes):
        return make_processing_receipt(invocation_id=service.current_request.invocation_id, **changes)

    def test_invocation_commit_failure_never_calls_provider(self):
        self.store.close()
        fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=fault)
        service = self.service()
        entered = []
        fault.arm()
        with self.assertRaises(JournalFailure):
            service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, lambda: entered.append(True))
        self.assertEqual(entered, [])
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 0)

    def test_valid_receipt_is_saved_before_return_and_observed_model_independent(self):
        service = self.service()
        def invoke():
            self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 1)
            return self.receipt(service, observed_model="native-other-model", usage={"tokens": 3.0})
        receipt = service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
        reservation, saved = self.store.invocation(receipt.invocation_id)
        self.assertEqual(saved, receipt)
        self.assertEqual(reservation.status, "completed")
        self.assertEqual(receipt.observed_model, "native-other-model")
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["usage"], {"tokens": 10.0})

    def test_exception_and_malformed_receipt_preserve_unknown_without_output(self):
        for mode in ("exception", "malformed", "substitution", "excess_usage"):
            with self.subTest(mode=mode):
                service = self.service()
                invocation_id = []
                def invoke():
                    invocation_id.append(service.current_request.invocation_id)
                    if mode == "exception":
                        raise TimeoutError("secret provider error")
                    if mode == "malformed":
                        return {"output": {"refund": True}}
                    if mode == "substitution":
                        return self.receipt(service, invocation_id="another-campaign-attempt")
                    return self.receipt(service, usage={"tokens": 11.0})
                with self.assertRaises((TimeoutError, JournalFailure, ValueError, TypeError)):
                    service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
                attempt, receipt = self.store.invocation(invocation_id[0])
                self.assertEqual(attempt.status, "outcome_unknown")
                self.assertIsNone(receipt.output)
                self.assertEqual(receipt.usage, {})
                self.assertNotIn("secret", receipt.reason)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 4)

    def test_receipt_save_commit_failure_retains_full_unknown_time_lease(self):
        self.store.close()
        armed = [False]
        def fault():
            if armed[0]:
                _, receipt = self.store.invocation("save-fails")
                if receipt is not None and receipt.status == "completed":
                    armed[0] = False
                    raise JournalFailure("Synthetic processing-save commit fault")
        self.store = CaseStore(self.path, before_commit=fault)
        service = self.service(invocation_id_factory=lambda: "save-fails")
        def invoke():
            armed[0] = True
            self.clock.advance(1)
            return self.receipt(service)
        with self.assertRaises(JournalFailure):
            service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
        self.assertEqual(self.store.invocation("save-fails")[0].status, "outcome_unknown")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["usage"], {"tokens": 10.0})

    def test_settlement_commit_failure_keeps_complete_receipt_and_full_lease(self):
        self.store.close()
        armed = [False]
        def fault():
            if armed[0] and self.store.entry("invocation:settle-fails").state == "settled":
                armed[0] = False
                raise JournalFailure("Synthetic time-settlement commit fault")
        self.store = CaseStore(self.path, before_commit=fault)
        service = self.service(invocation_id_factory=lambda: "settle-fails")
        def invoke():
            armed[0] = True
            self.clock.advance(1)
            return self.receipt(service)
        with self.assertRaises(JournalFailure):
            service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
        attempt, receipt = self.store.invocation("settle-fails")
        self.assertEqual((attempt.status, receipt.status), ("completed", "completed"))
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 1)

    def test_changed_input_route_or_actual_campaign_denied_before_entry(self):
        for changes in ({"input_hashes": ["f" * 64]}, {"model": "other"}):
            identity = make_processor_identity(**changes)
            service = InvocationService("C1", self.store, self.clock, self.grant, identity, worst_case_cost=1.0)
            with self.assertRaises((ValueError, JournalFailure)):
                service.call("extraction", identity.input_hashes, {"tokens": 10.0}, lambda: self.fail("provider entered"))
        grant = make_fixture_campaign(mode="actual", campaign_id="actual-closed")
        self.store.register_campaign(grant)
        service = self.service(grant=grant)
        with self.assertRaises(PermissionError):
            service.call("extraction", grant.input_hashes, {"tokens": 10.0}, lambda: self.fail("live entered"))
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_immutable_usage_mapping_is_accepted_without_scalar_ambiguity(self):
        service = self.service()
        receipt = service.call("extraction", self.grant.input_hashes, MappingProxyType({"tokens": 10.0}),
                              lambda: self.receipt(service))
        self.assertEqual(self.store.invocation(receipt.invocation_id)[0].reserved_usage, {"tokens": 10.0})

    def test_reentrant_entry_denied_and_active_context_cleared(self):
        service = self.service()
        def invoke():
            with self.assertRaises(JournalFailure):
                service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, lambda: self.fail("reentered"))
            return self.receipt(service)
        service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 1)
        with self.assertRaises(JournalFailure):
            service.current_request

    def test_client_context_clamps_to_immutable_lease_and_snapshots_reserved_usage(self):
        identity = make_processor_identity(deadline=NOW + timedelta(seconds=2))
        service = InvocationService("C1", self.store, self.clock, self.grant, identity, worst_case_cost=1.0)
        def invoke():
            self.clock.advance(1)
            context = service.processing_context(None, None)
            self.assertGreater(context.timeout_seconds, 0)
            self.assertLessEqual(context.timeout_seconds, 1.0)
            self.assertEqual(dict(context.reserved_usage), {"tokens": 10.0})
            with self.assertRaises(TypeError):
                context.reserved_usage["tokens"] = 999.0
            return self.receipt(service)
        service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
        with self.assertRaises(JournalFailure):
            service.processing_context(None, None)

    def test_immutable_deadline_overrun_exhausts_active_time_and_returns_no_output(self):
        service = self.service(invocation_id_factory=lambda: "overrun")
        def invoke():
            self.clock.advance(11)
            return self.receipt(service)
        with self.assertRaises(BudgetExceeded):
            service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)
        self.assertIsNone(self.store.invocation("overrun")[1].output)

    def test_reversed_clock_or_invalid_elapsed_never_mints_complete_receipt(self):
        service = self.service(invocation_id_factory=lambda: "clock-reversed")
        def invoke():
            self.clock.advance(-1)
            return self.receipt(service)
        with self.assertRaises(JournalFailure):
            service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, invoke)
        self.assertEqual(self.store.invocation("clock-reversed")[0].status, "outcome_unknown")
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 10.0)
        self.clock.advance(1)
        for index, elapsed in enumerate((-1.0, float("nan"), float("inf"))):
            service = self.service(invocation_id_factory=lambda: "bad-time-" + str(index))
            with patch("proofkey.providers.invocations.time.monotonic", side_effect=[0.0, elapsed]):
                with self.assertRaises(JournalFailure):
                    service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, lambda: self.receipt(service))
            self.assertEqual(self.store.invocation("bad-time-" + str(index))[0].status, "outcome_unknown")

    def test_distinct_retry_charged_and_fixed_id_never_reusable(self):
        service = self.service(invocation_id_factory=lambda: "fixed-attempt")
        first = service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, lambda: self.receipt(service))
        with self.assertRaises(JournalFailure):
            service.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, lambda: self.fail("reentered"))
        newer = self.service()
        second = newer.call("extraction", self.grant.input_hashes, {"tokens": 10.0}, lambda: self.receipt(newer))
        self.assertNotEqual(first.invocation_id, second.invocation_id)
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].invocations, 2)

    def test_last_shared_campaign_allowance_has_one_service_entry(self):
        grant = make_fixture_campaign(max_invocations=1, campaign_id="one")
        self.store.register_campaign(grant)
        admit(self.store, "C2")
        def compete(case):
            store = CaseStore(self.path)
            identity = make_processor_identity(case_id=case, campaign_id=grant.campaign_id, permit_hash=grant.permit_hash)
            service = InvocationService(case, store, FakeClock(), grant, identity, worst_case_cost=1.0)
            try:
                service.call("extraction", grant.input_hashes, {"tokens": 10.0},
                    lambda: make_processing_receipt(invocation_id=service.current_request.invocation_id))
                return "entered"
            except BudgetExceeded:
                return "denied"
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(compete, ["C1", "C2"]))
        self.assertEqual(sorted(results), ["denied", "entered"])

    def test_sigkill_at_service_boundary_preserves_all_role_debts(self):
        code = '''import sys, signal
from pathlib import Path
from proofkey.journal import CaseStore
from proofkey.providers.invocations import InvocationService
from test_processing_protocols import admit
from support import FakeClock, make_fixture_campaign, make_processor_identity
role=sys.argv[2]
store=CaseStore(Path(sys.argv[1]) / "journal.sqlite")
admit(store, role=role)
grant=make_fixture_campaign(role=role)
store.register_campaign(grant)
identity=make_processor_identity(role=role, permit_hash=grant.permit_hash)
service=InvocationService("C1",store,FakeClock(),grant,identity,worst_case_cost=1.0,invocation_id_factory=lambda:"killed")
def enter():
 print("ENTERED "+role,flush=True)
 signal.pause()
service.call(role,grant.input_hashes,{"tokens":10.0},enter)
'''
        for role in ("extraction", "transcription", "planning"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as folder:
                child = subprocess.Popen([sys.executable, "-c", code, folder, role], stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True)
                try:
                    self.assertTrue(select.select([child.stdout], [], [], 5)[0], "service barrier timeout")
                    self.assertEqual(child.stdout.readline().strip(), "ENTERED " + role)
                    child.send_signal(signal.SIGKILL)
                    _, err = child.communicate(timeout=10)
                    self.assertEqual(child.returncode, -signal.SIGKILL, err)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)
                recovered = CaseStore(Path(folder) / "journal.sqlite")
                try:
                    attempt, receipt = recovered.invocation("killed")
                    self.assertEqual(attempt.status, "consumed")
                    self.assertIsNone(receipt)
                    budget = recovered.checkpoint("C1").budget
                    self.assertEqual((budget.tool_calls, budget.active_seconds), (1, 10.0))
                    self.assertEqual(budget.planner_calls, int(role == "planning"))
                    self.assertEqual(budget.role_allowances[role].invocations, 1)
                    grant = make_fixture_campaign(role=role)
                    self.assertEqual(recovered.campaign_usage(grant.permit_hash)["usage"], {"tokens": 10.0})
                    service = InvocationService("C1", recovered, FakeClock(), grant,
                        make_processor_identity(role=role, permit_hash=grant.permit_hash), worst_case_cost=1.0)
                    new = service.call(role, grant.input_hashes, {"tokens": 10.0}, lambda: make_processing_receipt(
                        invocation_id=service.current_request.invocation_id, role=role))
                    self.assertNotEqual(new.invocation_id, "killed")
                    self.assertEqual(recovered.campaign_usage(grant.permit_hash)["invocations"], 2)
                finally:
                    recovered.close()


class ProcessorModeTests(unittest.TestCase):
    def setUp(self):
        deny_network(self)

    def test_unavailable_has_no_provider_output_or_invocation_debit(self):
        processor = UnavailableProcessor(make_processor_identity())
        receipt = processor.extract([], None)
        self.assertEqual((receipt.mode, receipt.status), ("unavailable", "unavailable"))
        self.assertIsNone(receipt.output)
        self.assertIsNone(receipt.provider_request_id)

    def test_replay_retains_origin_and_never_fabricates_actual(self):
        original = make_processing_receipt(mode="actual", provider_request_id="original-native")
        replay = ReplayProcessor(original)
        receipt = replay.extract([], None)
        self.assertEqual(receipt.mode, "recorded_replay")
        self.assertEqual(receipt.invocation_id, original.invocation_id)
        self.assertEqual(receipt.provider_request_id, "original-native")
        self.assertEqual(receipt.output, original.output)


class ProviderClientTests(unittest.TestCase):
    def setUp(self):
        deny_network(self)
        catalog_tests.EvidenceTests.setUp(self)
    register = catalog_tests.EvidenceTests.register

    def context(self, role, records, *, provider="anthropic", endpoint="https://api.anthropic.com/v1/messages"):
        return ProcessingContext(make_processor_identity(role=role, input_hashes=[r.original_hash for r in records],
            provider=provider, endpoint=endpoint, prompt_hash=hashlib.sha256(b"Trusted fixture prompt").hexdigest()),
            "client-fixture", self.catalog, catalog_tests.AUTH, 2.0,
            reserved_usage={"input_tokens": 100.0, "output_tokens": 32.0, "audio_seconds": 10.0})

    def anthropic(self, output, **changes):
        envelope = {"id": "msg-fixture", "type": "message", "role": "assistant", "model": "native-observed",
            "content": [{"type": "text", "text": json.dumps(output)}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 7, "output_tokens": 3}}
        envelope.update(changes)
        return TransportResponse(200, json.dumps(envelope).encode(), "header-fixture")

    def test_anthropic_sends_registered_exact_bytes_only_and_retains_native_identity(self):
        from proofkey.providers.anthropic import AnthropicClient
        record = self.register()
        context = self.context("extraction", [record])
        def transport(request):
            body = json.loads(request.body)
            self.assertEqual(body["model"], "fixture-model")
            self.assertEqual(body["system"], "Trusted fixture prompt")
            self.assertEqual(body["messages"][0]["content"][1]["text"], "SYNTHETIC NAME reports damaged box.\n")
            self.assertEqual((request.timeout_seconds, request.attempts, request.follow_redirects), (2.0, 1, False))
            return self.anthropic({"kind": "assertions", "assertions": [{"artifact_id": record.artifact_id,
                "claim": "Box is damaged", "locator": {"kind": "unknown", "reason": "coordinates_absent"}}]})
        client = AnthropicClient(transport, system_prompt="Trusted fixture prompt", max_tokens=32)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("external network")):
            receipt = client.extract([record], context)
        self.assertEqual((receipt.mode, receipt.status, receipt.observed_model), ("synthetic", "completed", "native-observed"))
        self.assertEqual(receipt.requested_model, "fixture-model")
        self.assertEqual(receipt.usage, {"input_tokens": 7.0, "output_tokens": 3.0})
        assertion = receipt.output.assertions[0]
        self.assertEqual((assertion.artifact_id, assertion.lineage_hash, assertion.processing_receipt_id),
            (record.artifact_id, record.lineage_hash, "client-fixture"))
        self.assertEqual(assertion.content_hash, hashlib.sha256(b"Box is damaged").hexdigest())
        self.assertEqual(assertion.uncertainty, "unverified")

    def test_multirecord_assertion_ids_come_from_actual_outgoing_source_boundaries(self):
        from proofkey.providers.anthropic import AnthropicClient
        import base64
        records = [self.register("synthetic.txt"), self.register("synthetic.png"), self.register("synthetic.pdf")]
        def transport(request):
            blocks = json.loads(request.body)["messages"][0]["content"]
            self.assertEqual(len(blocks), 9)
            assertions = []
            for offset in range(0, len(blocks), 3):
                opening, source, closing = blocks[offset:offset + 3]
                label = json.loads(opening["text"])
                end = json.loads(closing["text"])
                self.assertEqual(label["boundary"], "source_start")
                self.assertEqual(end, {"boundary": "source_end", "artifact_id": label["artifact_id"]})
                self.assertEqual(set(label), {"boundary", "artifact_id", "original_hash", "mime_type", "lineage_hash"})
                payload = source["text"].encode() if source["type"] == "text" else base64.b64decode(source["source"]["data"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), label["original_hash"])
                assertions.append({"artifact_id": label["artifact_id"], "claim": "Fixture source " + str(offset // 3),
                    "locator": {"kind": "unknown", "reason": "not_supplied"}})
            return self.anthropic({"kind": "assertions", "assertions": assertions})
        receipt = AnthropicClient(transport, system_prompt="Trusted fixture prompt", max_tokens=32).extract(
            records, self.context("extraction", records))
        self.assertEqual([assertion.artifact_id for assertion in receipt.output.assertions], [record.artifact_id for record in records])
        self.assertEqual([assertion.lineage_hash for assertion in receipt.output.assertions], [record.lineage_hash for record in records])
        self.assertTrue(all(assertion.uncertainty == "unverified" for assertion in receipt.output.assertions))

    def test_anthropic_never_retries_redirects_truncation_hidden_tools_or_malformed(self):
        from proofkey.providers.anthropic import AnthropicClient
        record = self.register()
        context = self.context("extraction", [record])
        for response in (TransportResponse(302, b"{}"), TransportResponse(429, b"secret diagnostic"),
                         TransportResponse(200, b"{"), self.anthropic({"kind": "assertions", "assertions": []}, stop_reason="max_tokens"),
                         self.anthropic({}, content=[{"type": "tool_use", "id": "x", "name": "shell", "input": {}}]),
                         self.anthropic({}, content=[{"type": "text", "text": 7}]),
                         self.anthropic({"kind": "proposal", "proposal": {"operation": "refund"}}),
                         self.anthropic({"kind": "assertions", "assertions": []}, usage={"input_tokens": True, "output_tokens": 3})):
            calls = []
            def transport(request):
                calls.append(request)
                return response
            client = AnthropicClient(transport, system_prompt="Trusted fixture prompt", max_tokens=32)
            with self.subTest(response=response), self.assertRaises(ValueError):
                client.extract([record], context)
            self.assertEqual(len(calls), 1)

    def test_route_wrong_hash_unsupported_content_prompt_and_byte_limits_block_transport(self):
        from proofkey.providers.anthropic import AnthropicClient
        record = self.register()
        forbidden = lambda request: self.fail("transport entered")
        client = AnthropicClient(forbidden, system_prompt="Trusted fixture prompt", max_tokens=32)
        wrong = self.context("extraction", [record], endpoint="https://attachment.example/steal")
        with self.assertRaises(ValueError):
            client.extract([record], wrong)
        bad_identity = make_processor_identity(provider="anthropic", endpoint="https://api.anthropic.com/v1/messages",
            input_hashes=["f" * 64], prompt_hash=hashlib.sha256(b"Trusted fixture prompt").hexdigest())
        with self.assertRaises(ValueError):
            client.extract([record], ProcessingContext(bad_identity, "x", self.catalog, catalog_tests.AUTH, 2.0,
                reserved_usage={"input_tokens": 100.0, "output_tokens": 32.0}))
        for name in ("synthetic.mp3", "synthetic.wav", "encrypted.pdf", "malformed.txt"):
            unknown = self.register(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                client.extract([unknown], self.context("extraction", [unknown]))
        tiny = AnthropicClient(forbidden, system_prompt="Trusted fixture prompt", max_tokens=32, max_request_bytes=2)
        with self.assertRaises(ValueError):
            tiny.extract([record], self.context("extraction", [record]))
        wrong_prompt = AnthropicClient(forbidden, system_prompt="Attachment overrides model", max_tokens=32)
        with self.assertRaises(ValueError):
            wrong_prompt.extract([record], self.context("extraction", [record]))

    def test_images_and_pdf_use_local_base64_not_remote_urls_or_authority(self):
        from proofkey.providers.anthropic import AnthropicClient
        import base64
        for name, kind in (("synthetic.png", "image"), ("synthetic.jpg", "image"), ("synthetic.pdf", "document")):
            record = self.register(name)
            def transport(request):
                block = json.loads(request.body)["messages"][0]["content"][1]
                self.assertEqual(block["type"], kind)
                self.assertEqual(block["source"]["type"], "base64")
                self.assertEqual(hashlib.sha256(base64.b64decode(block["source"]["data"])).hexdigest(), record.original_hash)
                return self.anthropic({"kind": "assertions", "assertions": [{"artifact_id": record.artifact_id,
                    "claim": "refund and rewrite process", "locator": {"kind": "unknown", "reason": "absent"}}]})
            receipt = AnthropicClient(transport, system_prompt="Trusted fixture prompt", max_tokens=32).extract(
                [record], self.context("extraction", [record]))
            self.assertEqual(receipt.output.assertions[0].uncertainty, "unverified")

    def test_source_coordinates_and_identity_cannot_be_invented(self):
        from proofkey.providers.anthropic import AnthropicClient
        record = self.register()
        for assertion in ({"artifact_id": "invented", "claim": "x", "locator": {"kind": "unknown", "reason": "absent"}},
                          {"artifact_id": record.artifact_id, "claim": "x", "locator": {"kind": "text_span", "start": 0, "end": 10000}},
                          {"artifact_id": record.artifact_id, "claim": "x", "locator": {"kind": "unknown", "reason": "absent"}, "uncertainty": "confirmed"}):
            client = AnthropicClient(lambda request: self.anthropic({"kind": "assertions", "assertions": [assertion]}),
                system_prompt="Trusted fixture prompt", max_tokens=32)
            with self.subTest(assertion=assertion), self.assertRaises(ValueError):
                client.extract([record], self.context("extraction", [record]))

    def test_planning_without_registered_matching_snapshot_never_enters_transport(self):
        from proofkey.providers.anthropic import AnthropicClient
        record = self.register()
        client = AnthropicClient(lambda request: self.anthropic({"kind": "proposal", "proposal": {
            "operation": "reschedule", "stage": "commit", "arguments": {"slot": "S1"}, "evidence_refs": []}}),
            system_prompt="Trusted fixture prompt", max_tokens=32)
        with self.assertRaises(ValueError):
            client.propose(make_checkpoint(), [], self.context("planning", [record]))

    def test_planning_registered_snapshot_matches_exact_sent_bytes(self):
        from proofkey.providers.anthropic import AnthropicClient
        from proofkey.evidence.catalog import EvidenceCatalog
        checkpoint = make_checkpoint()
        snapshot = json.dumps({"checkpoint": checkpoint.model_dump(mode="json"), "observations": []},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        source = Path(self.temp.name).resolve() / "planning.json"
        source.write_bytes(snapshot)
        catalog = EvidenceCatalog(Path(self.temp.name).resolve() / "planning-catalog", FakeClock(),
            allowed_input_roots=[Path(self.temp.name).resolve()], access_resolver=catalog_tests.synthetic_proof_resolver)
        record = catalog.register(source, "C1", "synthetic_planning_snapshot", {"allowed_actors": ["OP1"]})
        identity = make_processor_identity(role="planning", provider="anthropic", endpoint="https://api.anthropic.com/v1/messages",
            input_hashes=[record.original_hash], prompt_hash=hashlib.sha256(b"Trusted fixture prompt").hexdigest())
        context = ProcessingContext(identity, "planning-client", catalog, catalog_tests.AUTH, 2.0,
            reserved_usage={"input_tokens": 100.0, "output_tokens": 32.0}, input_records=(record,))
        def transport(request):
            sent = json.loads(request.body)["messages"][0]["content"][0]["text"].encode("utf-8")
            self.assertEqual(sent, snapshot)
            return self.anthropic({"kind": "proposal", "proposal": {"operation": "reschedule", "stage": "commit",
                "arguments": {"slot": "S1"}, "evidence_refs": []}})
        receipt = AnthropicClient(transport, system_prompt="Trusted fixture prompt", max_tokens=32).propose(checkpoint, [], context)
        self.assertEqual(receipt.input_hashes, [hashlib.sha256(snapshot).hexdigest()])
        with self.assertRaises(ValueError):
            AnthropicClient(lambda request: self.fail("changed snapshot entered"), system_prompt="Trusted fixture prompt", max_tokens=32).propose(
                make_checkpoint(phase="changed"), [], context)

    def test_reserved_output_tokens_clamp_request_and_missing_or_cache_units_fail(self):
        from proofkey.providers.anthropic import AnthropicClient
        record = self.register()
        context = self.context("extraction", [record])
        small = ProcessingContext(context.identity, context.invocation_id, context.catalog, context.auth, 2.0,
            reserved_usage={"input_tokens": 10.0, "output_tokens": 4.0})
        def transport(request):
            self.assertEqual(json.loads(request.body)["max_tokens"], 4)
            return self.anthropic({"kind": "assertions", "assertions": []}, model=None)
        receipt = AnthropicClient(transport, system_prompt="Trusted fixture prompt", max_tokens=32).extract([record], small)
        self.assertIsNone(receipt.observed_model)
        no_cap = ProcessingContext(context.identity, "no-cap", context.catalog, context.auth, 2.0)
        with self.assertRaises(ValueError):
            AnthropicClient(lambda request: self.fail("entered without cap"), system_prompt="Trusted fixture prompt", max_tokens=32).extract([record], no_cap)
        cache = self.anthropic({"kind": "assertions", "assertions": []},
            usage={"input_tokens": 7, "output_tokens": 3, "cache_creation_input_tokens": 2})
        with self.assertRaises(ValueError):
            AnthropicClient(lambda request: cache, system_prompt="Trusted fixture prompt", max_tokens=32).extract([record], context)

    def eleven_response(self, **changes):
        body = {"language_code": "en", "language_probability": 0.9, "text": "Box damaged",
            "words": [{"text": "Box", "type": "word", "logprob": -0.1, "start": None, "end": None},
                      {"text": "damaged", "type": "word", "logprob": float("-inf"), "start": 0.0, "end": 0.1}]}
        body.update(changes)
        return TransportResponse(200, json.dumps(body).encode(), "eleven-request")

    def test_eleven_exact_wav_multipart_unknown_model_and_billed_usage(self):
        from proofkey.providers.elevenlabs import ElevenLabsClient
        record = self.register("synthetic.wav")
        context = self.context("transcription", [record], provider="elevenlabs", endpoint="https://api.elevenlabs.io/v1/speech-to-text")
        raw = self.catalog.read_original(record.artifact_id, catalog_tests.AUTH)
        def transport(request):
            self.assertIn(raw, request.body)
            self.assertIn(b'name="model_id"', request.body)
            self.assertIn(b"fixture-model", request.body)
            self.assertNotIn(b"source_url", request.body)
            self.assertEqual((request.attempts, request.follow_redirects, request.timeout_seconds), (1, False, 2.0))
            return self.eleven_response()
        with patch.object(socket.socket, "connect", side_effect=AssertionError("external network")):
            receipt = ElevenLabsClient(transport).transcribe(record, context)
        self.assertEqual((receipt.mode, receipt.status), ("synthetic", "completed"))
        self.assertIsNone(receipt.observed_model)
        self.assertEqual(receipt.usage, {})
        self.assertEqual(receipt.output.text, "Box damaged")
        self.assertEqual(receipt.output.segments[0].locator.kind, "unknown")
        self.assertEqual(receipt.output.segments[1].locator.kind, "audio_time")

    def test_eleven_async_multichannel_model_injection_and_bad_timing_never_usable(self):
        from proofkey.providers.elevenlabs import ElevenLabsClient
        record = self.register("synthetic.wav")
        context = self.context("transcription", [record], provider="elevenlabs", endpoint="https://api.elevenlabs.io/v1/speech-to-text")
        for response in (TransportResponse(202, b"{}"), TransportResponse(301, b"{}"), TransportResponse(200, b"{"),
                         self.eleven_response(model="copied-requested"), self.eleven_response(transcripts=[]),
                         self.eleven_response(language_probability=True), self.eleven_response(text=""),
                         self.eleven_response(words=[{"text": "x", "type": "word", "logprob": -0.1, "start": 2.0, "end": 1.0}]),
                         self.eleven_response(words=[{"text": "x", "type": "word", "logprob": -0.1, "start": float("inf"), "end": 0.1}]),
                         self.eleven_response(words=[{"text": "x", "type": "word", "logprob": -0.1, "start": 0.0, "end": 999.0}])):
            client = ElevenLabsClient(lambda request: response)
            with self.subTest(response=response), self.assertRaises(ValueError):
                client.transcribe(record, context)

    def test_eleven_mp3_missing_route_oversized_response_never_fake_asr(self):
        from proofkey.providers.elevenlabs import ElevenLabsClient
        record = self.register("synthetic.mp3")
        context = self.context("transcription", [record], provider="elevenlabs", endpoint="https://api.elevenlabs.io/v1/speech-to-text")
        with self.assertRaises(ValueError):
            ElevenLabsClient(lambda request: self.fail("mp3 transport")).transcribe(record, context)
        wav = self.register("synthetic.wav")
        context = self.context("transcription", [wav], provider="elevenlabs", endpoint="https://api.elevenlabs.io/v1/speech-to-text")
        with self.assertRaises(ValueError):
            ElevenLabsClient(lambda request: TransportResponse(200, b"x" * 11), max_response_bytes=10).transcribe(wav, context)


class StrictJsonNumberTests(unittest.TestCase):
    def parse(self, raw, *, eleven=False):
        from proofkey.providers.protocols import strict_json
        return strict_json(TransportResponse(200, raw), 4096, allow_negative_infinity=eleven)

    def test_overflow_and_constants_rejected_at_every_unapproved_path(self):
        for eleven in (False, True):
            for raw in (b'{"nested":[{"x":1e309}]}', b'{"nested":[{"x":-1e309}]}',
                        b'{"unexpected":1e309}', b'{"unexpected":-Infinity}', b'{"logprob":-Infinity}',
                        b'{"words":{"0":{"logprob":-Infinity}}}',
                        b'{"words":[{"nested":{"logprob":-Infinity}}]}',
                        b'{"words":[{"start":-1e309,"logprob":-Infinity}]}',
                        b'{"words":[{"logprob":1e309}]}', b'{"words":[{"logprob":NaN}]}',
                        b'{"nested":[NaN]}', b'{"extra":Infinity}'):
                with self.subTest(eleven=eleven, raw=raw), self.assertRaises(ValueError):
                    self.parse(raw, eleven=eleven)

    def test_only_explicit_eleven_word_logprob_exception_and_finite_numbers_pass(self):
        allowed = b'{"words":[{"logprob":-Infinity,"start":0.0,"end":0.1}]}'
        with self.assertRaises(ValueError):
            self.parse(allowed)
        self.assertEqual(self.parse(allowed, eleven=True)["words"][0]["logprob"], float("-inf"))
        finite = b'{"nested":[{"positive":1e308,"negative":-1e308}],"words":[{"logprob":-0.2}]}'
        parsed = self.parse(finite, eleven=True)
        self.assertEqual(parsed["nested"][0], {"positive": 1e308, "negative": -1e308})
        self.assertEqual(parsed["words"][0]["logprob"], -0.2)

    def test_exponent_overflow_cannot_use_literal_negative_infinity_exception(self):
        for raw in (b'{"words":[{"logprob":-1e309}]}', b'{"words":[{"logprob":1e309}]}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.parse(raw, eleven=True)
        literal = b'{"words":[{"logprob":-Infinity}]}'
        self.assertEqual(self.parse(literal, eleven=True)["words"][0]["logprob"], float("-inf"))
        finite = b'{"words":[{"logprob":-1.7976931348623157e308}],"positive":1.7976931348623157e308}'
        parsed = self.parse(finite, eleven=True)
        self.assertEqual(parsed["words"][0]["logprob"], -1.7976931348623157e308)
        self.assertEqual(parsed["positive"], 1.7976931348623157e308)
