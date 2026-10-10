"""Synthetic public admission/accounting proofs, not content or provider evidence."""
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from proofkey.adapters.world import SimulatedWorld
from proofkey.budget import BudgetExceeded
from proofkey.engine import WorkflowEngine
from proofkey.gateway import ActionGateway
from proofkey.identity import request_fingerprint
from proofkey.journal import CaseStore, JournalFailure
from proofkey.processing import RoleAdmissionLimits
from proofkey.providers.invocations import InvocationService
from support import (DEADLINE, FakeClock, CommitFault, load_test_profile, make_auth,
                     make_fixture_campaign, make_processing_receipt,
                     make_processor_identity, make_request)


def limits(role="extraction", count=2, units=(("tokens", 4.0),), cost=2.0):
    return RoleAdmissionLimits(role, count, units, cost)


class ProcessingAdmissionTests(unittest.TestCase):
    def fixture(self, *, request=None, allowances=None, before_commit=None):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        clock, profile = FakeClock(), load_test_profile("flat-v1.2")
        request = request or make_request(narrative="Synthetic untrusted text")
        world = SimulatedWorld(root / "world.sqlite", Path(__file__).resolve().parents[1] /
            "fixtures/development/world.json", profile=profile, clock=clock)
        world.mutate("customer.request_fingerprint", request_fingerprint(request))
        world.mutate("customer.consent_mode", request.consent_mode)
        store = CaseStore(root / "journal.sqlite", before_commit=before_commit)
        self.addCleanup(lambda: fx.store.close())
        fx = SimpleNamespace(root=root, clock=clock, profile=profile, world=world,
            store=store, request=request, auth=make_auth())
        self.host(fx, allowances)
        return fx

    def host(self, fx, allowances):
        # Explicit host composition supplies the one gateway actually used by engine.
        bundle = fx.world.bundle()
        fx.gateway = ActionGateway(fx.profile, bundle, fx.store, fx.clock,
            auth=fx.auth, processing_allowances=allowances)
        fx.engine = WorkflowEngine(fx.profile, bundle, fx.store, fx.clock,
            gateway=fx.gateway)

    def admit(self, fx):
        fx.gateway.bind_request(fx.request, DEADLINE, initialize_process=True)
        return fx.store.checkpoint("C1")

    def service(self, fx, role="extraction", *, invocation_id="charged-synthetic"):
        cp = fx.store.checkpoint("C1")
        campaign = make_fixture_campaign(role=role)
        fx.store.register_campaign(campaign)
        identity = make_processor_identity(role=role, generation=cp.binding.generation,
            profile_version=cp.profile_version, process_version=cp.process_version,
            deadline=cp.deadline)
        return InvocationService("C1", fx.store, fx.clock, campaign, identity,
            worst_case_cost=1.0, invocation_id_factory=lambda: invocation_id)

    def charge(self, fx, role="extraction", *, fail=False):
        service = self.service(fx, role)
        def entered():
            # First observable callback state must already be durably charged.
            cp = fx.store.checkpoint("C1")
            self.assertEqual(cp.budget.role_allowances[role].invocations, 1)
            self.assertEqual(cp.budget.role_allowances[role].usage, {"tokens": 2.0})
            self.assertEqual(cp.budget.role_allowances[role].cost, 1.0)
            if fail:
                raise RuntimeError("synthetic interrupted callback")
            return make_processing_receipt(role=role,
                invocation_id=service.current_request.invocation_id,
                processed_at=fx.clock.now(), usage={"tokens": 1.0})
        return service.call(role, service.processor_identity.input_hashes,
            {"tokens": 2.0}, entered)

    def test_role_limits_reject_nonexact_or_unbounded_values(self):
        # Catches permissive/coercing configuration that could import caller grants.
        class CustomInt(int):
            pass
        class CustomString(str):
            pass
        bad = [dict(role="other"), dict(role=CustomString("extraction")),
            dict(count=True), dict(count=1.0), dict(count=-1), dict(count=CustomInt(1)),
            dict(cost=True), dict(cost=-1), dict(cost=float("inf")), dict(cost=float("nan")),
            dict(cost=10 ** 1000), dict(units=[]), dict(units=(("tokens", True),)),
            dict(units=(("", 1.0),)), dict(units=((" ", 1.0),)),
            dict(units=(("tokens", -1.0),)), dict(units=(("tokens", float("inf")),)),
            dict(units=(("tokens", float("nan")),)), dict(units=(("tokens", 1.0), ("tokens", 2.0))),
            dict(units=(("z", 1.0), ("a", 1.0))), dict(units=(["tokens", 1.0],)),
            dict(units=(("tokens", 1.0, 2.0),)), dict(units=())]
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises((ValueError, TypeError)):
                limits(**changes)
        disabled = limits(count=0, units=(), cost=0)
        self.assertEqual(disabled.max_invocations, 0)

    def test_constructor_rejects_invalid_recipes_before_source_or_store_entry(self):
        # Catches custom/mutable recipes and capacities above the shared ceilings.
        fx = self.fixture()
        class CustomLimits(RoleAdmissionLimits):
            pass
        class CustomTuple(tuple):
            pass
        bad = [[limits()], {"extraction": limits()}, CustomTuple((limits(),)),
            (object(),), (CustomLimits("extraction", 1, (("tokens", 1.0),), 1.0),),
            (limits(), limits()), (limits("planning", 5),),
            (limits(count=13), limits("transcription", 12)),
            (limits(), limits("transcription"), limits("planning"), limits(count=0, units=()))]
        for recipe in bad:
            with self.subTest(recipe=recipe), self.assertRaises((ValueError, TypeError)):
                self.host(fx, recipe)
        self.assertEqual(fx.world.calls, ())
        with self.assertRaises(JournalFailure):
            fx.store.admission_account("C1")

    def test_stopped_cross_family_replacement_keeps_consumption_and_original_caps(self):
        # Catches re-financing the special stopped-reschedule -> refusal path.
        fx = self.fixture(allowances=(limits(count=1),))
        fx.engine.run(fx.request, fx.auth)
        self.charge(fx)
        fx.engine.stop("C1", "G1", fx.auth)
        before = fx.store.checkpoint("C1")
        self.assertTrue(before.stop.requested)
        self.host(fx, (limits(count=20), limits("planning", 4)))
        fx.request = make_request(request_id="REQ2", request_revision="v2", consent_revision="v2",
            kind="goods_refusal", consent_mode="unknown", arguments={"inventory": {"item-1": 1}},
            narrative="Synthetic replacement request")
        for fact, value in (("case.binding", {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ2"}),
                ("case.generation", "G2"), ("case.request_revision", "v2"), ("customer.consent_revision", "v2"),
                ("customer.consent_mode", "unknown"), ("customer.request_fingerprint", request_fingerprint(fx.request)),
                ("delivery.status", "delivered")):
            fx.world.mutate(fact, value)
        after = self.admit(fx)
        self.assertEqual(after.binding.generation, "G2")
        self.assertFalse(after.stop.requested)
        self.assertEqual(after.budget.role_allowances, before.budget.role_allowances)
        self.assertEqual(after.budget.max_planner_calls, before.budget.max_planner_calls)
        self.assertEqual(after.budget.tool_calls, before.budget.tool_calls + 3)
        self.assertGreaterEqual(after.budget.active_seconds, before.budget.active_seconds)
        self.assertEqual(after.deadline, before.deadline)

    def test_historical_duplicate_cannot_restore_earlier_case_budget_or_new_recipe(self):
        # Catches applying constructor funding during historical duplicate lookup.
        fx = self.fixture(allowances=(limits(count=1),))
        original = fx.request
        self.admit(fx)
        self.charge(fx)
        self.host(fx, (limits(count=20), limits("planning", 4)))
        fx.request = make_request(request_revision="v2", consent_revision="v2", narrative="later content")
        for fact, value in (("case.generation", "G2"), ("case.request_revision", "v2"),
                ("customer.consent_revision", "v2"), ("customer.request_fingerprint", request_fingerprint(fx.request))):
            fx.world.mutate(fact, value)
        before = self.admit(fx)
        result = fx.engine.run(original, fx.auth)
        self.assertEqual(result.status, "denied")
        after = fx.store.checkpoint("C1")
        self.assertEqual(after.binding, before.binding)
        self.assertEqual(after.budget.role_allowances, before.budget.role_allowances)
        self.assertEqual(after.budget.max_planner_calls, before.budget.max_planner_calls)
        self.assertGreaterEqual(after.budget.tool_calls, before.budget.tool_calls)

    def test_fresh_public_engine_imports_explicit_roles_and_admission_debt(self):
        # Catches importing legacy planning-only grants instead of the fixed recipe.
        fx = self.fixture(allowances=(limits(), limits("transcription", 1), limits("planning", 3)))
        result = fx.engine.run(fx.request, fx.auth)
        self.assertEqual(result.status, "authorized")
        cp = fx.store.checkpoint("C1")
        self.assertEqual(set(cp.budget.role_allowances), {"extraction", "transcription", "planning"})
        self.assertEqual(cp.budget.max_planner_calls, 3)
        self.assertEqual(cp.budget.tool_calls, 3)
        self.assertEqual(cp.budget.planner_calls, 0)
        self.assertEqual(cp.budget.active_seconds, 0.0)
        for role, count in (("extraction", 2), ("transcription", 1), ("planning", 3)):
            allowance = cp.budget.role_allowances[role]
            self.assertEqual((allowance.max_invocations, allowance.usage_allowances, allowance.max_cost),
                (count, {"tokens": 4.0}, 2.0))
            self.assertEqual((allowance.invocations, allowance.usage, allowance.cost), (0, {}, 0.0))
        self.assertEqual(fx.store.original_request("C1", "G1"), fx.request)
        self.assertTrue(fx.store.admission_account("C1").imported)
        self.assertEqual([call.operation for call in fx.world.calls], ["read_case", "read_principal", "read_owner"])

    def test_configured_each_role_callback_is_precharged_and_cannot_exceed_capacity(self):
        # Catches unusable fresh caps, uncharged callbacks or case-cap bypass.
        for role in ("extraction", "transcription", "planning"):
            with self.subTest(role=role):
                fx = self.fixture(allowances=(limits(role, 1),))
                fx.engine.run(fx.request, fx.auth)
                receipt = self.charge(fx, role)
                self.assertEqual(receipt.status, "completed")
                before = fx.store.checkpoint("C1").budget
                service = self.service(fx, role, invocation_id="over-cap")
                with self.assertRaises(BudgetExceeded):
                    service.call(role, service.processor_identity.input_hashes, {"tokens": 2.0},
                        lambda: self.fail("exhausted role entered callback"))
                self.assertEqual(fx.store.checkpoint("C1").budget, before)
                self.assertEqual(before.tool_calls, 4)
                self.assertEqual(before.planner_calls, int(role == "planning"))

    def test_none_is_legacy_and_explicit_empty_disables_content_processing(self):
        # Catches conflating empty configuration with None's legacy planning grant.
        for recipe, expected, ceiling in ((None, {"planning"}, 4), ((), set(), 0)):
            with self.subTest(recipe=recipe):
                fx = self.fixture(allowances=recipe)
                cp = self.admit(fx)
                self.assertEqual(set(cp.budget.role_allowances), expected)
                self.assertEqual(cp.budget.max_planner_calls, ceiling)
                service = self.service(fx)
                with self.assertRaises(BudgetExceeded):
                    service.call("extraction", service.processor_identity.input_hashes, {"tokens": 1.0},
                        lambda: self.fail("unfunded role entered callback"))

    def test_structured_configured_case_runs_business_with_zero_planner_ceiling(self):
        # Catches configuration accidentally enabling structured planner entry.
        fx = self.fixture(request=make_request(narrative=" \t"), allowances=(limits("planning", 4),))
        result = fx.engine.run(fx.request, fx.auth)
        self.assertEqual(result.effects["reschedule"].status, "verified")
        cp = fx.store.checkpoint("C1")
        self.assertEqual(cp.budget.max_planner_calls, 0)
        self.assertEqual(cp.budget.planner_calls, 0)
        self.assertEqual(cp.budget.role_allowances["planning"].max_invocations, 4)
        service = self.service(fx, "planning")
        with self.assertRaises(BudgetExceeded):
            service.call("planning", service.processor_identity.input_hashes, {"tokens": 1.0},
                lambda: self.fail("structured planner entered callback"))

    def test_frozen_recipe_is_detached_from_caller_before_admission(self):
        # Catches retaining even a forcibly mutated caller dataclass alias.
        item = limits(count=1)
        fx = self.fixture(allowances=(item,))
        with self.assertRaises(FrozenInstanceError):
            item.max_invocations = 99
        object.__setattr__(item, "max_invocations", 99)
        object.__setattr__(item, "usage_allowances", (("tokens", 99.0),))
        cp = self.admit(fx)
        self.assertEqual(cp.budget.role_allowances["extraction"].max_invocations, 1)
        self.assertEqual(cp.budget.role_allowances["extraction"].usage_allowances, {"tokens": 4.0})

    def test_reopen_recover_and_current_duplicate_keep_consumed_debt_with_richer_host(self):
        # Catches re-financing an existing original on any recovery/current branch.
        fx = self.fixture(allowances=(limits(count=1),))
        fx.engine.run(fx.request, fx.auth)
        with self.assertRaisesRegex(RuntimeError, "synthetic interrupted"):
            self.charge(fx, fail=True)
        before = fx.store.checkpoint("C1")
        self.assertEqual(before.budget.active_seconds, 10.0)
        fx.store.close()
        fx.store = CaseStore(fx.root / "journal.sqlite")
        self.host(fx, (limits(count=20), limits("planning", 4)))
        fx.engine.recover("C1", fx.auth)
        self.admit(fx)
        after = fx.store.checkpoint("C1")
        self.assertEqual(after.budget.role_allowances, before.budget.role_allowances)
        self.assertEqual(after.budget.max_planner_calls, 0)
        self.assertGreater(after.budget.tool_calls, before.budget.tool_calls)
        self.assertGreaterEqual(after.budget.active_seconds, before.budget.active_seconds)
        self.assertEqual(after.deadline, before.deadline)
        self.assertEqual(fx.store.invocation("charged-synthetic")[1].status, "outcome_unknown")

    def test_new_generation_preserves_original_role_caps_and_consumption(self):
        # Catches fresh recipe import when current binding changes generation.
        fx = self.fixture(allowances=(limits(count=1),))
        self.admit(fx)
        self.charge(fx)
        before = fx.store.checkpoint("C1")
        self.host(fx, (limits(count=20), limits("planning", 4)))
        fx.request = make_request(request_revision="v2", consent_revision="v2", narrative="new text")
        for fact, value in (("case.generation", "G2"), ("case.request_revision", "v2"),
                ("customer.consent_revision", "v2"), ("customer.request_fingerprint", request_fingerprint(fx.request))):
            fx.world.mutate(fact, value)
        after = self.admit(fx)
        self.assertEqual(after.binding.generation, "G2")
        self.assertEqual(after.budget.role_allowances, before.budget.role_allowances)
        self.assertEqual(after.budget.max_planner_calls, before.budget.max_planner_calls)
        self.assertEqual(after.budget.tool_calls, before.budget.tool_calls + 3)
        self.assertEqual(after.deadline, before.deadline)

    def test_structured_first_new_content_cannot_upgrade_planner_or_legacy_roles(self):
        # Catches later content retroactively funding structured-first cases.
        for recipe in (None, (), (limits("planning", 4),)):
            with self.subTest(recipe=recipe):
                fx = self.fixture(request=make_request(), allowances=recipe)
                before = self.admit(fx)
                self.host(fx, (limits(), limits("planning", 4)))
                fx.request = make_request(request_revision="v2", consent_revision="v2", narrative="later content")
                for fact, value in (("case.generation", "G2"), ("case.request_revision", "v2"),
                        ("customer.consent_revision", "v2"), ("customer.request_fingerprint", request_fingerprint(fx.request))):
                    fx.world.mutate(fact, value)
                after = self.admit(fx)
                self.assertEqual(after.budget.role_allowances, before.budget.role_allowances)
                self.assertEqual(after.budget.max_planner_calls, 0)

    def test_unauthorized_and_malformed_inputs_never_gain_case_allowances(self):
        # Catches bypassing proof/source validation because a recipe exists.
        fx = self.fixture(allowances=(limits(),))
        self.assertEqual(fx.engine.run(fx.request, make_auth(proof_reference="revoked")).status, "denied")
        self.assertEqual(fx.engine.run({"case_id": "C1", "processing_allowances": (limits(),)}, fx.auth).status, "denied")
        with self.assertRaises(JournalFailure):
            fx.store.checkpoint("C1")
        with self.assertRaises(JournalFailure):
            fx.store.original_request("C1", "G1")
        self.assertEqual(fx.world.effect_count("reschedule"), 0)

    def test_admission_transaction_failure_keeps_unbound_debt_without_partial_funding(self):
        # Catches funding/original writes split from the existing debt transaction.
        fault = CommitFault()
        fx = self.fixture(allowances=(limits(),), before_commit=fault)
        original_admit = fx.store.admit_from_attempt
        def fail_commit(*args):
            fault.arm()
            return original_admit(*args)
        fx.store.admit_from_attempt = fail_commit
        self.assertEqual(fx.engine.run(fx.request, fx.auth).status, "denied")
        with self.assertRaises(JournalFailure):
            fx.store.checkpoint("C1")
        with self.assertRaises(JournalFailure):
            fx.store.original_request("C1", "G1")
        debt = fx.store.admission_account("C1")
        self.assertEqual((debt.tool_calls, debt.pending_tool_calls, debt.imported), (3, 3, False))
        fx.store.admit_from_attempt = original_admit
        cp = self.admit(fx)
        self.assertEqual(cp.budget.tool_calls, 6)
        self.assertEqual(cp.budget.role_allowances["extraction"].invocations, 0)

    def test_constructor_revalidates_tampered_mutable_role_values_before_capture(self):
        # Catches normalizing a corrupted typed recipe into a newly valid grant.
        fx = self.fixture()
        for mutable_units in ([ ("tokens", 4.0) ], (["tokens", 4.0],)):
            item = limits()
            object.__setattr__(item, "usage_allowances", mutable_units)
            with self.subTest(units=mutable_units), self.assertRaises((ValueError, TypeError)):
                self.host(fx, (item,))
        self.assertEqual(fx.world.calls, ())


if __name__ == "__main__":
    unittest.main()
