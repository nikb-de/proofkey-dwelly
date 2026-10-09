"""Host-owned scoped questions; accepted reply bodies remain untrusted data."""
from datetime import timedelta

from .contracts import (ActionProposal, AuthContext, PhaseCheckpoint, ScopedReply,
                        WaitState)
from .identity import fingerprint, request_fingerprint, stable_action_id
from .journal import JournalFailure
from .policy import GateDenied, PolicyGate, qualified_observations
from .process import ProcessController
from .profiles import validate_profile
from .packet_contracts import packet_enabled
from .wait_contracts import WaitRecordV1


class WaitService:
    def __init__(self, profile, bundle, store, clock, *, gateway):
        self.profile = validate_profile(profile)
        if (gateway.profile != self.profile or gateway.bundle is not bundle
                or gateway.store is not store or gateway.clock is not clock):
            raise ValueError("Waits require the host's same gateway and source bundle")
        self.bundle, self.store, self.clock, self.gateway = bundle, store, clock, gateway

    @staticmethod
    def question_id(binding, *, operation="send_clarification"):
        if operation not in {"send_clarification", "enqueue_handoff"}:
            raise GateDenied("scope_denied")
        return "question:" + stable_action_id(binding, operation,
            "enqueue" if operation == "enqueue_handoff" else "send")

    def _configured(self, checkpoint, record=None):
        profile = validate_profile(self.profile)
        current = self.store.checkpoint(checkpoint.binding.case_id)
        original = self.store.original_request(checkpoint.binding.case_id, checkpoint.binding.generation)
        spec = profile.processes.get(original.kind) if original is not None else None
        if (current.binding != checkpoint.binding or original is None or spec is None
                or request_fingerprint(original) != checkpoint.binding.fingerprint
                or checkpoint.profile_version != profile.version or checkpoint.process_version != spec.version
                or checkpoint.policy_version != "v1" or checkpoint.phase not in spec.phases
                or self.gateway.profile != profile):
            raise GateDenied("scope_denied")
        if record is not None and (record.profile_hash != profile.release_hash
                or record.policy_hash != profile.policy_hash or record.process != spec
                or any(getattr(record.origin_checkpoint, key) != getattr(checkpoint, key)
                    for key in ("binding", "profile_version", "process_version", "policy_version"))):
            raise GateDenied("scope_denied")
        return original, spec

    @staticmethod
    def _accounting_only(before, after):
        # Reads may update accounting only; any concurrent control mutation denies.
        if after.model_copy(update={"budget": before.budget}) != before:
            raise GateDenied("scope_denied")

    def _pending(self, question_id):
        record = self.store.load_wait_record(question_id)
        current = self.store.checkpoint(record.wait.binding.case_id)
        self._configured(current, record)
        if (record.lifecycle != "pending" or current.stop.requested
                or self.store.generation_stop(current.binding).requested
                or current.binding != record.wait.binding
                or current.question_id != question_id or current.phase != record.wait_phase
                or current.awaited_fields != record.wait.awaited_fields
                or (current.ownership_state, current.ownership_state_revision, current.ownership_epoch) !=
                   (record.owner_state, record.owner_revision, record.owner_epoch)):
            raise GateDenied("scope_denied")
        return record, current

    def create(self, checkpoint, fields):
        """Persist declared questions during the same gateway's owned batch."""
        checkpoint = PhaseCheckpoint.model_validate(checkpoint.model_dump())
        original, spec = self._configured(checkpoint)
        if (self.store.checkpoint(checkpoint.binding.case_id) != checkpoint or checkpoint.stop.requested
                or self.clock.now() >= checkpoint.deadline):
            raise GateDenied("scope_denied")
        edges = [edge for edge in spec.edges if edge.origin == checkpoint.phase
                 and edge.operation in {"send_clarification", "enqueue_handoff"}
                 and any(wait.phase == edge.target and isinstance(fields, (list, tuple))
                         and list(fields) == wait.awaited_fields for wait in spec.waits)]
        if len(edges) != 1:
            raise GateDenied("scope_denied")
        edge = edges[0]
        contract = next(wait for wait in spec.waits if wait.phase == edge.target)
        if edge.operation == "enqueue_handoff":
            return self._create_operator(checkpoint, original, spec, edge, contract)
        if (not isinstance(fields, (list, tuple)) or list(fields) != contract.awaited_fields
                or edge.operation != "send_clarification" or contract.recipient_role != "customer"):
            raise GateDenied("scope_denied")
        action_id = stable_action_id(checkpoint.binding, edge.operation, "send")
        question_id = self.question_id(checkpoint.binding)
        records = [record for record in self.store.intents(checkpoint.binding.case_id)
                   if record.intent.binding == checkpoint.binding and record.intent.operation == edge.operation]
        existing_wait = self.store.wait(question_id)
        if existing_wait is not None:
            record = self.store.load_wait_record(question_id)
            self._configured(checkpoint, record)
            if (record.lifecycle != "pending" or record.wait.origin != checkpoint.phase
                    or record.communication_action_id != action_id or record.wait.awaited_fields != list(fields)
                    or self.clock.now() >= record.wait.expires_at):
                raise GateDenied("scope_denied")
        elif records:
            # An existing original can never retroactively acquire a new question.
            raise GateDenied("scope_denied")
        if records:
            if len(records) != 1 or existing_wait is None:
                raise GateDenied("scope_denied")
            intent_record = records[0]
            args = intent_record.intent.arguments
            if (intent_record.intent.action_id != action_id or args != self._arguments(record.wait)
                    or intent_record.intent.stage != "send"):
                raise GateDenied("scope_denied")
            if intent_record.state == "prepared":
                def resume(request, observations):
                    current = self.store.checkpoint(checkpoint.binding.case_id)
                    self._accounting_only(checkpoint, current)
                    self._configured(current, record)
                    if request != original:
                        raise GateDenied("scope_denied")
                    values = {key: item.value for key, item in qualified_observations(
                        self.profile, request.object_id, observations).items()}
                    self._saved_source_scope(record, current, values)
                    return ActionProposal(operation=edge.operation, stage="send",
                        arguments=intent_record.intent.arguments, evidence_refs=[]), intent_record.intent.postcondition
                result = self.gateway.execute_proposal(checkpoint.binding.case_id, edge.operation, resume)
            else:
                result = self.gateway.reconcile_read_only(action_id)
        else:
            def build(request, observations):
                current = self.store.checkpoint(checkpoint.binding.case_id)
                self._accounting_only(checkpoint, current)
                self._configured(current)
                indexed = qualified_observations(self.profile, request.object_id, observations)
                values = {key: item.value for key, item in indexed.items()}
                recipient = values.get("messaging.recipient")
                question_revision = values.get("case.question_revision")
                if (request != original or not isinstance(question_revision, str) or not question_revision.strip()
                        or recipient != request.principal_id
                        or values.get("ownership.owner") != self.gateway.auth.caller_id
                        or (values.get("ownership.state"), values.get("ownership.state_revision"), values.get("ownership.epoch")) !=
                           (current.ownership_state, current.ownership_state_revision, current.ownership_epoch)):
                    raise GateDenied("scope_denied")
                now = self.clock.now()
                wait = WaitState(question_id=question_id, binding=current.binding, origin=current.phase,
                    next_gate=contract.next_gate, recipient=recipient, owner_state_revision=current.ownership_state_revision,
                    awaited_fields=contract.awaited_fields, expires_at=min(current.deadline,
                        now + timedelta(seconds=contract.expiry_seconds)), budget=current.budget)
                arguments = self._arguments(wait)
                proposal = ActionProposal(operation=edge.operation, stage="send", arguments=arguments, evidence_refs=[])
                if not PolicyGate(self.profile).evaluate(request, proposal, observations, current).allowed:
                    raise GateDenied("scope_denied")
                if existing_wait is not None:
                    self._saved_source_scope(record, current, values)
                    # Crash after wait commit but before prepare: original scope,
                    # expiry and debit remain immutable under the same question.
                    return ActionProposal(operation=edge.operation, stage="send",
                        arguments=self._arguments(record.wait), evidence_refs=[]), {
                            "question_id": question_id, "recipient": record.wait.recipient, "status": "sent"}
                # Preserve only this leased host batch as immutable source context.
                origin = PhaseCheckpoint.model_validate({**current.model_dump(), "observations": list(observations)})
                self.store.save_checkpoint(origin)
                accept = [candidate for candidate in spec.edges if candidate.origin == edge.target
                          and candidate.target == contract.next_gate and candidate.operation.startswith("accept_")]
                expiry = [candidate for candidate in spec.edges if candidate.origin == edge.target
                          and candidate.operation == "expire_wait"]
                if len(accept) != 1 or len(expiry) != 1:
                    raise GateDenied("scope_denied")
                new_record = WaitRecordV1(wait=wait, origin_checkpoint=origin,
                    origin_hash=fingerprint(origin.model_dump(mode="json")), process=spec,
                    profile_hash=self.profile.release_hash, policy_hash=self.profile.policy_hash,
                    owner_id=values["ownership.owner"], owner_state=origin.ownership_state,
                    owner_revision=origin.ownership_state_revision, owner_epoch=origin.ownership_epoch,
                    recipient_role=contract.recipient_role, wait_phase=edge.target, communication_edge=edge,
                    communication_stage="send", communication_action_id=action_id,
                    accept_edge=accept[0], expiry_edge=expiry[0], created_at=now)
                self.store.create_wait_atomic(new_record, now)
                return proposal, {"question_id": question_id, "recipient": recipient, "status": "sent"}
            result = self.gateway.execute_proposal(checkpoint.binding.case_id, edge.operation, build)
        saved_wait = self.store.wait(question_id)
        if saved_wait is None:
            raise GateDenied("scope_denied")
        # A stored question may precede durable prepare during a genuine crash.
        # No caller reply or transport status is used to manufacture sent evidence.
        return saved_wait

    def _create_operator(self, checkpoint, original, spec, edge, contract):
        if contract.recipient_role != "operator" or not packet_enabled(self.profile):
            raise GateDenied("scope_denied")
        action_id = stable_action_id(checkpoint.binding, "enqueue_handoff", "enqueue")
        question_id = self.question_id(checkpoint.binding, operation="enqueue_handoff")
        communications = [r for r in self.store.intents(checkpoint.binding.case_id)
            if r.intent.binding == checkpoint.binding and r.intent.operation == "enqueue_handoff"]
        existing = self.store.wait(question_id)
        record = None
        if existing is not None:
            record = self.store.load_wait_record(question_id)
            self._configured(checkpoint, record)
            if (record.lifecycle != "pending" or record.communication_intent is None
                    or record.wait.origin != checkpoint.phase or record.communication_edge != edge
                    or record.communication_stage != "enqueue" or record.communication_action_id != action_id
                    or record.wait.awaited_fields != contract.awaited_fields
                    or self.clock.now() >= record.wait.expires_at):
                raise GateDenied("scope_denied")
        if communications:
            if (len(communications) != 1 or record is None
                    or communications[0].intent != record.communication_intent):
                # Nonwait, bare legacy or different originals cannot gain a wait.
                raise GateDenied("scope_denied")
            if communications[0].state != "prepared":
                self.gateway.reconcile_read_only(action_id)
                return record.wait
        accept = [e for e in spec.edges if e.origin == edge.target and e.target == contract.next_gate
                  and e.operation.startswith("accept_")]
        expiry = [e for e in spec.edges if e.origin == edge.target and e.operation == "expire_wait"]
        if len(accept) != 1 or len(expiry) != 1:
            raise GateDenied("scope_denied")

        def persist(intent, sources, supplied):
            current = self.store.checkpoint(checkpoint.binding.case_id)
            self._accounting_only(checkpoint, current)
            request, configured = self._configured(current, record)
            if (request != original or configured != spec or supplied != current
                    or intent.binding != checkpoint.binding or intent.action_id != action_id
                    or sources.binding != checkpoint.binding):
                raise GateDenied("scope_denied")
            values = {key: o.value for key, o in qualified_observations(
                self.profile, current.binding.object_id, sources.observations).items()}
            if (not isinstance(values.get("case.question_revision"), str)
                    or not values["case.question_revision"].strip()
                    or values.get("operator.recipient") != intent.arguments["recipient"]
                    or values.get("ownership.owner") != self.gateway.auth.caller_id
                    or type(values.get("ownership.epoch")) is not int
                    or (values.get("ownership.state"), values.get("ownership.state_revision"), values.get("ownership.epoch")) !=
                       (current.ownership_state, current.ownership_state_revision, current.ownership_epoch)):
                raise GateDenied("scope_denied")
            if record is not None:
                self._saved_source_scope(record, current, values)
                if intent != record.communication_intent:
                    raise GateDenied("scope_denied")
                return
            now = self.clock.now()
            wait = WaitState(question_id=question_id, binding=current.binding, origin=current.phase,
                next_gate=contract.next_gate, recipient=intent.arguments["recipient"],
                owner_state_revision=current.ownership_state_revision, awaited_fields=contract.awaited_fields,
                expires_at=min(current.deadline, now + timedelta(seconds=contract.expiry_seconds)), budget=current.budget)
            origin = PhaseCheckpoint.model_validate({**current.model_dump(), "observations": list(sources.observations)})
            new_record = WaitRecordV1(wait=wait, origin_checkpoint=origin,
                origin_hash=fingerprint(origin.model_dump(mode="json")), process=spec,
                profile_hash=self.profile.release_hash, policy_hash=self.profile.policy_hash,
                owner_id=values["ownership.owner"], owner_state=origin.ownership_state,
                owner_revision=origin.ownership_state_revision, owner_epoch=origin.ownership_epoch,
                recipient_role="operator", wait_phase=edge.target, communication_edge=edge,
                communication_stage="enqueue", communication_action_id=action_id,
                communication_intent=intent, accept_edge=accept[0], expiry_edge=expiry[0], created_at=now)
            self.store.save_checkpoint(origin)
            self.store.create_wait_atomic(new_record, now)

        self.gateway.enqueue_operator_packet(checkpoint.binding.case_id, "review_facts", before_prepare=persist)
        if self.store.wait(question_id) is None:
            raise GateDenied("scope_denied")
        return self.store.load_wait_record(question_id).wait

    def _saved_source_scope(self, record, current, values):
        original = {key: item.value for key, item in qualified_observations(
            self.profile, current.binding.object_id, record.origin_checkpoint.observations).items()}
        if (record.lifecycle != "pending" or self.clock.now() >= record.wait.expires_at
                or values.get("case.question_revision") != original.get("case.question_revision")
                or original.get("case.question_revision") is None
                or values.get("messaging.recipient" if record.recipient_role == "customer" else "operator.recipient") != record.wait.recipient
                or values.get("ownership.owner") != record.owner_id
                or type(values.get("ownership.epoch")) is not int
                or (values.get("ownership.state"), values.get("ownership.state_revision"), values.get("ownership.epoch")) !=
                   (record.owner_state, record.owner_revision, record.owner_epoch)
                or (current.ownership_state, current.ownership_state_revision, current.ownership_epoch) !=
                   (record.owner_state, record.owner_revision, record.owner_epoch)):
            raise GateDenied("scope_denied")

    @staticmethod
    def _arguments(wait):
        return {"question_id": wait.question_id, "recipient": wait.recipient,
                "text": "Please provide: " + ", ".join(wait.awaited_fields)}

    def _successor(self, record, current, edge):
        declared = {candidate.operation for candidate in record.process.edges if candidate.origin == edge.target}
        preferred = {"completeness": "authenticate", "operator_facts": "reenter_facts",
                     "exact_gate": "reschedule", "verification": "read_effect",
                     "verify_refusal": "read_effect", "verify_return": "read_effect",
                     "expired": "enqueue_handoff"}.get(edge.target)
        if preferred not in declared:
            raise GateDenied("scope_denied")
        return PhaseCheckpoint.model_validate({**current.model_dump(), "phase": edge.target,
            "next_gate": preferred, "processing_status": "pending", "observations": [],
            "question_id": None, "awaited_fields": []})

    def accept(self, reply, auth):
        if not isinstance(reply, ScopedReply) or not isinstance(auth, AuthContext):
            raise GateDenied("scope_denied")
        reply, auth = ScopedReply.model_validate(reply.model_dump()), AuthContext.model_validate(auth.model_dump())
        record, before = self._pending(reply.question_id)
        now = self.clock.now()
        if (reply.binding != record.wait.binding or reply.actor_id != auth.caller_id
                or reply.actor_id != record.wait.recipient or reply.request_revision != reply.binding.request_revision
                or reply.consent_revision != reply.binding.consent_revision or reply.owner_state_revision != record.owner_revision
                or set(reply.fields) != set(record.wait.awaited_fields)
                or not record.created_at <= reply.received_at <= now < record.wait.expires_at):
            raise GateDenied("scope_denied")
        communication = self.store.intent(record.communication_action_id)
        matches = (communication.intent == record.communication_intent if record.recipient_role == "operator"
                   else communication.intent.arguments == self._arguments(record.wait))
        if (communication.state == "prepared" or not matches
                or record.recipient_role == "operator" and record.communication_intent is None
                or communication.intent.binding != record.wait.binding
                or communication.intent.operation != record.communication_edge.operation
                or communication.intent.stage != record.communication_stage):
            raise GateDenied("scope_denied")
        if communication.verification is None or communication.verification.status != "verified":
            sent = self.gateway.reconcile_read_only(record.communication_action_id)
            if sent.status != "verified":
                raise GateDenied("scope_denied")
            before = self.store.checkpoint(reply.binding.case_id)
        observations = self.gateway.read_reply_sources(reply.binding, auth, recipient_role=record.recipient_role)
        current = self.store.checkpoint(reply.binding.case_id)
        self._accounting_only(before, current)
        self._pending(reply.question_id)
        values = {key: item.value for key, item in qualified_observations(
            self.profile, reply.binding.object_id, observations).items()}
        original_values = {key: item.value for key, item in qualified_observations(
            self.profile, reply.binding.object_id, record.origin_checkpoint.observations).items()}
        recipient_key = "messaging.recipient" if record.recipient_role == "customer" else "operator.recipient"
        if (values.get("case.question_revision") != original_values.get("case.question_revision")
                or original_values.get("case.question_revision") is None
                or values.get(recipient_key) != record.wait.recipient
                or values.get("ownership.owner") != record.owner_id
                or type(values.get("ownership.epoch")) is not int
                or values.get("ownership.epoch") != record.owner_epoch):
            raise GateDenied("scope_denied")
        successor = self._successor(record, current, record.accept_edge)
        consumed = self.store.consume_wait_reply_atomic(reply.question_id, current, reply, successor, self.clock.now())
        # Canonical private accepted_reply is never copied into authority data.
        if self.store.checkpoint(reply.binding.case_id) != consumed:
            raise GateDenied("scope_denied")
        sourced = PhaseCheckpoint.model_validate({**consumed.model_dump(), "observations": list(observations)})
        self.store.save_checkpoint(sourced)
        return self.store.checkpoint(reply.binding.case_id)

    def expire(self, question_id):
        record, current = self._pending(question_id)
        return self.store.expire_wait_atomic(question_id, current,
            self._successor(record, current, record.expiry_edge), self.clock.now())
