"""Independent receipt boundary; Task5/6 policy/engine propagation remains a separate gate.

Breaks caught: usable proposal without durable matching receipt; model expanding tools/graph.
"""
import tempfile
import unittest
from pathlib import Path

from proofkey.contracts import ActionProposal, ProposalOutput
from proofkey.journal import CaseStore, JournalFailure
from proofkey.planner import BoundedPlanner, validated_proposal
from proofkey.providers.invocations import InvocationService
from support import (FakeClock, make_checkpoint, make_fixture_campaign,
                     make_processor_identity, make_processing_receipt)
from test_processing_protocols import admit, deny_network


class ProposalTests(unittest.TestCase):
    def setUp(self):
        deny_network(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = CaseStore(Path(self.temp.name) / "journal.sqlite")
        self.addCleanup(self.store.close)
        admit(self.store, role="planning")
        self.grant = make_fixture_campaign(role="planning")
        self.store.register_campaign(self.grant)
        self.service = InvocationService("C1", self.store, FakeClock(), self.grant,
            make_processor_identity(role="planning", permit_hash=self.grant.permit_hash), worst_case_cost=1.0)

    def receipt(self, **changes):
        return make_processing_receipt(role="planning", invocation_id=self.service.current_request.invocation_id, **changes)

    def test_only_durable_matching_receipt_exposes_proposal(self):
        receipt = self.service.call("planning", self.grant.input_hashes, {"tokens": 10.0}, self.receipt)
        proposal = validated_proposal(self.store, receipt, self.store.invocation(receipt.invocation_id)[0].identity)
        self.assertEqual(proposal.operation, "reschedule")
        self.assertEqual(proposal.arguments, {"slot": "S1"})
        unsaved = make_processing_receipt(role="planning", invocation_id="unsaved")
        with self.assertRaises(JournalFailure):
            validated_proposal(self.store, unsaved, make_processor_identity(role="planning"))
        forged = make_processing_receipt(role="planning", invocation_id=receipt.invocation_id,
            output=ProposalOutput(kind="proposal", proposal=ActionProposal(
                operation="refund", stage="commit", arguments={}, evidence_refs=[])))
        with self.assertRaises(JournalFailure):
            validated_proposal(self.store, forged, self.store.invocation(receipt.invocation_id)[0].identity)

    def test_crosscampaign_expected_identity_cannot_use_saved_proposal(self):
        receipt = self.service.call("planning", self.grant.input_hashes, {"tokens": 10.0}, self.receipt)
        with self.assertRaises(JournalFailure):
            validated_proposal(self.store, receipt, make_processor_identity(role="planning", campaign_id="other"))

    def test_raw_saved_replay_or_bad_output_hash_is_not_validated_planning(self):
        for mode, hashes in (("recorded_replay", None), ("synthetic", ["f" * 64])):
            with self.subTest(mode=mode):
                request = self.service.make_invocation_request("planning", self.grant.input_hashes, {"tokens": 10.0})
                self.store.reserve_invocation(request, self.service.clock.now())
                changes = {"output_hashes": hashes} if hashes else {}
                receipt = make_processing_receipt(role="planning", invocation_id=request.invocation_id, mode=mode, **changes)
                self.store.record_processing(request.invocation_id, receipt)
                with self.assertRaises(JournalFailure):
                    validated_proposal(self.store, receipt, request.identity)

    def test_planner_never_rewrites_graph_adds_refund_or_hidden_tools(self):
        for output in ({"operation": "refund", "stage": "commit", "arguments": {}, "evidence_refs": []},
                       {"operation": "reschedule", "stage": "commit", "arguments": {}, "evidence_refs": [], "tools": ["shell"]},
                       {"operation": "rewrite_process", "stage": "commit", "arguments": {}, "evidence_refs": []},
                       {"operation": "reschedule", "stage": "commit", "arguments": {"permissions": "all"}, "evidence_refs": []}):
            with self.subTest(output=output):
                planner = BoundedPlanner(lambda checkpoint, observations: self.receipt(
                    output={"kind": "proposal", "proposal": output}), self.service,
                    allowed_steps={"reschedule": {"commit": {"slot"}}}, usage_ceiling={"tokens": 10.0})
                with self.assertRaises((ValueError, JournalFailure)):
                    planner.propose(make_checkpoint(), [])
        self.assertEqual(self.store.checkpoint("C1").budget.planner_calls, 4)
        self.assertEqual(self.store.campaign_usage(self.grant.permit_hash)["invocations"], 4)

    def test_valid_bounded_planner_returns_saved_receipt_not_dispatch(self):
        planner = BoundedPlanner(lambda checkpoint, observations: self.receipt(), self.service,
            allowed_steps={"reschedule": {"commit": {"slot"}}}, usage_ceiling={"tokens": 10.0})
        receipt = planner.propose(make_checkpoint(), [])
        self.assertEqual(receipt.output.proposal.arguments, {"slot": "S1"})
        self.assertEqual(self.store.invocation(receipt.invocation_id)[1], receipt)

    def test_interruption_has_no_usable_proposal(self):
        def interrupted(checkpoint, observations):
            raise TimeoutError()
        planner = BoundedPlanner(interrupted, self.service,
            allowed_steps={"reschedule": {"commit": {"slot"}}}, usage_ceiling={"tokens": 10.0})
        with self.assertRaises(TimeoutError):
            planner.propose(make_checkpoint(), [])
