import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import threading
from types import SimpleNamespace
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from unittest.mock import patch
from proofkey.contracts import (ArtifactRecord, AuthContext, AssertionsOutput, AuthorityObservation, BudgetLedger, InvocationRequest,
    EvidenceAssertion, ProcessingReceipt, ProcessorIdentity, RoleAllowance, UnknownLocator)
from proofkey.evidence.catalog import EvidenceCatalog
from proofkey.evidence.processing_contracts import (PlanningEvidenceInputV2,
    ProcessingCatalogBindings, ProcessingPublicationError, SavedOriginalScope, canonical)
from proofkey.execution import ExecutionContext
from proofkey.gateway import ActionGateway
from proofkey.identity import fingerprint
from proofkey.processing import RoleAdmissionLimits
from proofkey.processing_orchestration import (PlanningRegistration, ProcessingRecipe,
    ProcessingOrchestrator, ProcessingStepOutcome)
from proofkey.providers.anthropic import AnthropicClient, ENDPOINT
from proofkey.providers.invocations import InvocationService, output_digest
from proofkey.providers.protocols import TransportResponse
from support import (DEADLINE, NOW, FakeClock, build_test_runtime, make_binding,
    make_checkpoint, make_fixture_campaign, make_request)

PROMPT = "Synthetic prepared V2 planner"
USAGE = (("input_tokens", 100.0), ("output_tokens", 32.0))

class Clock(FakeClock):
    def __init__(self):
        super().__init__()
        self.seconds = 0.0
    def monotonic(self): return self.seconds
    def advance(self, seconds):
        self.seconds += seconds
        super().advance(seconds)

class PreparedConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.fx = build_test_runtime(self.root, profile_name="flat-v1",
            request=make_request(narrative="Box condition uncertain.\n"))
        self.store, self.auth, self.clock = self.fx.store, self.fx.auth, Clock()
        self.addCleanup(self.store.close)
        self.original, self.binding = self.fx.request, make_binding(self.fx.request)
        self.gateway = ActionGateway(self.fx.profile, self.fx.world.bundle(),
            self.store, self.clock, auth=self.auth)
        budget = BudgetLedger(case_id="C1", deadline=DEADLINE,
            role_allowances={
                "extraction": RoleAllowance(max_invocations=2, max_cost=2.0,
                    usage_allowances={"tokens": 4.0}),
                "planning": RoleAllowance(max_invocations=2, max_cost=2.0,
                    usage_allowances={"input_tokens": 200.0, "output_tokens": 64.0})})
        self.store.admit(self.binding, self.original, make_checkpoint(binding=self.binding,
            phase="window_gate", next_gate="reschedule", budget=budget))
        self.scope_bytes = canonical(dict(allowed_actors=["U1"], case_id="C1", object_id="O1",
            binding_hash=fingerprint(self.binding.model_dump(mode="json")),
            original_request_hash=fingerprint(self.original.model_dump(mode="json")),
            scope_id="saved-scope", policy_id="synthetic-local-policy",
            authorization_reference="synthetic-proof", provenance="synthetic_host_registration",
            expires_at=DEADLINE.isoformat()))
        def original_lookup(binding):
            if self.store.find_request(binding.case_id, binding.request_id,
                binding.request_revision, binding.consent_revision, binding.fingerprint) != binding:
                raise ValueError("Exact durable original required")
            return self.store.original_request(binding.case_id, binding.generation)
        def saved_scope(binding, original, auth, purpose):
            if (binding, original, auth) != (self.binding, self.original, self.auth) or self.clock.now() >= DEADLINE:
                return None
            return SavedOriginalScope(canonical(self.binding.model_dump(mode="json")),
                fingerprint(self.original.model_dump(mode="json")), "saved-scope", self.scope_bytes,
                "synthetic-local-policy", "synthetic_host_registration", "synthetic-proof", DEADLINE)
        def access(auth, record, scope, purpose):
            return (auth == self.auth and record.case_id == self.binding.case_id
                and scope.get("scope_id") == "saved-scope" and scope.get("allowed_actors") == ("U1",))
        self.catalog = EvidenceCatalog(self.root / "catalog", self.clock,
            allowed_input_roots=[self.root], access_resolver=access,
            processing_bindings=ProcessingCatalogBindings(original_lookup,
                lambda b: self.store.checkpoint(b.case_id), self.store.invocation, saved_scope,
                profile_lookup=lambda b, o: self.fx.profile))
        self.observations = (AuthorityObservation(authority="delivery", fact="delivery.status",
            object_id="O1", value="scheduled", revision="v1", observed_at=NOW,
            evidence_ref="synthetic-source-status"),)
        self.ids, self.requests = [], []
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            blocker = patch(target, side_effect=AssertionError("No network"))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.record, self.input = self.prepare_public_input()

    def prepare_public_input(self):
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        grant = make_fixture_campaign(role="extraction", input_hashes=[record.original_hash],
            max_usage={"tokens": 2.0}, campaign_id="synthetic-extract")
        self.store.register_campaign(grant)  # independent host setup, before callback
        identity = ProcessorIdentity(case_id="C1", generation="G1", role="extraction",
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash,
            input_hashes=grant.input_hashes, provider=grant.provider, model=grant.model,
            endpoint=grant.endpoint, prompt_hash=hashlib.sha256(PROMPT.encode()).hexdigest(),
            version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
        service = InvocationService("C1", self.store, self.clock, grant, identity,
            worst_case_cost=1.0, invocation_id_factory=lambda: "extract-1")
        def invoke():
            self.catalog.seal_invocation_inputs(self.binding, "extract-1", (record.artifact_id,), self.auth)
            output = AssertionsOutput(kind="assertions", assertions=[EvidenceAssertion(
                artifact_id=record.artifact_id, content_hash=record.original_hash,
                lineage_hash=record.lineage_hash, claim="Damaged", locator=UnknownLocator(reason="not_measured"),
                uncertainty="unverified", processing_receipt_id="extract-1")])
            return ProcessingReceipt(invocation_id="extract-1", role="extraction",
                provider=identity.provider, requested_model=identity.model, prompt_hash=identity.prompt_hash,
                version=identity.version, input_hashes=identity.input_hashes, mode="synthetic",
                status="completed", latency_seconds=0.0, usage={"tokens": 1.0}, output=output,
                output_hashes=[output_digest(output)], processed_at=self.clock.now())
        service.call("extraction", identity.input_hashes, {"tokens": 2.0}, invoke)
        self.catalog.publish_processing_output(self.binding, "extract-1", self.auth)
        record = self.catalog.register_planning_evidence_snapshot(self.store.checkpoint("C1"),
            self.observations, ("extract-1",), self.auth)
        return record, PlanningEvidenceInputV2.from_bytes(self.catalog.read_original(record.artifact_id, self.auth))

    def grant(self, hashes, *, campaign_id="synthetic-prepared-plan"):
        return make_fixture_campaign(role="planning", campaign_id=campaign_id,
            provider="anthropic", endpoint=ENDPOINT, input_hashes=list(hashes), max_usage=dict(USAGE))

    def consumer(self, grants):
        def transport(request):
            self.requests.append(request)
            self.clock.advance(0.25)
            output = {"kind": "proposal", "proposal": {"operation": "reschedule", "stage": "commit",
                "arguments": {"slot": "S1"}, "evidence_refs": ["synthetic-source-status"]}}
            return TransportResponse(200, canonical({"id": "msg-synthetic", "type": "message",
                "role": "assistant", "model": "synthetic-observed", "stop_reason": "end_turn",
                "content": [{"type": "text", "text": json.dumps(output)}],
                "usage": {"input_tokens": 7, "output_tokens": 3}}))
        processor = AnthropicClient(transport, system_prompt=PROMPT, max_tokens=32)
        registrations = tuple(PlanningRegistration(binding_bytes=canonical(self.binding.model_dump(mode="json")),
            campaign_bytes=canonical(g.model_dump(mode="json")), processor=processor,
            prompt_hash=hashlib.sha256(PROMPT.encode()).hexdigest(), version="v1",
            profile_version="v1", process_version="v1", usage_ceiling=USAGE, worst_case_cost=1.0,
            allowed_steps=(("reschedule", "commit", ("slot",)),)) for g in grants)
        recipe = ProcessingRecipe(allowances=(RoleAdmissionLimits("planning", 2,
            (("input_tokens", 200.0), ("output_tokens", 64.0)), 2.0),), planning_registrations=registrations)
        def next_id():
            value = "plan-" + str(len(self.ids) + 1)
            self.ids.append(value)
            return value
        return ProcessingOrchestrator(self.store, self.clock, self.catalog,
            parent_gateway=self.gateway, recipe=recipe, invocation_id_factory=next_id)
    def test_exact_registered_prepared_v2_returns_saved_validated_planning_output(self):
        before = self.store.checkpoint("C1")
        self.assertEqual(before, self.input.checkpoint())
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)  # outside consumer/provider callbacks
        self.assertEqual(self.store.checkpoint("C1"), before)
        consumer = self.consumer((grant,))
        execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=20), self.clock)
        with self.gateway.execution_scope(execution):
            outcome = consumer.plan_prepared(self.record, self.input, self.auth)
        self.assertEqual(outcome.status, "completed")
        reservation, saved = self.store.invocation(outcome.receipt.invocation_id)
        self.assertEqual(saved, outcome.receipt)
        self.assertEqual(reservation.status, "completed")
        self.assertEqual(saved.input_hashes, [self.input.envelope_hash])
        self.assertEqual(saved.output.proposal.arguments, {"slot": "S1"})
        self.assertEqual(outcome.publication.invocation_id, saved.invocation_id)
        self.assertEqual(self.ids, ["plan-1"])
        self.assertEqual(len(self.requests), 1)
        body = json.loads(self.requests[0].body)
        self.assertEqual(body["messages"][0]["content"][0]["text"], self.input.envelope_bytes.decode("utf-8"))
        current = self.store.checkpoint("C1")
        self.assertEqual(current.budget.planner_calls, before.budget.planner_calls + 1)
        self.assertNotEqual(current, self.input.checkpoint())  # debit is historical, not a publication denial
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)
        self.assertEqual([a.invocation_id for a, r in self.store.processing_attempts(self.binding)],
                         ["extract-1", "plan-1"])
    def test_absent_unregistered_or_mismatched_permit_keeps_original_accounting(self):
        exact = self.grant((self.input.envelope_hash,))
        wrong = self.grant(("f" * 64,))
        self.store.register_campaign(wrong)  # host setup only; exact remains unregistered
        before = (self.store.checkpoint("C1"), self.store.processing_attempts(self.binding),
                  self.store.campaign_usage(wrong.permit_hash))
        for registrations in ((), (exact,), (wrong,)):
            with self.subTest(permits=len(registrations)):
                consumer = self.consumer(registrations)
                execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=20), self.clock)
                with self.gateway.execution_scope(execution):
                    outcome = consumer.plan_prepared(self.record, self.input, self.auth)
                self.assertEqual(outcome.status, "unavailable")
                self.assertEqual(outcome.entry_local_reason, "permit_unavailable")
                self.assertIsNone(outcome.receipt)
                self.assertIsNone(outcome.publication)
                self.assertEqual(self.ids, [])
                self.assertEqual(self.requests, [])
                self.assertEqual((self.store.checkpoint("C1"), self.store.processing_attempts(self.binding),
                                  self.store.campaign_usage(wrong.permit_hash)), before)

    def test_registration_rejects_literal_malformed_mutable_and_widened_configuration(self):
        # Break caught: omitting any individual constructor guard admits unsafe configuration.
        grant = self.grant((self.input.envelope_hash,))
        good = self.consumer((grant,)).recipe.planning_registrations[0]
        wire = grant.model_dump(mode="json")
        bad_wire = {**wire, "permit_hash": "0" * 64}
        unknown_wire = {**wire, "unknown": True}
        missing_wire = {k: v for k, v in wire.items() if k != "max_invocations"}
        cases = [
            {"binding_bytes": bytearray(good.binding_bytes)},
            {"binding_bytes": good.binding_bytes + b" "},
            {"binding_bytes": b"x" * 65537},
            {"binding_bytes": canonical({**self.binding.model_dump(mode="json"), "unknown": True})},
            {"binding_bytes": good.binding_bytes.replace(b'"case_id":"C1"', b'"case_id":"C1","case_id":"C1"')},
            {"campaign_bytes": bytearray(good.campaign_bytes)},
            {"campaign_bytes": b"x" * 131073},
            {"campaign_bytes": canonical(bad_wire)},
            {"campaign_bytes": canonical(unknown_wire)},
            {"campaign_bytes": canonical(missing_wire)},
            {"campaign_bytes": good.campaign_bytes.replace(b'"role":"planning"', b'"role":"planning","role":"planning"')},
            {"campaign_bytes": canonical(make_fixture_campaign(role="extraction").model_dump(mode="json"))},
            {"campaign_bytes": canonical(self.grant((self.input.envelope_hash, "f" * 64)).model_dump(mode="json"))},
            {"campaign_bytes": canonical(make_fixture_campaign(role="planning", mode="actual").model_dump(mode="json"))},
            {"prompt_hash": "bad"}, {"prompt_hash": True}, {"prompt_hash": good.prompt_hash.encode()},
            {"version": " "}, {"version": b"v1"},
            {"profile_version": True}, {"process_version": ""}, {"processor": object()},
            {"usage_ceiling": list(USAGE)}, {"usage_ceiling": (["input_tokens", 100.0],)},
            {"usage_ceiling": ()}, {"usage_ceiling": (("", 1.0),)},
            {"usage_ceiling": (("tokens", 1.0), ("tokens", 1.0))},
            {"usage_ceiling": tuple(("u" + str(i), 1.0) for i in range(9))},
            {"usage_ceiling": (("input_tokens", True),)},
            {"usage_ceiling": (("input_tokens", 1),)},
            {"usage_ceiling": (("input_tokens", 0.0),)},
            {"usage_ceiling": (("input_tokens", float("inf")),)},
            {"usage_ceiling": (("input_tokens", float("nan")),)},
            {"usage_ceiling": (("input_tokens", 101.0), ("output_tokens", 32.0))},
            {"worst_case_cost": True}, {"worst_case_cost": 1}, {"worst_case_cost": -1.0},
            {"worst_case_cost": float("inf")}, {"worst_case_cost": float("nan")},
            {"worst_case_cost": 5.0},
            {"allowed_steps": [("reschedule", "commit", ("slot",))]},
            {"allowed_steps": (["reschedule", "commit", ("slot",)],)},
            {"allowed_steps": (("reschedule", "commit", ["slot"]),)},
            {"allowed_steps": (("reschedule", "commit", ("slot", "slot")),)},
            {"allowed_steps": (("reschedule", "commit", (" ",)),)},
            {"allowed_steps": ((True, "commit", ("slot",)),)},
            {"allowed_steps": ((b"reschedule", "commit", ("slot",)),)},
            {"allowed_steps": (("reschedule", b"commit", ("slot",)),)},
            {"allowed_steps": (("reschedule", "commit", (b"slot",)),)},
            {"allowed_steps": (("reschedule", "commit", ("slot",)), ("reschedule", "commit", ("slot",)))},
            {"allowed_steps": tuple(("op" + str(i), "commit", ()) for i in range(9))},
            {"allowed_steps": (("reschedule", "commit", tuple("key" + str(i) for i in range(9))),)},
        ]
        before = (self.store.checkpoint("C1"), self.store.processing_attempts(self.binding))
        for index, changes in enumerate(cases):
            with self.subTest(case=index, fields=tuple(changes)):
                with self.assertRaises((ValueError, TypeError)):
                    replace(good, **changes)
        self.assertEqual((self.store.checkpoint("C1"), self.store.processing_attempts(self.binding)), before)
        for value, attribute in ((good, "prompt_hash"), (self.consumer((grant,)).recipe, "allowances")):
            with self.assertRaises((FrozenInstanceError, AttributeError)):
                setattr(value, attribute, None)
            self.assertFalse(hasattr(value, "__dict__"))

    def test_recipe_rejects_duplicate_ambiguous_nonexact_and_incompatible_limits(self):
        # Break caught: recipe aliases, duplicate selection, or caps without an enabled role enter processing.
        grant = self.grant((self.input.envelope_hash,))
        good = self.consumer((grant,)).recipe
        registration = good.planning_registrations[0]
        alternate = replace(registration, version="v2")
        for index, changes in enumerate((
                {"allowances": list(good.allowances)}, {"allowances": None},
                {"allowances": (object(),)}, {"allowances": good.allowances * 2},
                {"planning_registrations": list(good.planning_registrations)},
                {"planning_registrations": (object(),)},
                {"planning_registrations": (registration,) * 5},
                {"planning_registrations": (registration, registration)},
                {"planning_registrations": (registration, alternate)},
                {"allowances": ()},
                {"allowances": (RoleAdmissionLimits("planning", 0, (), 0.0),)},
                {"allowances": (RoleAdmissionLimits("planning", 1, (("input_tokens", 99.0), ("output_tokens", 32.0)), 1.0),)},
                {"allowances": (RoleAdmissionLimits("planning", 1, USAGE, 0.5),)})):
            with self.subTest(case=index, fields=tuple(changes)):
                with self.assertRaises((ValueError, TypeError)):
                    replace(good, **changes)

    def test_outcome_and_orchestrator_constructors_preserve_typed_scope_and_privacy(self):
        # Break caught: forged public completion or foreign parent/ID factory survives construction.
        recipe = self.consumer(()).recipe
        for parent, store, clock, factory in (
                (object(), self.store, self.clock, None),
                (None, self.store, self.clock, None),
                (self.gateway, object(), self.clock, None),
                (self.gateway, self.store, object(), None),
                (self.gateway, self.store, self.clock, object())):
            with self.subTest(parent=parent, factory=factory):
                with self.assertRaises((ValueError, TypeError)):
                    ProcessingOrchestrator(store, clock, self.catalog, parent_gateway=parent,
                        recipe=recipe, invocation_id_factory=factory)
        with self.subTest(case="recipe"):
            with self.assertRaises((ValueError, TypeError)):
                ProcessingOrchestrator(self.store, self.clock, self.catalog,
                    parent_gateway=self.gateway, recipe=object())
        for kwargs in ({"status": "completed"}, {"status": "wrong"},
                {"status": "unavailable", "entry_local_reason": "wrong"},
                {"status": "denied", "receipt": object(), "entry_local_reason": "scope_denied"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises((ValueError, TypeError)):
                    ProcessingStepOutcome(**kwargs)
        consumer = self.consumer(())
        for name, original in (("store", self.store), ("clock", self.clock),
                ("catalog", self.catalog), ("parent_gateway", self.gateway), ("recipe", consumer.recipe)):
            self.assertIs(getattr(consumer, name), original)
            with self.assertRaises(AttributeError):
                setattr(consumer, name, object())

    def run_consumer(self, consumer, record=None, input=None, auth=None):
        execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=20), self.clock)
        with self.gateway.execution_scope(execution):
            return consumer.plan_prepared(record or self.record, input or self.input, auth or self.auth)

    def assert_private_failure(self, outcome, status, reason):
        self.assertEqual((outcome.status, outcome.entry_local_reason), (status, reason))
        self.assertIsNone(outcome.receipt)
        self.assertIsNone(outcome.publication)

    def durable_state(self, grant):
        return (self.store.checkpoint("C1"), self.store.processing_attempts(self.binding),
            self.store.campaign_usage(grant.permit_hash))

    def add_extraction(self, identifier, *, empty=False, failed=False):
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        grant = make_fixture_campaign(role="extraction", input_hashes=[record.original_hash],
            max_usage={"tokens": 2.0}, campaign_id="synthetic-" + identifier)
        self.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id="C1", generation="G1", role="extraction",
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash,
            input_hashes=grant.input_hashes, provider=grant.provider, model=grant.model,
            endpoint=grant.endpoint, prompt_hash=hashlib.sha256(PROMPT.encode()).hexdigest(),
            version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
        service = InvocationService("C1", self.store, self.clock, grant, identity,
            worst_case_cost=1.0, invocation_id_factory=lambda: identifier)
        def invoke():
            self.catalog.seal_invocation_inputs(self.binding, identifier, (record.artifact_id,), self.auth)
            assertions = [] if empty else [EvidenceAssertion(artifact_id=record.artifact_id,
                content_hash=record.original_hash, lineage_hash=record.lineage_hash, claim="Unverified",
                locator=UnknownLocator(reason="not_measured"), uncertainty="unverified",
                processing_receipt_id=identifier)]
            output = None if failed else AssertionsOutput(kind="assertions", assertions=assertions)
            return ProcessingReceipt(invocation_id=identifier, role="extraction",
                provider=identity.provider, requested_model=identity.model, prompt_hash=identity.prompt_hash,
                version="v1", input_hashes=identity.input_hashes, mode="synthetic",
                status="failed" if failed else "completed", latency_seconds=0.0, usage={"tokens": 1.0},
                output=output, output_hashes=[] if failed else [output_digest(output)],
                processed_at=self.clock.now())
        service.call("extraction", identity.input_hashes, {"tokens": 2.0}, invoke)
        if not failed:
            self.catalog.publish_processing_output(self.binding, identifier, self.auth)

    def prepare_again(self, identifiers=("extract-1",)):
        record = self.catalog.register_planning_evidence_snapshot(self.store.checkpoint("C1"),
            self.observations, identifiers, self.auth)
        return record, PlanningEvidenceInputV2.from_bytes(self.catalog.read_original(record.artifact_id, self.auth))

    def test_exhausted_campaign_and_recipe_debt_deny_before_id_or_debit(self):
        # Break caught: preflight creates an ID or resets earlier debt on an exhausted scope.
        grant = make_fixture_campaign(role="planning", campaign_id="synthetic-zero",
            provider="anthropic", endpoint=ENDPOINT, input_hashes=[self.input.envelope_hash],
            max_usage=dict(USAGE), max_invocations=0)
        self.store.register_campaign(grant)
        before = self.durable_state(grant)
        self.assert_private_failure(self.run_consumer(self.consumer((grant,))), "unavailable", "permit_unavailable")
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])
        self.assertEqual(self.durable_state(grant), before)

    def test_prior_planning_debt_obeys_smaller_recipe_without_reset(self):
        # Break caught: only original role balances are checked, ignoring smaller constructor caps.
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        self.assertEqual(self.run_consumer(self.consumer((grant,))).status, "completed")
        self.record, self.input = self.prepare_again()
        next_grant = self.grant((self.input.envelope_hash,), campaign_id="synthetic-next-plan")
        self.store.register_campaign(next_grant)
        consumer = self.consumer((next_grant,))
        recipe = replace(consumer.recipe, allowances=(RoleAdmissionLimits("planning", 1, USAGE, 1.0),))
        limited = ProcessingOrchestrator(self.store, self.clock, self.catalog,
            parent_gateway=self.gateway, recipe=recipe, invocation_id_factory=lambda: self.ids.append("forbidden") or "forbidden")
        before = self.durable_state(next_grant)
        self.assert_private_failure(self.run_consumer(limited), "unavailable", "permit_unavailable")
        self.assertEqual(self.ids, ["plan-1"])
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.durable_state(next_grant), before)

    def test_full_mixed_extraction_inventory_rejects_subset_and_reordered_ids(self):
        # Break caught: a valid registrar subset/order is mistaken for all durable publications.
        self.add_extraction("extract-empty", empty=True)
        for index, identifiers in enumerate((("extract-1",), ("extract-empty", "extract-1"))):
            with self.subTest(identifiers=identifiers):
                record, input = self.prepare_again(identifiers)
                grant = self.grant((input.envelope_hash,), campaign_id="synthetic-invalid-order-" + str(index))
                self.store.register_campaign(grant)
                before = self.durable_state(grant)
                self.assert_private_failure(self.run_consumer(self.consumer((grant,)), record, input),
                    "unavailable", "input_unavailable")
                self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])
        self.record, self.input = self.prepare_again(("extract-1", "extract-empty"))
        grant = self.grant((self.input.envelope_hash,), campaign_id="synthetic-full-order")
        self.store.register_campaign(grant)
        outcome = self.run_consumer(self.consumer((grant,)))
        self.assertEqual(outcome.status, "completed")
        self.assertEqual([p.invocation_id for p in self.input.extraction_publications()], ["extract-1", "extract-empty"])
        self.assertEqual([len(p.assertions()) for p in self.input.extraction_publications()], [1, 0])
        self.assertEqual([a.invocation_id for a, _ in self.store.processing_attempts(self.binding)],
            ["extract-1", "extract-empty", "plan-1"])

    def test_unrelated_failed_extraction_keeps_debt_but_does_not_replace_eligible_inputs(self):
        # Dependency characterization if initially green: failed history is not an input or refund.
        self.add_extraction("extract-failed", failed=True)
        self.record, self.input = self.prepare_again()
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        before = self.store.checkpoint("C1").budget.role_allowances["extraction"]
        outcome = self.run_consumer(self.consumer((grant,)))
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(before.invocations, 2)
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"], before)
        self.assertEqual([(a.invocation_id, a.status) for a, _ in self.store.processing_attempts(self.binding)],
            [("extract-1", "completed"), ("extract-failed", "failed"), ("plan-1", "completed")])

    def test_custom_companions_record_and_auth_aliases_never_enter(self):
        # Break caught: duck types/subclasses bypass the exact caller input boundary.
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        class InputAlias(PlanningEvidenceInputV2):
            pass
        class RecordAlias(ArtifactRecord):
            pass
        class AuthAlias(AuthContext):
            pass
        alias = InputAlias(self.input.checkpoint_bytes, self.input.observation_bytes,
            self.input.extraction_publication_bytes, self.input.envelope_bytes, self.input.envelope_hash)
        pairs = ((self.record, alias, self.auth),
            (RecordAlias(**self.record.model_dump()), self.input, self.auth),
            (self.record, self.input, AuthAlias(**self.auth.model_dump())),
            (self.record, SimpleNamespace(checkpoint=lambda: self.ids.append("alias-read") or self.input.checkpoint(),
                observations=self.input.observations, extraction_publications=self.input.extraction_publications,
                envelope_hash=self.input.envelope_hash), self.auth))
        for index, (record, input, auth) in enumerate(pairs):
            with self.subTest(case=index):
                before = self.durable_state(grant)
                outcome = self.run_consumer(consumer, record, input, auth)
                self.assertNotEqual(outcome.status, "completed")
                self.assertIsNone(outcome.receipt)
                self.assertIsNone(outcome.publication)
                self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])

    def test_recursive_entry_is_denied_by_creator_lock_with_only_outer_debit(self):
        # Break caught: no orchestrator lock, allowing nested input/source entry under one creator.
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.transport
        nested = []
        def transport(request):
            nested.append(consumer.plan_prepared(self.record, self.input, self.auth))
            return original(request)
        processor.transport = transport
        outcome = self.run_consumer(consumer)
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(len(nested), 1)
        self.assert_private_failure(nested[0], "denied", "scope_denied")
        self.assertEqual(self.ids, ["plan-1"])
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def assert_no_effects(self):
        for operation in ("reschedule", "register_goods_refusal", "register_service_refusal",
                "create_return", "send_clarification", "send_status", "enqueue_handoff", "transfer_owner"):
            self.assertEqual(self.fx.world.effect_count(operation), 0)

    def rejected_proposal(self, proposal):
        # These are saved-receipt validator/privacy characterizations if initially green.
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.transport
        def transport(request):
            response = original(request)
            envelope = json.loads(response.body)
            envelope["content"][0]["text"] = json.dumps({"kind": "proposal", "proposal": proposal})
            return TransportResponse(200, canonical(envelope))
        processor.transport = transport
        outcome = self.run_consumer(consumer)
        self.assert_private_failure(outcome, "denied", "output_rejected")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("completed", "completed"))
        self.assertEqual(self.store.checkpoint("C1").budget.planner_calls, 1)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)
        self.assertEqual(self.ids, ["plan-1"])
        self.assertEqual(len(self.requests), 1)
        self.assert_no_effects()
        # Observe actual output artifacts: moving publication ahead of semantic
        # validation would create a private-proposal file despite the denied outcome.
        self.assertEqual(tuple((self.root / "catalog" / "receipts").glob("private-proposal-*.json")), ())

    def test_illegal_operation_keeps_completed_private_debt_and_no_usable_suggestion(self):
        self.rejected_proposal({"operation": "create_return", "stage": "commit",
            "arguments": {"slot": "S1"}, "evidence_refs": ["synthetic-source-status"]})

    def test_illegal_stage_keeps_completed_private_debt_and_no_usable_suggestion(self):
        self.rejected_proposal({"operation": "reschedule", "stage": "other",
            "arguments": {"slot": "S1"}, "evidence_refs": ["synthetic-source-status"]})

    def test_illegal_argument_keeps_completed_private_debt_and_no_usable_suggestion(self):
        self.rejected_proposal({"operation": "reschedule", "stage": "commit",
            "arguments": {"slot": "S1", "admin": True}, "evidence_refs": ["synthetic-source-status"]})

    def test_absent_reference_keeps_completed_private_debt_and_no_usable_suggestion(self):
        self.rejected_proposal({"operation": "reschedule", "stage": "commit",
            "arguments": {"slot": "S1"}, "evidence_refs": ["invented-model-authority"]})

    def test_callback_exception_retains_unknown_and_subsequent_lawful_entry(self):
        # Initial-green service debt characterization; new consumer must retain finite privacy.
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        def transport(request):
            self.requests.append(request)
            raise RuntimeError("Private injected failure")
        processor.transport = transport
        self.assert_private_failure(self.run_consumer(consumer), "denied", "processing_interrupted")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("outcome_unknown", "outcome_unknown"))
        self.assertIsNone(saved.output)
        self.assertEqual(self.store.checkpoint("C1").budget.planner_calls, 1)
        self.record, self.input = self.prepare_again()
        next_grant = self.grant((self.input.envelope_hash,), campaign_id="synthetic-recovery-plan")
        self.store.register_campaign(next_grant)
        # The old consumer lock released, but its old exact grant remains historical.
        before = self.durable_state(next_grant)
        self.assert_private_failure(self.run_consumer(consumer), "unavailable", "permit_unavailable")
        self.assertEqual(self.durable_state(next_grant), before)
        self.assertEqual(self.run_consumer(self.consumer((next_grant,))).status, "completed")
        self.assertEqual([a.invocation_id for a, _ in self.store.processing_attempts(self.binding)],
            ["extract-1", "plan-1", "plan-2"])
        self.assert_no_effects()

    def test_invalid_callback_receipt_keeps_unknown_without_private_output(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.propose_with_evidence
        def propose(input, context):
            return original(input, context).model_copy(update={"requested_model": "foreign-model"})
        processor.propose_with_evidence = propose
        self.assert_private_failure(self.run_consumer(consumer), "denied", "processing_interrupted")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("outcome_unknown", "outcome_unknown"))
        self.assertIsNone(saved.output)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def test_late_callback_keeps_real_debt_without_completed_output(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.transport
        def transport(request):
            response = original(request)
            self.clock.seconds += 11.0
            return response
        processor.transport = transport
        self.assert_private_failure(self.run_consumer(consumer), "denied", "processing_interrupted")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("outcome_unknown", "outcome_unknown"))
        self.assertIsNone(saved.output)
        self.assertEqual(self.store.checkpoint("C1").budget.active_seconds, 120.0)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def test_revoked_acl_during_transport_never_returns_saved_private_receipt(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.transport
        def transport(request):
            response = original(request)
            self.catalog.access_resolver = lambda *args: False
            return response
        processor.transport = transport
        self.assert_private_failure(self.run_consumer(consumer), "denied", "scope_denied")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("completed", "completed"))
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)
        self.assert_no_effects()

    def test_persistently_invalid_original_clock_retains_consumed_without_fabricated_unknown(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.transport
        clock_now = self.clock.now
        def transport(request):
            response = original(request)
            self.clock.now = lambda: None
            return response
        processor.transport = transport
        try:
            outcome = self.run_consumer(consumer)
        finally:
            self.clock.now = clock_now
        self.assert_private_failure(outcome, "denied", "processing_interrupted")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual(attempt.status, "consumed")
        self.assertIsNone(saved)
        self.assertEqual(self.store.checkpoint("C1").budget.planner_calls, 1)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def test_inactive_parent_wrong_thread_wrong_proof_and_changed_association_deny_pre_id(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        before = self.durable_state(grant)
        self.assert_private_failure(consumer.plan_prepared(self.record, self.input, self.auth), "denied", "scope_denied")
        outcomes = []
        thread = threading.Thread(target=lambda: outcomes.append(consumer.plan_prepared(self.record, self.input, self.auth)))
        execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=20), self.clock)
        with self.gateway.execution_scope(execution):
            thread.start()
            thread.join()
        self.assert_private_failure(outcomes[0], "denied", "scope_denied")
        wrong_auth = self.auth.model_copy(update={"proof_reference": "wrong-proof"})
        self.assert_private_failure(self.run_consumer(consumer, auth=wrong_auth), "denied", "scope_denied")
        original_clock = self.gateway.clock
        self.gateway.clock = Clock()
        try:
            self.assert_private_failure(self.run_consumer(consumer), "denied", "scope_denied")
        finally:
            self.gateway.clock = original_clock
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])
        self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(self.run_consumer(consumer).status, "completed")

    def test_changed_record_companion_and_checkpoint_are_unusable_before_permit_disclosure(self):
        # Exact-input characterizations: a missing permit must not hide an invalid current input.
        consumer = self.consumer(())
        for record, input in ((self.record.model_copy(update={"source": "foreign-source"}), self.input),
                (self.record.model_copy(update={"case_id": "C2"}), self.input)):
            with self.subTest(source=record.source, case=record.case_id):
                self.assert_private_failure(self.run_consumer(consumer, record, input), "unavailable", "input_unavailable")
        observations = (self.observations[0].model_copy(update={"evidence_ref": "different-source"}),)
        other_record = self.catalog.register_planning_evidence_snapshot(self.store.checkpoint("C1"),
            observations, ("extract-1",), self.auth)
        other_input = PlanningEvidenceInputV2.from_bytes(self.catalog.read_original(other_record.artifact_id, self.auth))
        self.assert_private_failure(self.run_consumer(consumer, self.record, other_input), "unavailable", "input_unavailable")
        self.store.consume("C1", "tool_calls", 1, self.clock.now())
        before = self.store.checkpoint("C1")
        self.assert_private_failure(self.run_consumer(consumer), "unavailable", "input_unavailable")
        self.assertEqual(self.store.checkpoint("C1"), before)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])

    def test_prior_cost_and_named_usage_debt_independently_narrow_recipe(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        self.assertEqual(self.run_consumer(self.consumer((grant,))).status, "completed")
        self.record, self.input = self.prepare_again()
        next_grant = self.grant((self.input.envelope_hash,), campaign_id="synthetic-cost-usage-plan")
        self.store.register_campaign(next_grant)
        base = self.consumer((next_grant,))
        for cap in (
                RoleAdmissionLimits("planning", 2, (("input_tokens", 200.0), ("output_tokens", 64.0)), 1.5),
                RoleAdmissionLimits("planning", 2, (("input_tokens", 150.0), ("output_tokens", 64.0)), 2.0),
                RoleAdmissionLimits("planning", 2, (("input_tokens", 200.0), ("output_tokens", 48.0)), 2.0)):
            with self.subTest(cap=cap):
                consumer = ProcessingOrchestrator(self.store, self.clock, self.catalog,
                    parent_gateway=self.gateway, recipe=replace(base.recipe, allowances=(cap,)),
                    invocation_id_factory=lambda: self.ids.append("forbidden") or "forbidden")
                before = self.durable_state(next_grant)
                self.assert_private_failure(self.run_consumer(consumer), "unavailable", "permit_unavailable")
                self.assertEqual(self.durable_state(next_grant), before)
        self.assertEqual(self.ids, ["plan-1"])

    def test_original_role_remaining_cannot_be_upgraded_by_larger_recipe(self):
        for index in range(2):
            grant = self.grant((self.input.envelope_hash,), campaign_id="synthetic-original-role-" + str(index))
            self.store.register_campaign(grant)
            self.assertEqual(self.run_consumer(self.consumer((grant,))).status, "completed")
            self.record, self.input = self.prepare_again()
        grant = self.grant((self.input.envelope_hash,), campaign_id="synthetic-original-exhausted")
        self.store.register_campaign(grant)
        base = self.consumer((grant,))
        rich = replace(base.recipe, allowances=(RoleAdmissionLimits("planning", 4,
            (("input_tokens", 400.0), ("output_tokens", 128.0)), 4.0),))
        consumer = ProcessingOrchestrator(self.store, self.clock, self.catalog,
            parent_gateway=self.gateway, recipe=rich,
            invocation_id_factory=lambda: self.ids.append("forbidden") or "forbidden")
        before = self.durable_state(grant)
        self.assert_private_failure(self.run_consumer(consumer), "unavailable", "permit_unavailable")
        self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(self.ids, ["plan-1", "plan-2"])

    def test_original_global_remaining_is_checked_before_id(self):
        # Public consume is explicit host setup, never a model callback or budget reset.
        self.store.consume("C1", "tool_calls", 23, self.clock.now())
        self.record, self.input = self.prepare_again()
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        before = self.durable_state(grant)
        self.assert_private_failure(self.run_consumer(self.consumer((grant,))), "unavailable", "permit_unavailable")
        self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])

    def test_original_monotonic_setup_expiry_prevents_id_or_debit(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        original = self.catalog.register_planning_evidence_snapshot
        def register(*args):
            result = original(*args)
            self.clock.seconds += 20.0
            return result
        before = self.durable_state(grant)
        with patch.object(self.catalog, "register_planning_evidence_snapshot", register):
            self.assert_private_failure(self.run_consumer(consumer), "denied", "scope_denied")
        self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])

    def test_final_publication_scope_loss_returns_neither_saved_receipt_nor_publication(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        original = self.catalog.publish_processing_output
        execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=20), self.clock)
        parent = self.gateway.execution_scope(execution)
        parent.__enter__()
        def publish(binding, identifier, auth):
            result = original(binding, identifier, auth)
            if identifier == "plan-1":
                parent.__exit__(None, None, None)
            return result
        try:
            with patch.object(self.catalog, "publish_processing_output", publish):
                outcome = consumer.plan_prepared(self.record, self.input, self.auth)
        finally:
            parent.__exit__(None, None, None)
        self.assert_private_failure(outcome, "denied", "scope_denied")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("completed", "completed"))
        self.assertEqual(self.store.checkpoint("C1").budget.planner_calls, 1)
        self.assert_no_effects()

    def test_stopped_current_checkpoint_denies_before_processing(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        self.store.set_stop("C1", "G1")
        before = self.durable_state(grant)
        outcome = self.run_consumer(consumer)
        self.assertNotEqual(outcome.status, "completed")
        self.assertIsNone(outcome.receipt)
        self.assertIsNone(outcome.publication)
        self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])

    def fresh_inventory_fixture(self, *, count):
        # Independent public fixture; original setup/store remains preserved and gets its own cleanup.
        root = self.root / "inventory"
        root.mkdir()
        self.fx = build_test_runtime(root, profile_name="flat-v1", request=self.original)
        self.store = self.fx.store
        self.addCleanup(self.store.close)
        budget = BudgetLedger(case_id="C1", deadline=DEADLINE,
            role_allowances={"extraction": RoleAllowance(max_invocations=count, max_cost=float(count),
                usage_allowances={"tokens": 2.0 * count}),
                "planning": RoleAllowance(max_invocations=2, max_cost=2.0,
                    usage_allowances={"input_tokens": 200.0, "output_tokens": 64.0})})
        self.store.admit(self.binding, self.original, make_checkpoint(binding=self.binding,
            phase="window_gate", next_gate="reschedule", budget=budget))
        self.gateway = ActionGateway(self.fx.profile, self.fx.world.bundle(),
            self.store, self.clock, auth=self.auth)
        def original_lookup(binding):
            if self.store.find_request(binding.case_id, binding.request_id, binding.request_revision,
                    binding.consent_revision, binding.fingerprint) != binding:
                raise ValueError("Exact durable original required")
            return self.store.original_request(binding.case_id, binding.generation)
        def scope(binding, original, auth, purpose):
            if (binding, original, auth) != (self.binding, self.original, self.auth):
                return None
            return SavedOriginalScope(canonical(binding.model_dump(mode="json")),
                fingerprint(original.model_dump(mode="json")), "saved-scope", self.scope_bytes,
                "synthetic-local-policy", "synthetic_host_registration", "synthetic-proof", DEADLINE)
        self.catalog = EvidenceCatalog(root / "catalog", self.clock, allowed_input_roots=[self.root],
            access_resolver=lambda auth, record, scope, purpose: auth == self.auth and record.case_id == "C1"
                and scope.get("scope_id") == "saved-scope" and scope.get("allowed_actors") == ("U1",),
            processing_bindings=ProcessingCatalogBindings(original_lookup,
                lambda b: self.store.checkpoint(b.case_id), self.store.invocation, scope,
                profile_lookup=lambda b, o: self.fx.profile))

    def test_more_than_sixteen_real_eligible_publications_denies_instead_of_subset(self):
        self.fresh_inventory_fixture(count=17)
        identifiers = tuple("inventory-" + str(i) for i in range(17))
        for identifier in identifiers:
            self.add_extraction(identifier)
        self.record, self.input = self.prepare_again(identifiers[:16])
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        before = self.durable_state(grant)
        self.assert_private_failure(self.run_consumer(self.consumer((grant,))), "unavailable", "input_unavailable")
        self.assertEqual(self.durable_state(grant), before)
        self.assertEqual(len(self.store.processing_attempts(self.binding)), 17)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])

    def test_all_empty_saved_extraction_has_no_usable_public_v2_input(self):
        self.fresh_inventory_fixture(count=1)
        self.add_extraction("all-empty", empty=True)
        before = self.store.processing_attempts(self.binding)
        with self.assertRaises(ProcessingPublicationError) as failure:
            self.prepare_again(("all-empty",))
        self.assertEqual(failure.exception.code, "input_unavailable")
        self.assertEqual(self.store.processing_attempts(self.binding), before)
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].invocations, 1)
        self.assertEqual(self.ids, [])
        self.assertEqual(self.requests, [])

    def test_nonusable_unknown_no_receipt_and_replay_history_remains_debited_and_unsubstitutable(self):
        # Explicit host recovery fixtures use the public reservation/record APIs.
        self.fresh_inventory_fixture(count=4)
        self.add_extraction("eligible")
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        for identifier, status, mode in (("unknown", "outcome_unknown", "synthetic"),
                ("no-receipt", None, "synthetic"), ("replay-only", "completed", "replay")):
            grant = make_fixture_campaign(role="extraction", campaign_id="history-" + identifier,
                input_hashes=[record.original_hash], max_usage={"tokens": 2.0})
            self.store.register_campaign(grant)
            identity = ProcessorIdentity(case_id="C1", generation="G1", role="extraction",
                campaign_id=grant.campaign_id, permit_hash=grant.permit_hash,
                input_hashes=grant.input_hashes, provider=grant.provider, model=grant.model,
                endpoint=grant.endpoint, prompt_hash=hashlib.sha256(PROMPT.encode()).hexdigest(),
                version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
            self.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id=identifier,
                requested_usage={"tokens": 2.0}, worst_case_cost=1.0), self.clock.now())
            if status is not None:
                output = None if status != "completed" else AssertionsOutput(kind="assertions", assertions=[])
                self.store.record_processing(identifier, ProcessingReceipt(invocation_id=identifier,
                    role="extraction", provider=identity.provider, requested_model=identity.model,
                    prompt_hash=identity.prompt_hash, version="v1", input_hashes=identity.input_hashes,
                    mode=mode, status=status, latency_seconds=0.0, usage={}, output=output,
                    output_hashes=[] if output is None else [output_digest(output)], processed_at=self.clock.now()))
            with self.assertRaises(ProcessingPublicationError):
                self.prepare_again(("eligible", identifier))
        self.record, self.input = self.prepare_again(("eligible",))
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        before = self.store.checkpoint("C1").budget.role_allowances["extraction"]
        outcome = self.run_consumer(self.consumer((grant,)))
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(before.invocations, 4)
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"], before)
        self.assertEqual([(a.invocation_id, a.status, None if r is None else r.mode)
            for a, r in self.store.processing_attempts(self.binding)],
            [("eligible", "completed", "synthetic"), ("unknown", "outcome_unknown", "synthetic"),
                ("no-receipt", "consumed", None), ("replay-only", "completed", "replay"),
                ("plan-1", "completed", "synthetic")])

    def test_stop_during_callback_keeps_completed_processing_but_returns_no_suggestion(self):
        # Break caught: a newly stopped original case still returns usable output after callback.
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.transport
        def transport(request):
            response = original(request)
            self.store.set_stop("C1", "G1")
            return response
        processor.transport = transport
        self.assert_private_failure(self.run_consumer(consumer), "denied", "scope_denied")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("completed", "completed"))
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)
        self.assertEqual(tuple((self.root / "catalog" / "receipts").glob("private-proposal-*.json")), ())
        self.assert_no_effects()

    def test_final_current_scope_read_time_cannot_outlive_original_parent(self):
        # Break caught: checking Timing before final current-state I/O permits a late return.
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        published = []
        original_publish = self.catalog.publish_processing_output
        original_checkpoint = self.store.checkpoint
        def publish(binding, identifier, auth):
            result = original_publish(binding, identifier, auth)
            if identifier == "plan-1":
                published.append(identifier)
            return result
        def checkpoint(case_id):
            result = original_checkpoint(case_id)
            if published:
                self.clock.seconds += 20.0
            return result
        with patch.object(self.catalog, "publish_processing_output", publish), \
                patch.object(self.store, "checkpoint", checkpoint):
            outcome = self.run_consumer(consumer)
        self.assert_private_failure(outcome, "denied", "scope_denied")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("completed", "completed"))
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def test_parent_exit_during_transport_retains_unknown_and_omits_private_output(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original = processor.transport
        execution = ExecutionContext.capture(self.clock.now() + timedelta(seconds=20), self.clock)
        parent = self.gateway.execution_scope(execution)
        parent.__enter__()
        def transport(request):
            response = original(request)
            parent.__exit__(None, None, None)
            return response
        processor.transport = transport
        try:
            outcome = consumer.plan_prepared(self.record, self.input, self.auth)
        finally:
            parent.__exit__(None, None, None)
        self.assert_private_failure(outcome, "denied", "processing_interrupted")
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("outcome_unknown", "outcome_unknown"))
        self.assertIsNone(saved.output)
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)

    def test_acl_revoked_by_actual_publication_read_withholds_completed_receipt(self):
        grant = self.grant((self.input.envelope_hash,))
        self.store.register_campaign(grant)
        consumer = self.consumer((grant,))
        processor = consumer.recipe.planning_registrations[0].processor
        original_transport = processor.transport
        original_access = self.catalog.access_resolver
        after_callback, publication_reads = [], []
        def access(auth, record, scope, purpose):
            if after_callback and record.source == "saved-planning-evidence-v2":
                publication_reads.append(record.artifact_id)
                if len(publication_reads) >= 3:
                    return False
            return original_access(auth, record, scope, purpose)
        def transport(request):
            response = original_transport(request)
            after_callback.append(True)
            return response
        self.catalog.access_resolver = access
        processor.transport = transport
        self.assert_private_failure(self.run_consumer(consumer), "denied", "scope_denied")
        self.assertGreaterEqual(len(publication_reads), 3)
        attempt, saved = self.store.invocation("plan-1")
        self.assertEqual((attempt.status, saved.status), ("completed", "completed"))
        self.assertEqual(self.store.campaign_usage(grant.permit_hash)["invocations"], 1)
        self.assert_no_effects()
