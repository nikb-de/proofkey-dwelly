"""Prepared saved V2 suggestions in one original host scope; never effect authority."""
from dataclasses import dataclass
import math
from threading import Lock, get_ident
from typing import Literal
from pydantic import TypeAdapter

from proofkey.contracts import (ProcessingReceipt, ProcessorIdentity, RequestBinding,
    CampaignPermit, Hash, Revision, Identifier, ArtifactRecord, AuthContext)
from proofkey.evidence.catalog import EvidenceCatalog
from proofkey.evidence.processing_contracts import (
    PlanningEvidenceInputV2, ProcessingPublication, ProcessingPublicationError, model_bytes)
from proofkey.planner import BoundedPlanner
from proofkey.processing import RoleAdmissionLimits, freeze_processing_allowances
from proofkey.providers.invocations import InvocationService
from proofkey.providers.protocols import EvidencePlanner
from proofkey.identity import fingerprint
from proofkey.gateway import ActionGateway


def _tuple(value, cap, *, nonempty=False):
    if type(value) is not tuple or len(value) > cap or (nonempty and not value):
        raise ValueError("Bounded exact immutable tuple required")


def _float(value, *, positive=False):
    if type(value) is not float or not math.isfinite(value) or (value <= 0 if positive else value < 0):
        raise ValueError("Exact finite float ceiling required")


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningRegistration:
    binding_bytes: bytes
    campaign_bytes: bytes
    processor: EvidencePlanner
    prompt_hash: str
    version: str
    profile_version: str
    process_version: str
    usage_ceiling: tuple[tuple[str, float], ...]
    worst_case_cost: float
    allowed_steps: tuple[tuple[str, str, tuple[str, ...]], ...]

    def __post_init__(self):
        for name, cap in (("binding_bytes", 65536), ("campaign_bytes", 131072)):
            value = getattr(self, name)
            if type(value) is not bytes or not 0 < len(value) <= cap:
                raise ValueError("Bounded exact canonical registration bytes required")
        model_bytes(RequestBinding, self.binding_bytes)
        campaign = model_bytes(CampaignPermit, self.campaign_bytes)
        wire = campaign.model_dump(mode="json")
        if (campaign.permit_hash != fingerprint({k: v for k, v in wire.items() if k != "permit_hash"})
                or campaign.role != "planning" or campaign.mode != "simulated"
                or len(campaign.input_hashes) != 1):
            raise ValueError("Exact simulated planning permit required")
        for name, contract in (("prompt_hash", Hash), ("version", Revision),
                ("profile_version", Revision), ("process_version", Revision)):
            TypeAdapter(contract).validate_python(getattr(self, name), strict=True)
        if not callable(getattr(self.processor, "propose_with_evidence", None)):
            raise ValueError("Explicit evidence planner required")
        _tuple(self.usage_ceiling, 8, nonempty=True)
        names = set()
        for pair in self.usage_ceiling:
            _tuple(pair, 2)
            if len(pair) != 2:
                raise ValueError("Exact usage pair required")
            name, amount = pair
            if type(name) is not str or not name.strip() or name in names:
                raise ValueError("Distinct nonempty usage unit required")
            _float(amount, positive=True)
            if name not in campaign.max_usage or amount > campaign.max_usage[name]:
                raise ValueError("Usage exceeds original campaign")
            names.add(name)
        _float(self.worst_case_cost)
        if self.worst_case_cost > campaign.max_cost:
            raise ValueError("Cost exceeds original campaign")
        _tuple(self.allowed_steps, 8)
        routes = set()
        for step in self.allowed_steps:
            _tuple(step, 3)
            if len(step) != 3:
                raise ValueError("Exact operation/stage/keys required")
            operation, stage, keys = step
            TypeAdapter(Identifier).validate_python(operation, strict=True)
            TypeAdapter(Identifier).validate_python(stage, strict=True)
            _tuple(keys, 8)
            for key in keys:
                TypeAdapter(Identifier).validate_python(key, strict=True)
            if len(set(keys)) != len(keys) or (operation, stage) in routes:
                raise ValueError("Duplicate route or argument alias")
            routes.add((operation, stage))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingRecipe:
    allowances: tuple[RoleAdmissionLimits, ...]
    planning_registrations: tuple[PlanningRegistration, ...]

    def __post_init__(self):
        if type(self.allowances) is not tuple:
            raise ValueError("Exact immutable role configuration required")
        allowances = freeze_processing_allowances(self.allowances)
        object.__setattr__(self, "allowances", allowances)
        planning = next((a for a in allowances if a.role == "planning"), None)
        if planning is None or not planning.max_invocations:
            raise ValueError("Enabled planning recipe required")
        _tuple(self.planning_registrations, 4)
        selections = set()
        for registration in self.planning_registrations:
            if type(registration) is not PlanningRegistration:
                raise ValueError("Exact planning registration required")
            registration.__post_init__()
            campaign = model_bytes(CampaignPermit, registration.campaign_bytes)
            selection = (registration.binding_bytes, tuple(campaign.input_hashes))
            if selection in selections:
                raise ValueError("Duplicate or ambiguous prepared planning selection")
            selections.add(selection)
            limits = dict(planning.usage_allowances)
            if (registration.worst_case_cost > planning.max_cost
                    or any(name not in limits or amount > limits[name]
                           for name, amount in registration.usage_ceiling)):
                raise ValueError("Request exceeds planning recipe ceilings")


@dataclass(frozen=True, slots=True)
class ProcessingStepOutcome:
    status: Literal["completed", "unavailable", "denied"]
    receipt: ProcessingReceipt | None = None
    publication: ProcessingPublication | None = None
    entry_local_reason: str | None = None

    def __post_init__(self):
        reasons = {"permit_unavailable", "input_unavailable", "scope_denied",
            "processing_interrupted", "output_rejected", "publication_unavailable"}
        if self.status == "completed":
            if (type(self.receipt) is not ProcessingReceipt or self.receipt.status != "completed"
                    or self.receipt.role != "planning" or self.receipt.mode != "synthetic"
                    or type(self.publication) is not ProcessingPublication
                    or self.publication.invocation_id != self.receipt.invocation_id
                    or self.publication.receipt_hash != fingerprint(self.receipt.model_dump(mode="json"))
                    or tuple(self.receipt.output_hashes) != self.publication.output_hashes
                    or self.entry_local_reason is not None):
                raise ValueError("Completion requires exact private saved receipt/publication joins")
        elif (self.status not in {"denied", "unavailable"} or self.entry_local_reason not in reasons
                or self.receipt is not None or self.publication is not None):
            raise ValueError("Finite noncomplete outcome must omit private output")


class ProcessingOrchestrator:
    def __init__(self, store, clock, catalog, *, parent_gateway, recipe,
                 invocation_id_factory=None):
        if type(recipe) is not ProcessingRecipe:
            raise ValueError("Exact immutable recipe required")
        recipe.__post_init__()
        if (type(parent_gateway) is not ActionGateway or parent_gateway.store is not store
                or parent_gateway.clock is not clock or type(catalog) is not EvidenceCatalog
                or catalog.clock is not clock
                or (invocation_id_factory is not None and not callable(invocation_id_factory))):
            raise ValueError("Exact original processing associations and ID reference required")
        self._store, self._clock, self._catalog = store, clock, catalog
        self._parent_gateway, self._recipe = parent_gateway, recipe
        self._invocation_id_factory = invocation_id_factory
        self._creator_thread, self._lock = get_ident(), Lock()

    @property
    def store(self):
        return self._store

    @property
    def clock(self):
        return self._clock

    @property
    def catalog(self):
        return self._catalog

    @property
    def parent_gateway(self):
        return self._parent_gateway

    @property
    def recipe(self):
        return self._recipe

    def plan_prepared(self, record, input, auth) -> ProcessingStepOutcome:
        if get_ident() != self._creator_thread or not self._lock.acquire(blocking=False):
            return ProcessingStepOutcome("denied", entry_local_reason="scope_denied")
        try:
            return self._plan_owned(record, input, auth)
        finally:
            self._lock.release()

    def _parent_timing(self, expected=None, deadline=None):
        if (self.parent_gateway.store is not self.store or self.parent_gateway.clock is not self.clock
                or self.catalog.clock is not self.clock):
            raise ValueError("Original processing association changed")
        timing = self.parent_gateway.processing_parent_timing(store=self.store, clock=self.clock)
        if expected is not None and timing is not expected:
            raise ValueError("Original processing timing changed")
        if deadline is not None and timing.remaining_seconds(deadline) <= 0:
            raise ValueError("Original processing deadline expired")
        return timing

    def _permit_remaining(self, registration, campaign, checkpoint, consumed):
        budget = checkpoint.budget
        original = budget.role_allowances.get("planning")
        configured = next(a for a in self.recipe.allowances if a.role == "planning")
        deadline = min(checkpoint.deadline, budget.deadline)
        if (original is None or campaign.expires_at < deadline or self.clock.now() >= campaign.expires_at
                or budget.active_seconds >= budget.max_active_seconds
                or budget.tool_calls + 1 > budget.max_tool_calls
                or budget.planner_calls + 1 > budget.max_planner_calls
                or consumed["invocations"] + 1 > campaign.max_invocations
                or consumed["cost"] + registration.worst_case_cost > campaign.max_cost):
            return False
        recipe_usage = dict(configured.usage_allowances)
        for limits, maxima in ((original, original.usage_allowances), (configured, recipe_usage)):
            if (original.invocations + 1 > limits.max_invocations
                    or original.cost + registration.worst_case_cost > limits.max_cost
                    or any(name not in maxima or original.usage.get(name, 0) + amount > maxima[name]
                           for name, amount in registration.usage_ceiling)):
                return False
        return all(name in campaign.max_usage
            and consumed["usage"].get(name, 0) + amount <= campaign.max_usage[name]
            for name, amount in registration.usage_ceiling)

    def _current_scope(self, binding):
        current = self.store.checkpoint(binding.case_id)
        if (current.binding != binding or current.stop.requested
                or current.ownership_state in {"pending", "transfer_pending", "stopped"}):
            raise ValueError("Current original scope no longer permits processing")
        return current

    def _plan_owned(self, record, input, auth):
        stage = "scope"
        try:
            timing = self._parent_timing()
            if type(auth) is not AuthContext:
                return ProcessingStepOutcome("denied", entry_local_reason="scope_denied")
            stage = "input"
            if type(record) is not ArtifactRecord or type(input) is not PlanningEvidenceInputV2:
                return ProcessingStepOutcome("unavailable", entry_local_reason="input_unavailable")
            input = PlanningEvidenceInputV2(input.checkpoint_bytes, input.observation_bytes,
                input.extraction_publication_bytes, input.envelope_bytes, input.envelope_hash)
            checkpoint = input.checkpoint()
            binding = checkpoint.binding
            publications = input.extraction_publications()
            rebuilt = self.catalog.register_planning_evidence_snapshot(checkpoint, input.observations(),
                tuple(p.invocation_id for p in publications), auth)
            actual = PlanningEvidenceInputV2.from_bytes(self.catalog.read_original(
                rebuilt.artifact_id, auth, purpose="provider_processing"))
            if rebuilt != record or actual != input or self.store.checkpoint(binding.case_id) != checkpoint:
                return ProcessingStepOutcome("unavailable", entry_local_reason="input_unavailable")
            eligible_ids = tuple(attempt.invocation_id for attempt, receipt in self.store.processing_attempts(binding)
                if attempt.identity.role == "extraction" and attempt.status == "completed"
                and type(receipt) is ProcessingReceipt and receipt.status == "completed" and receipt.mode == "synthetic")
            if len(eligible_ids) > 16 or eligible_ids != tuple(p.invocation_id for p in publications):
                return ProcessingStepOutcome("unavailable", entry_local_reason="input_unavailable")
            stage = "scope"
            self._parent_timing(timing, min(checkpoint.deadline, checkpoint.budget.deadline))
            if checkpoint.stop.requested or checkpoint.ownership_state in {"pending", "transfer_pending", "stopped"}:
                return ProcessingStepOutcome("denied", entry_local_reason="scope_denied")
            stage = "permit"
            selected = []
            for registration in self.recipe.planning_registrations:
                original = model_bytes(RequestBinding, registration.binding_bytes)
                campaign = model_bytes(CampaignPermit, registration.campaign_bytes)
                if (original == binding and campaign.role == "planning"
                        and campaign.input_hashes == [input.envelope_hash]
                        and (registration.profile_version, registration.process_version)
                        == (checkpoint.profile_version, checkpoint.process_version)):
                    selected.append((registration, campaign))
            if len(selected) != 1:
                return ProcessingStepOutcome("unavailable", entry_local_reason="permit_unavailable")
            registration, campaign = selected[0]
            consumed = self.store.campaign_usage(campaign.permit_hash)
            if not self._permit_remaining(registration, campaign, checkpoint, consumed):
                return ProcessingStepOutcome("unavailable", entry_local_reason="permit_unavailable")
            stage = "scope"
            self._parent_timing(timing, min(checkpoint.deadline, checkpoint.budget.deadline))
            identity = ProcessorIdentity(case_id=binding.case_id, generation=binding.generation,
                role="planning", campaign_id=campaign.campaign_id, permit_hash=campaign.permit_hash,
                input_hashes=[input.envelope_hash], provider=campaign.provider, model=campaign.model,
                endpoint=campaign.endpoint, prompt_hash=registration.prompt_hash,
                version=registration.version, profile_version=registration.profile_version,
                process_version=registration.process_version,
                deadline=min(checkpoint.deadline, checkpoint.budget.deadline))
            service = InvocationService(binding.case_id, self.store, self.clock, campaign, identity,
                worst_case_cost=registration.worst_case_cost,
                invocation_id_factory=self._invocation_id_factory, parent_gateway=self.parent_gateway)
            allowed_steps = {}
            for operation, step, keys in registration.allowed_steps:
                allowed_steps.setdefault(operation, {})[step] = keys
            planner = BoundedPlanner(registration.processor, service,
                allowed_steps=allowed_steps, usage_ceiling=dict(registration.usage_ceiling))
            def invoke():
                self.catalog.seal_invocation_inputs(binding, service.current_request.invocation_id,
                    (record.artifact_id,), auth)
                context = service.processing_context(self.catalog, auth, input_records=(record,))
                return registration.processor.propose_with_evidence(input, context)
            stage = "invoke"
            receipt = service.call_in_parent("planning", identity.input_hashes,
                dict(registration.usage_ceiling), invoke)
            stage = "scope"
            self._current_scope(binding)
            self._parent_timing(timing, identity.deadline)
            stage = "output"
            planner.validate_evidence_receipt(receipt, input)
            stage = "publication"
            publication = self.catalog.publish_processing_output(binding, receipt.invocation_id, auth)
            stage = "scope"
            self._current_scope(binding)
            self._parent_timing(timing, identity.deadline)
            return ProcessingStepOutcome("completed", receipt, publication)
        except ProcessingPublicationError as error:
            if error.code == "scope_denied":
                return ProcessingStepOutcome("denied", entry_local_reason="scope_denied")
            reason = "publication_unavailable" if stage == "publication" else "input_unavailable"
            return ProcessingStepOutcome("unavailable", entry_local_reason=reason)
        except Exception:
            status, reason = {
                "scope": ("denied", "scope_denied"),
                "input": ("unavailable", "input_unavailable"),
                "permit": ("unavailable", "permit_unavailable"),
                "invoke": ("denied", "processing_interrupted"),
                "output": ("denied", "output_rejected"),
                "publication": ("unavailable", "publication_unavailable"),
            }[stage]
            return ProcessingStepOutcome(status, entry_local_reason=reason)
