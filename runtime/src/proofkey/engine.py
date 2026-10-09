"""Finite offline workflow orchestration over the common action gateway.

Local graph predicates never authorize transport: each physical entry rereads
designated material authority through the gateway. Unsupported waits/media stay
visible until their scoped services are installed; no fabricated reply is used.
"""
from datetime import datetime, timedelta
from contextlib import contextmanager
from threading import get_ident

from .contracts import (ActionProposal, AuthContext, CanonicalRequest, CaseResult,
                        EnvironmentProfile, PhaseCheckpoint, ReadTarget, SavedResult, ScopedReply, VerificationResult)
from .gateway import ActionGateway
from .identity import request_fingerprint
from .journal import JournalFailure
from .policy import GateDenied, qualified_observations
from .process import ProcessController
from .replay import ReplayService
from .waits import WaitService
from .packet_contracts import packet_enabled
from .budget import BudgetExceeded


_BUSINESS = {"reschedule_window": "reschedule", "reschedule_exact": "reschedule",
             "goods_refusal": "register_goods_refusal", "service_refusal": "register_service_refusal"}
_LOCAL = {"intake": "extract_input", "extraction": "check_completeness",
          "completeness": "authenticate", "auth_gate": "read_authority",
          "window_gate": "reschedule", "exact_gate": "reschedule",
          "refusal_complete": "check_return", "return_gate": "create_return"}
_STAGES = {"reschedule": "commit", "register_goods_refusal": "commit",
           "register_service_refusal": "commit", "create_return": "initiate", "enqueue_handoff": "enqueue"}


def _interval(start, end):
    if not isinstance(start, str) or not isinstance(end, str):
        raise GateDenied("scope_denied")
    start, end = datetime.fromisoformat(start), datetime.fromisoformat(end)
    if start.utcoffset() is None or end.utcoffset() is None or start >= end:
        raise GateDenied("scope_denied")
    return start, end


class WorkflowEngine:
    def __init__(self, profile, bundle, store, clock, planner=None, evidence=None, *, gateway=None):
        self.profile = EnvironmentProfile.model_validate(profile.model_dump())
        self.bundle, self.store, self.clock = bundle, store, clock
        self.planner, self.evidence = planner, evidence
        self.process = ProcessController(self.profile)
        self._gateway = gateway if gateway is not None else ActionGateway(self.profile, bundle, store, clock)
        self.waits = WaitService(self.profile, bundle, store, clock, gateway=self._gateway)
        self._owner_thread = get_ident()
        self._entry_active = False

    @property
    def gateway(self):
        """The same authenticated, budgeted gateway used by every workflow."""
        return self._gateway

    @staticmethod
    def _public_denial(case_id, reason="denied"):
        return CaseResult(status="denied", correlation_id=case_id, reason=reason)

    @contextmanager
    def _entry_scope(self):
        """Creator-thread serial entry, reusable by later reply/stop services.

        This guard precedes auth/controller mutation and SQLite access. It does
        not disable the journal's independent creator-thread restrictions.
        """
        if get_ident() != self._owner_thread or self._entry_active:
            raise GateDenied("scope_denied")
        self._entry_active = True
        try:
            yield
        finally:
            self._entry_active = False

    def authenticate_and_bind(self, request, auth, deadline=None):
        if (get_ident() != self._owner_thread or not self._entry_active
                or not isinstance(request, CanonicalRequest) or not isinstance(auth, AuthContext)):
            raise GateDenied("scope_denied")
        request = CanonicalRequest.model_validate(request.model_dump())
        self._gateway.auth = auth
        # Trusted offline host horizon, matching the finite provisional case cap;
        # this is neither customer policy nor a native consent expiry.
        deadline = deadline or self.clock.now() + timedelta(seconds=120)
        binding = self._gateway.bind_request(request, deadline, initialize_process=True)
        checkpoint = self.store.checkpoint(binding.case_id)
        spec = self.profile.processes.get(request.kind)
        if (checkpoint.binding != binding or spec is None or checkpoint.phase not in spec.phases
                or checkpoint.profile_version != self.profile.version or checkpoint.process_version != spec.version
                or checkpoint.policy_version != "v1" or checkpoint.deadline > deadline):
            raise GateDenied("scope_denied")
        self.process = ProcessController(self.profile, request.kind)
        return checkpoint

    def run(self, request, auth):
        case_id = request.case_id if isinstance(request, CanonicalRequest) else "invalid-request"
        try:
            with self._entry_scope():
                if not isinstance(request, CanonicalRequest) or not isinstance(auth, AuthContext):
                    raise GateDenied("scope_denied")
                request = CanonicalRequest.model_validate(request.model_dump())
                auth = AuthContext.model_validate(auth.model_dump())
                replay = ReplayService(self.profile, self.bundle, self.store, self.clock).lookup(request, auth)
                if replay is not None:
                    return replay
                # None permits only the independent fresh gate below, preserving
                # exact unfinished input/phase and its shared accounting.
                checkpoint = self.authenticate_and_bind(request, auth)
                original = self.store.original_request(case_id, checkpoint.binding.generation)
                if original != request:
                    raise GateDenied("scope_denied")
                # Completed duplicates returned above; unfinished recovery remains
                # explicit and must never refresh a saved historical unknown.
                if checkpoint.stop.requested or self.process.is_terminal(checkpoint.phase):
                    return self._public_denial(case_id, "unavailable")
                return self._drive(checkpoint, original, auth)
        except (GateDenied, JournalFailure, BudgetExceeded, ValueError, TypeError):
            return self._public_denial(case_id)

    def recover(self, case_id, auth):
        try:
            with self._entry_scope():
                if not isinstance(auth, AuthContext):
                    raise GateDenied("scope_denied")
                auth = AuthContext.model_validate(auth.model_dump())
                saved = self.store.checkpoint(case_id)
                if saved.stop.requested or self.store.generation_stop(saved.binding).requested:
                    self._gateway.auth = auth
                    checkpoint = self._gateway.authenticate_control(saved.binding, auth, purpose="recorded_state")
                    for record in self.store.intents(case_id):
                        if record.intent.binding == checkpoint.binding and record.state != "prepared":
                            result = self._gateway.reconcile_read_only(record.intent.action_id)
                            if result.reason == "scope_denied" and not result.action_id:
                                raise GateDenied("scope_denied")
                    return self.build_case_result(self.store.checkpoint(case_id), save=False)
                original = self.store.original_request(case_id, saved.binding.generation)
                if original is None:
                    raise GateDenied("scope_denied")
                checkpoint = self.authenticate_and_bind(original, auth, saved.deadline)
                if (checkpoint.phase, checkpoint.next_gate, checkpoint.binding) != (saved.phase, saved.next_gate, saved.binding):
                    raise GateDenied("scope_denied")
                if checkpoint.stop.requested or self.process.is_terminal(checkpoint.phase):
                    return self._public_denial(case_id, "unavailable")
                return self._drive(checkpoint, original, auth, recovering=True)
        except (GateDenied, JournalFailure, BudgetExceeded, ValueError, TypeError):
            return self._public_denial(case_id)

    def reply(self, reply, auth):
        case_id = reply.binding.case_id if isinstance(reply, ScopedReply) else "invalid-reply"
        try:
            with self._entry_scope():
                if not isinstance(reply, ScopedReply) or not isinstance(auth, AuthContext):
                    raise GateDenied("scope_denied")
                auth = AuthContext.model_validate(auth.model_dump())
                self._gateway.auth = auth
                checkpoint = self.waits.accept(reply, auth)
                original = self.store.original_request(case_id, checkpoint.binding.generation)
                self.process = ProcessController(self.profile, original.kind)
                if checkpoint.phase == "operator_facts" and auth.caller_id != original.principal_id:
                    # Facts-only recipient authentication is not customer
                    # authority. Reenter completeness, then await a separate
                    # customer-authenticated entry before any business batch.
                    checkpoint = self._transition(checkpoint, original, "reenter_facts")
                    return self.build_case_result(self._save(checkpoint, processing_status="unavailable"))
                return self._drive(checkpoint, original, auth)
        except (GateDenied, JournalFailure, BudgetExceeded, ValueError, TypeError):
            return self._public_denial(case_id)

    def stop(self, case_id, generation, auth):
        try:
            with self._entry_scope():
                if not isinstance(auth, AuthContext):
                    raise GateDenied("scope_denied")
                auth = AuthContext.model_validate(auth.model_dump())
                current = self.store.checkpoint(case_id)
                if current.binding.generation != generation:
                    raise GateDenied("scope_denied")
                self._gateway.auth = auth
                authenticated = self._gateway.authenticate_control(current.binding, auth, purpose="stop")
                checkpoint = self.store.stop_waits_atomic(current.binding, authenticated)
                original = self.store.original_request(case_id, generation)
                self.process = ProcessController(self.profile, original.kind)
                # The durable fence precedes cosmetic graph advancement.
                target = self.process.next_phase(checkpoint.phase, "request_stop", {})
                if target is not None:
                    checkpoint = self._save(checkpoint, phase=target, next_gate="record_stop")
                if checkpoint.phase == "stop":
                    target = self.process.next_phase("stop", "record_stop", {})
                    if target is not None:
                        checkpoint = self._save(checkpoint, phase=target, next_gate=target)
                return self.build_case_result(checkpoint, save=False)
        except (GateDenied, JournalFailure, BudgetExceeded, ValueError, TypeError):
            return self._public_denial(case_id)

    def _save(self, checkpoint, **changes):
        updated = PhaseCheckpoint.model_validate({**checkpoint.model_dump(), **changes})
        self.store.save_checkpoint(updated)
        return self.store.checkpoint(checkpoint.binding.case_id)

    def _records(self, checkpoint):
        return {r.intent.operation: r for r in self.store.intents(checkpoint.binding.case_id)
                if r.intent.binding == checkpoint.binding}

    @staticmethod
    def _selected(checkpoint, operation):
        # A phase marker leaves selection to this finite implementation; an
        # explicitly selected continuation may never be silently replaced.
        if checkpoint.next_gate not in {checkpoint.phase, operation}:
            raise GateDenied("scope_denied")

    def _graph_facts(self, checkpoint, request):
        indexed = qualified_observations(self.profile, request.object_id, checkpoint.observations)
        facts = {key: item.value for key, item in indexed.items()}
        source_scope = (facts.get("customer.request_fingerprint") == checkpoint.binding.fingerprint
                        and facts.get("customer.consent_mode") == request.consent_mode
                        and facts.get("customer.consent") == "granted")
        if source_scope and request.kind == "reschedule_window":
            facts["customer.consent"] = "window"
        if source_scope and request.kind == "reschedule_exact" and set(request.arguments) <= {"slot", "inventory"}:
            if isinstance(request.arguments.get("slot"), str) and request.arguments["slot"]:
                facts.update({"customer.consent": "exact_slot", "customer.confirmation": "verified"})
        for operation, record in self._records(checkpoint).items():
            if record.state == "verified" and record.verification is not None and record.verification.status == "verified":
                fact = {"reschedule": "delivery.reschedule", "register_goods_refusal": "goods.refusal",
                        "register_service_refusal": "service.refusal", "create_return": "returns.return"}.get(operation)
                if fact:
                    facts[fact] = "verified"
        return facts

    def _transition(self, checkpoint, request, operation, *, facts=None):
        wait = next((w for w in self.profile.processes[request.kind].waits if w.phase == checkpoint.phase), None)
        if checkpoint.next_gate not in {checkpoint.phase, operation} | ({wait.next_gate} if wait else set()):
            raise GateDenied("scope_denied")
        target = self.process.next_phase(checkpoint.phase, operation,
                                        facts if facts is not None else self._graph_facts(checkpoint, request))
        if target is None:
            raise GateDenied("scope_denied")
        return self._save(checkpoint, phase=target, next_gate=target, processing_status="pending")

    def _pause(self, checkpoint, request, *, unknown=False):
        if (checkpoint.phase == "completeness" and not unknown and checkpoint.question_id is None
                and self._graph_facts(checkpoint, request).get("case.completeness") == "missing"):
            contract = next((w for w in self.profile.processes[request.kind].waits if w.phase == "wait_customer"), None)
            if contract is not None:
                try:
                    return self._communication_wait(checkpoint, request, contract.awaited_fields)
                except (GateDenied, JournalFailure, ValueError, TypeError):
                    checkpoint = self.store.checkpoint(request.case_id)
        if not unknown and checkpoint.question_id is None:
            spec = self.profile.processes[request.kind]
            physical = [w for w in spec.waits if w.recipient_role == "operator" and any(
                e.origin == checkpoint.phase and e.target == w.phase and e.operation == "enqueue_handoff"
                for e in spec.edges)]
            if len(physical) == 1 and packet_enabled(self.profile):
                try:
                    return self._communication_wait(checkpoint, request, physical[0].awaited_fields)
                except (GateDenied, JournalFailure, BudgetExceeded, ValueError, TypeError):
                    return self._save(self.store.checkpoint(request.case_id), processing_status="unavailable")
        if unknown:
            checkpoint = self._transition(checkpoint, request, "mark_unknown")
        elif not checkpoint.phase.startswith("wait"):
            target = self.process.next_phase(checkpoint.phase, "ask_operator", {})
            if target is not None:
                checkpoint = self._save(checkpoint, phase=target, next_gate=target)
        spec = self.profile.processes[request.kind]
        wait = next((w for w in spec.waits if w.phase == checkpoint.phase), None)
        return self._save(checkpoint, next_gate=wait.next_gate if wait else checkpoint.next_gate,
                          awaited_fields=wait.awaited_fields if wait else checkpoint.awaited_fields,
                          processing_status="unavailable")

    def _communication_wait(self, checkpoint, request, fields):
        wait = self.waits.create(checkpoint, fields)
        record = self.store.load_wait_record(wait.question_id)
        current = self.store.checkpoint(request.case_id)
        communication = next((r for r in self.store.intents(request.case_id)
                              if r.intent.action_id == record.communication_action_id), None)
        if communication is None or communication.state == "prepared":
            return self._save(current, processing_status="unavailable")
        return self._save(current, phase=record.wait_phase, next_gate=record.accept_edge.operation,
            question_id=wait.question_id, awaited_fields=wait.awaited_fields, processing_status="unavailable")

    def _build_proposal(self, operation):
        def build(request, observations):
            values = {key: item.value for key, item in qualified_observations(
                self.profile, request.object_id, observations).items()}
            if operation == "reschedule":
                if values.get("delivery.status") != "scheduled":
                    raise GateDenied("scope_denied")
                capacity, details = values.get("scheduling.capacity"), values.get("scheduling.slot_details")
                if not isinstance(capacity, list) or not isinstance(details, dict):
                    raise GateDenied("scope_denied")
                if request.kind == "reschedule_exact":
                    slot = request.arguments.get("slot")
                    if slot not in capacity:
                        raise GateDenied("scope_denied")
                else:
                    lower, upper = _interval(request.arguments.get("window_start"), request.arguments.get("window_end"))
                    candidates = []
                    for slot in capacity:
                        if not isinstance(slot, str) or not isinstance(details.get(slot), dict):
                            raise GateDenied("scope_denied")
                        start, end = _interval(details[slot].get("start"), details[slot].get("end"))
                        if lower <= start and end <= upper:
                            candidates.append((start, end, slot))
                    if not candidates:
                        raise GateDenied("scope_denied")
                    slot = min(candidates)[2]
                arguments, post = {"slot": slot}, {"slot": slot}
            elif operation in {"register_goods_refusal", "create_return"}:
                inventory = request.arguments.get("inventory")
                if (not isinstance(inventory, dict) or not inventory or inventory != values.get("goods.inventory")
                        or any(type(q) is not int or q <= 0 for q in inventory.values())
                        or type(values.get("goods.quantity")) is not int
                        or sum(inventory.values()) != values["goods.quantity"]):
                    raise GateDenied("scope_denied")
                arguments = {"inventory": inventory}
                post = {"inventory": inventory, "quantity": sum(inventory.values())}
                if operation == "create_return":
                    destination = values.get("returns.destination")
                    if not isinstance(destination, str) or not destination:
                        raise GateDenied("scope_denied")
                    arguments["destination"] = destination
                    post.update({"returns.status": "initiated", "destination": destination})
                else:
                    post["goods.refusal"] = "verified"
            elif operation == "register_service_refusal":
                if values.get("delivery.status") != "completed":
                    raise GateDenied("scope_denied")
                arguments, post = {"scope": "service"}, {"service.refusal": "verified"}
            else:
                # Packet identity is deterministic, while recipient/revision/hash
                # come only from the designated current operator authority.
                packet_id = "packet:" + request_fingerprint(request)
                arguments = {"packet_id": packet_id, "packet_revision": values.get("operator.packet_revision"),
                             "packet_hash": values.get("operator.packet_hash"), "recipient": values.get("operator.recipient")}
                post = {"operator.handoff_disposition": "pending", **{k: arguments[k] for k in
                        ("packet_id", "packet_revision", "packet_hash")}}
            return ActionProposal(operation=operation, stage=_STAGES[operation], arguments=arguments,
                                  evidence_refs=[]), post
        return build

    def _external(self, checkpoint, request, operation, *, reconcile=False):
        read_gate = "read_communication" if operation == "enqueue_handoff" else "read_effect"
        self._selected(checkpoint, read_gate if reconcile else operation)
        record = self._records(checkpoint).get(operation)
        if not reconcile and record is not None and record.state != "prepared":
            # An entered original is not another business entry. Its durable
            # receipt permits only the existing unique edge's destination,
            # whose declared original-read gate is then saved before entry.
            edges = [edge for edge in self.profile.processes[request.kind].edges
                     if edge.origin == checkpoint.phase and edge.operation == operation]
            if len(edges) != 1:
                raise GateDenied("scope_denied")
            destination = PhaseCheckpoint.model_validate({**checkpoint.model_dump(),
                "phase": edges[0].target, "next_gate": read_gate})
            facts = self._graph_facts(checkpoint, request)
            facts["journal.original_effect"] = ReadTarget(kind="original_effect", operation=operation,
                generation=record.intent.binding.generation, action_id=record.intent.action_id,
                provider_key=record.intent.provider_key, fingerprint=record.intent.argument_fingerprint)
            if self.process.next_phase(destination.phase, read_gate, facts) is None:
                raise GateDenied("scope_denied")
            checkpoint = self._save(destination, processing_status="pending")
            reconcile = True
        else:
            checkpoint = self._save(checkpoint, next_gate=read_gate if reconcile else operation)
        if reconcile:
            if record is None or record.state == "prepared":
                return self._pause(checkpoint, request)
            facts = self._graph_facts(checkpoint, request)
            facts["journal.original_effect"] = ReadTarget(kind="original_effect", operation=operation,
                generation=record.intent.binding.generation, action_id=record.intent.action_id,
                provider_key=record.intent.provider_key, fingerprint=record.intent.argument_fingerprint)
            edge_operation = "read_communication" if operation == "enqueue_handoff" else "read_effect"
            target = self.process.next_phase(checkpoint.phase, edge_operation, facts)
            if target is None:
                return self._pause(checkpoint, request)
            result = self._gateway.reconcile(record.intent.action_id)
        else:
            if operation == "enqueue_handoff" and packet_enabled(self.profile):
                result = self._gateway.enqueue_operator_packet(request.case_id, "review_facts")
            else:
                result = (self._gateway.execute(record.intent) if record is not None else
                          self._gateway.execute_proposal(request.case_id, operation, self._build_proposal(operation)))
            # Transport permission and the conceptual scope predicates are
            # checked inside gateway policy with the just-read designated set.
            target = next((e.target for e in self.profile.processes[request.kind].edges
                           if e.origin == checkpoint.phase and e.operation == operation), None)
        checkpoint = self.store.checkpoint(request.case_id)
        if result.reason == "scope_denied" and not result.action_id:
            entered = self._records(checkpoint).get(operation)
            if entered is not None and entered.state != "prepared":
                raise GateDenied("scope_denied")
            return self._pause(checkpoint, request)
        if target is None:
            return self._pause(checkpoint, request)
        return self._save(checkpoint, phase=target, next_gate=target, processing_status="pending")

    def run_one_approved_phase(self, checkpoint, request, auth, *, recovering=False):
        phase = checkpoint.phase
        if checkpoint.stop.requested:
            return checkpoint
        spec = self.profile.processes[request.kind]
        declared = {edge.operation for edge in spec.edges if edge.origin == phase}
        wait = next((w for w in spec.waits if w.phase == phase), None)
        if checkpoint.next_gate not in ({phase} | declared | ({wait.next_gate} if wait else set())):
            raise GateDenied("scope_denied")
        physical = [w for w in spec.waits if w.recipient_role == "operator" and any(
            e.origin == phase and e.target == w.phase and e.operation == "enqueue_handoff" for e in spec.edges)]
        if len(physical) == 1 and checkpoint.question_id is None:
            question_id = self.waits.question_id(checkpoint.binding, operation="enqueue_handoff")
            retained = self.store.wait(question_id) is not None or any(
                r.intent.binding == checkpoint.binding and r.intent.operation == "enqueue_handoff"
                for r in self.store.intents(request.case_id))
            # A crash can leave the full envelope at the business gate. Inspect
            # that original before repeating business assembly or fresh reads.
            if retained or checkpoint.next_gate == "enqueue_handoff":
                return self._communication_wait(checkpoint, request, physical[0].awaited_fields)
        if phase == "completeness" and checkpoint.next_gate == "send_clarification":
            contract = next((w for w in spec.waits if w.phase == "wait_customer"), None)
            if contract is None:
                return self._save(checkpoint, processing_status="unavailable")
            return self._communication_wait(checkpoint, request, contract.awaited_fields)
        if (phase.startswith("wait") and (phase != "wait_confirmation" or checkpoint.question_id is not None)) or phase == "expired":
            if checkpoint.question_id is None:
                self._selected(checkpoint, wait.next_gate if wait else phase)
            return self._save(checkpoint, processing_status="unavailable")
        if checkpoint.next_gate in {"read_effect", "read_communication"}:
            operation = ("enqueue_handoff" if checkpoint.next_gate == "read_communication" else
                         "create_return" if phase in {"return_dispatch", "verify_return", "outcome_unknown_return"}
                         else _BUSINESS[request.kind])
            return self._external(checkpoint, request, operation, reconcile=True)
        if phase == "extraction" and (request.evidence_ids or (request.narrative and request.narrative.strip())):
            self._selected(checkpoint, "check_completeness")
            return self._pause(checkpoint, request)
        if phase == "read_authority":
            operation = {"reschedule_window": "check_window", "reschedule_exact": "find_exact_slot"}.get(request.kind, "check_refusal")
        elif phase == "slot_selection":
            facts = self._graph_facts(checkpoint, request)
            if facts.get("customer.confirmation") != "verified":
                contract = next((w for w in spec.waits if w.phase == "wait_confirmation"), None)
                if contract is None:
                    return self._save(checkpoint, processing_status="unavailable")
                return self._communication_wait(checkpoint, request, contract.awaited_fields)
            operation = "ask_customer"
        elif phase == "operator_facts":
            operation = "reenter_facts"
        elif phase == "wait_confirmation":
            operation = "accept_confirmation"
        elif phase == "refusal_gate":
            operation = _BUSINESS[request.kind]
        elif phase == "refusal_complete":
            operation = "enqueue_handoff" if request.kind == "service_refusal" else "check_return"
        elif phase in {"dispatch", "return_dispatch", "verification", "verify_refusal", "verify_return"} or phase.startswith("outcome_unknown"):
            operation = "create_return" if phase in {"return_dispatch", "verify_return", "outcome_unknown_return"} else _BUSINESS[request.kind]
            record = self._records(checkpoint).get(operation)
            if record is None:
                self._selected(checkpoint, "ask_operator")
                return self._pause(checkpoint, request)
            if phase.startswith("outcome_unknown") or (recovering and record.state not in {"verified", "conflict", "rejected"}):
                self._selected(checkpoint, "read_effect")
                return self._external(checkpoint, request, operation, reconcile=True)
            if phase in {"dispatch", "return_dispatch"}:
                facts = self._graph_facts(checkpoint, request)
                facts["journal.original_effect"] = ReadTarget(kind="original_effect", operation=operation,
                    generation=record.intent.binding.generation, action_id=record.intent.action_id,
                    provider_key=record.intent.provider_key, fingerprint=record.intent.argument_fingerprint)
                return self._transition(checkpoint, request, "read_effect", facts=facts)
            if record.verification is None or record.verification.status != "verified":
                unknown = record.state in {"outcome_unknown", "dispatching"}
                self._selected(checkpoint, "mark_unknown" if unknown else "ask_operator")
                return self._pause(checkpoint, request, unknown=unknown)
            operation = {"verification": "finish", "verify_refusal": "verify_refusal", "verify_return": "verify_return"}[phase]
        elif phase == "handoff_attempted":
            record = self._records(checkpoint).get("enqueue_handoff")
            status = record.verification.status if record and record.verification else "outcome_unknown"
            disposition = {"verified": "pending", "pending": "pending", "rejected": "blocked"}.get(status, "outcome_unknown")
            facts = self._graph_facts(checkpoint, request)
            facts.update({"operator.handoff_attempt": "recorded", "operator.handoff_disposition": disposition})
            return self._transition(checkpoint, request, "record_handoff_" + disposition, facts=facts)
        elif phase.startswith("handoff_"):
            facts = self._graph_facts(checkpoint, request)
            facts["operator.handoff_disposition"] = phase.removeprefix("handoff_")
            return self._transition(checkpoint, request, "finish", facts=facts)
        else:
            operation = _LOCAL.get(phase)
        if checkpoint.next_gate not in {phase, operation}:
            raise GateDenied("scope_denied")
        if operation in _STAGES:
            return self._external(checkpoint, request, operation)
        if operation is None:
            return self._save(checkpoint, processing_status="unavailable")
        try:
            return self._transition(checkpoint, request, operation)
        except GateDenied:
            return self._pause(checkpoint, request)

    def _drive(self, checkpoint, request, auth, *, recovering=False):
        if checkpoint.stop.requested:
            return self.build_case_result(checkpoint)
        # One sweep of the finite graph per entry. Unknown/wait states pause;
        # recovery performs at most one original read, never a polling loop.
        limit = len(self.profile.processes[request.kind].phases) * 2
        for _ in range(limit):
            if self.process.is_terminal(checkpoint.phase):
                break
            checkpoint = self.run_one_approved_phase(checkpoint, request, auth, recovering=recovering)
            recovering = False
            if checkpoint.processing_status == "unavailable" or checkpoint.stop.requested:
                break
        else:
            checkpoint = self._save(checkpoint, processing_status="unavailable")
        return self.build_case_result(checkpoint)

    def build_case_result(self, checkpoint, *, save=True):
        records = self._records(checkpoint)
        effects = {op: record.verification for op, record in records.items() if record.verification is not None}
        for operation, record in records.items():
            if checkpoint.stop.requested and record.state == "prepared":
                intent = record.intent
                effects[operation] = VerificationResult(status="rejected", object_id=intent.binding.object_id,
                    action_id=intent.action_id, fingerprint=intent.argument_fingerprint,
                    postcondition=intent.postcondition, reason="stopped_before_entry")
            elif record.verification is None and record.state != "prepared":
                intent = record.intent
                effects[operation] = VerificationResult(status="outcome_unknown", object_id=intent.binding.object_id,
                    action_id=intent.action_id, fingerprint=intent.argument_fingerprint, postcondition=intent.postcondition,
                    reason="entry_unresolved")
        handoff = effects.get("enqueue_handoff")
        handoff_status = ("none" if handoff is None else {"verified": "pending", "pending": "pending",
                         "rejected": "rejected"}.get(handoff.status, "outcome_unknown"))
        request = self.store.original_request(checkpoint.binding.case_id, checkpoint.binding.generation)
        has_media = bool(request.evidence_ids or (request.narrative and request.narrative.strip()))
        result = SavedResult(binding=checkpoint.binding, fingerprint=checkpoint.binding.fingerprint,
            result_version="v1", as_of=self.clock.now(), effects=effects, stop=checkpoint.stop,
            wait_status="pending" if checkpoint.phase.startswith("wait") or checkpoint.phase.startswith("outcome_unknown") else "none",
            handoff_status=handoff_status, media_status="unavailable" if has_media else "none",
            evidence_refs=sorted({ref for verification in effects.values() for ref in verification.evidence_refs}),
            policy_refs=[self.profile.policy_hash], rationale="Offline phase " + checkpoint.phase +
            ("; scoped continuation unavailable" if checkpoint.processing_status == "unavailable" else ""))
        if save and not checkpoint.stop.requested and checkpoint.phase == self.profile.processes[request.kind].completion.phase:
            self.store.save_result(result)
        return result
