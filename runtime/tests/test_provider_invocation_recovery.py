from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest

from proofkey.budget import BudgetExceeded
from proofkey.contracts import BudgetLedger, CampaignPermit, InvocationRequest, ProcessingReceipt, ProcessorIdentity, RoleAllowance
from proofkey.identity import fingerprint
from proofkey.journal import CaseStore, JournalFailure
from support import NOW, DEADLINE, CommitFault, make_binding, make_checkpoint, make_request


def permit(role="extraction", **changes):
    data = dict(campaign_id="campaign-1", input_hashes=["1" * 64], role=role, provider="offline-role", model="model-1",
        endpoint="offline://role", privacy_approval="privacy", rights_approval="rights", max_cost=10.0,
        max_usage={"tokens": 100.0}, max_invocations=4, expires_at=DEADLINE, approval_receipt="approval", mode="simulated")
    data.update(changes)
    parsed = CampaignPermit(permit_hash="0" * 64, **data)
    wire = parsed.model_dump(mode="json")
    wire["permit_hash"] = fingerprint({k: v for k, v in wire.items() if k != "permit_hash"})
    return CampaignPermit.model_validate(wire)


def invocation(grant, case="C1", invocation_id="invoke-1", **changes):
    identity = dict(case_id=case, generation="G1", role=grant.role, campaign_id=grant.campaign_id, permit_hash=grant.permit_hash,
        input_hashes=["1" * 64], provider=grant.provider, model=grant.model, endpoint=grant.endpoint,
        prompt_hash="2" * 64, version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
    identity.update(changes)
    return InvocationRequest(identity=ProcessorIdentity(**identity), invocation_id=invocation_id,
        requested_usage={"tokens": 20.0}, worst_case_cost=2.0)


class InvocationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.admit(self.store)

    def admit(self, store, case="C1", role="extraction", max_invocations=3):
        binding = make_binding(case_id=case)
        store.bind(binding)
        store.save_request(binding, make_request(case_id=case))
        budget = BudgetLedger(case_id=case, deadline=DEADLINE, role_allowances={role: RoleAllowance(
            max_invocations=max_invocations, max_cost=6.0, usage_allowances={"tokens": 60.0})})
        store.save_checkpoint(make_checkpoint(binding=binding, budget=budget))

    def test_interrupted_each_role_stays_consumed_after_restart(self):
        for role in ("extraction", "transcription", "planning"):
            case = "case-" + role
            self.admit(self.store, case, role)
            grant = permit(role, campaign_id="campaign-" + role)
            self.store.register_campaign(grant)
            reserved = self.store.reserve_invocation(invocation(grant, case, "invoke-" + role), NOW)
            self.assertEqual(reserved.status, "consumed")
        self.store.close()
        self.store = CaseStore(self.path)
        for role in ("extraction", "transcription", "planning"):
            ledger = self.store.checkpoint("case-" + role).budget
            self.assertEqual(ledger.role_allowances[role].invocations, 1)
            self.assertEqual(ledger.role_allowances[role].cost, 2.0)
            self.assertEqual(ledger.role_allowances[role].usage["tokens"], 20.0)
            self.assertEqual(ledger.tool_calls, 1)
            self.assertEqual(ledger.planner_calls, int(role == "planning"))

    def test_new_attempt_charged_duplicate_id_never_free_reentry(self):
        grant = permit()
        self.store.register_campaign(grant)
        self.store.reserve_invocation(invocation(grant), NOW)
        with self.assertRaises(JournalFailure):
            self.store.reserve_invocation(invocation(grant), NOW)
        self.store.reserve_invocation(invocation(grant, invocation_id="invoke-2"), NOW)
        self.store.reserve_invocation(invocation(grant, invocation_id="invoke-3"), NOW)
        with self.assertRaises(BudgetExceeded):
            self.store.reserve_invocation(invocation(grant, invocation_id="invoke-4"), NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].invocations, 3)

    def test_exact_route_input_expiry_and_permit_registration(self):
        grant = permit()
        with self.assertRaises(JournalFailure):
            self.store.reserve_invocation(invocation(grant), NOW)
        bad = CampaignPermit.model_validate({**grant.model_dump(), "permit_hash": "0" * 64})
        with self.assertRaises(JournalFailure):
            self.store.register_campaign(bad)
        self.store.register_campaign(grant)
        for changes in ({"input_hashes": ["3" * 64]}, {"model": "other"}, {"endpoint": "https://other"},
                        {"provider": "other"}, {"role": "planning"}, {"profile_version": "other"}, {"deadline": DEADLINE + timedelta(seconds=1)}):
            with self.assertRaises(JournalFailure):
                self.store.reserve_invocation(invocation(grant, **changes), NOW)
        with self.assertRaises((JournalFailure, BudgetExceeded)):
            self.store.reserve_invocation(invocation(grant), DEADLINE)

    def test_commit_fault_rolls_back_case_role_and_campaign(self):
        grant = permit(max_invocations=1)
        self.store.register_campaign(grant)
        self.store.close()
        fault = CommitFault()
        self.store = CaseStore(self.path, before_commit=fault)
        fault.arm()
        with self.assertRaises(JournalFailure):
            self.store.reserve_invocation(invocation(grant), NOW)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 0)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 0.0)
        with self.assertRaises(JournalFailure):
            self.store.entry("invocation:invoke-1")
        self.store.reserve_invocation(invocation(grant), NOW)

    def test_unknown_usage_keeps_worst_case_debit_and_receipt_identity(self):
        grant = permit()
        self.store.register_campaign(grant)
        request = invocation(grant)
        self.store.reserve_invocation(request, NOW)
        receipt = ProcessingReceipt(invocation_id="invoke-1", role="extraction", provider=grant.provider,
            requested_model=grant.model, prompt_hash="2" * 64, version="v1", input_hashes=["1" * 64],
            mode="synthetic", status="outcome_unknown", latency_seconds=0.0, usage={}, processed_at=NOW)
        bad = ProcessingReceipt.model_validate({**receipt.model_dump(), "requested_model": "other"})
        with self.assertRaises(JournalFailure):
            self.store.record_processing("invoke-1", bad)
        self.store.record_processing("invoke-1", receipt)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["cost"], 2.0)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["usage"], {"tokens": 20.0})

    def test_crosscase_last_campaign_allowance_is_atomic(self):
        grant = permit(max_invocations=1)
        self.store.register_campaign(grant)
        self.admit(self.store, "C2")
        def compete(case):
            store = CaseStore(self.path)
            try:
                store.reserve_invocation(invocation(grant, case, "invoke-" + case), NOW)
                return "reserved"
            except BudgetExceeded:
                return "denied"
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(compete, ["C1", "C2"]))
        self.assertEqual(sorted(outcomes), ["denied", "reserved"])
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def test_empty_role_allowances_disable_provider_entry(self):
        binding = make_binding(case_id="disabled")
        self.store.admit(binding, make_request(case_id="disabled"), make_checkpoint(binding=binding))
        grant = permit()
        self.store.register_campaign(grant)
        with self.assertRaises(BudgetExceeded):
            self.store.reserve_invocation(invocation(grant, "disabled"), NOW)
        self.assertEqual(self.store.checkpoint("disabled").budget.tool_calls, 0)

    def test_receipt_state_corruption_fails_closed_on_recovery(self):
        import json
        import sqlite3
        grant = permit()
        self.store.register_campaign(grant)
        self.store.reserve_invocation(invocation(grant), NOW)
        receipt = ProcessingReceipt(invocation_id="invoke-1", role="extraction", provider=grant.provider,
            requested_model=grant.model, prompt_hash="2" * 64, version="v1", input_hashes=["1" * 64],
            mode="synthetic", status="outcome_unknown", latency_seconds=0.0, usage={}, processed_at=NOW)
        self.store.record_processing("invoke-1", receipt)
        raw = receipt.model_dump(mode="json")
        raw["status"] = "running"
        db = sqlite3.connect(self.path)
        db.execute("UPDATE invocations SET receipt_json=?", (json.dumps(raw),))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.invocation("invoke-1")

    def test_campaign_consumption_cannot_disagree_with_committed_invocations(self):
        import json
        import sqlite3
        grant = permit()
        self.store.register_campaign(grant)
        self.store.reserve_invocation(invocation(grant), NOW)
        db = sqlite3.connect(self.path)
        db.execute("UPDATE campaigns SET consumed_json=?", (json.dumps({"invocations": 0, "cost": 0.0, "usage": {}}),))
        db.commit()
        db.close()
        with self.assertRaises(JournalFailure):
            self.store.campaign_usage(grant.permit_hash)

    def test_sigkill_after_predebit_each_role_preserves_unknown_attempt(self):
        import signal
        import subprocess
        import sys
        for role in ("extraction", "transcription", "planning"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as folder:
                stage = "provider:" + role
                child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("crash_worker.py")), folder, stage],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertEqual(child.stdout.readline().strip(), "BOUNDARY " + stage)
                child.send_signal(signal.SIGKILL)
                out, err = child.communicate(timeout=10)
                self.assertEqual(child.returncode, -signal.SIGKILL, (out, err))
                recovered = CaseStore(Path(folder) / "journal.sqlite")
                try:
                    reserved, receipt = recovered.invocation("invoke-1")
                    self.assertIsNone(receipt)
                    self.assertEqual(reserved.status, "consumed")
                    ledger = recovered.checkpoint("C1").budget
                    self.assertEqual(ledger.tool_calls, 1)
                    self.assertEqual(ledger.active_seconds, 10.0)
                    self.assertEqual(ledger.planner_calls, int(role == "planning"))
                    self.assertEqual(ledger.role_allowances[role].cost, 2.0)
                finally:
                    recovered.close()

    def test_shared_role_debts_survive_new_generation_and_restart(self):
        grant = permit()
        self.store.register_campaign(grant)
        self.store.reserve_invocation(invocation(grant), NOW)
        newer = make_binding(generation="G2", request_revision="v2", supersedes_generation="G1")
        budget = BudgetLedger(case_id="C1", deadline=DEADLINE, role_allowances={"extraction": RoleAllowance(
            max_invocations=3, max_cost=6.0, usage_allowances={"tokens": 60.0})})
        self.store.admit(newer, make_request(request_revision="v2"), make_checkpoint(binding=newer, budget=budget))
        self.store.close()
        self.store = CaseStore(self.path)
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].invocations, 1)
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].cost, 2.0)

    def test_usage_and_cost_caps_reject_before_any_debit(self):
        grant = permit(max_cost=1.0)
        self.store.register_campaign(grant)
        with self.assertRaises(BudgetExceeded):
            self.store.reserve_invocation(invocation(grant), NOW)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 0)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)

    def test_provider_lease_is_clamped_to_processor_deadline(self):
        grant = permit()
        self.store.register_campaign(grant)
        deadline = NOW + timedelta(seconds=2)
        self.store.reserve_invocation(invocation(grant, deadline=deadline), NOW)
        lease = self.store.entry("invocation:invoke-1")
        self.assertEqual(lease.reserved_seconds, 2.0)
        self.assertEqual(lease.deadline, deadline)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 2.0)

    def test_provider_lease_never_runs_beyond_campaign_expiry(self):
        expiry = NOW + timedelta(seconds=3)
        grant = permit(expires_at=expiry)
        self.store.register_campaign(grant)
        self.store.reserve_invocation(invocation(grant, deadline=expiry), NOW)
        lease = self.store.entry("invocation:invoke-1")
        self.assertEqual(lease.reserved_seconds, 3.0)
        self.assertEqual(lease.deadline, expiry)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 3.0)
