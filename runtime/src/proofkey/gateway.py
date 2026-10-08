"""One durable, authenticated physical-effect path for all six ports."""
from datetime import timedelta
import math
from uuid import uuid4

from .contracts import (ActionProposal, AuthContext, AuthorityReadback, CanonicalRequest, EffectIntent, PhaseCheckpoint, ReadRequest, RequestBinding,
                        ReadTarget, RevisionVector, VerificationResult)
from .identity import fingerprint, stable_action_id
from .journal import JournalFailure
from .policy import (GateDenied, IDENTITY_FIELDS, OWNER_FIELDS, PolicyGate,
                     qualified_observations, required_fields)
from .verifier import expected_facts, verify

_PORTS = {"reschedule": "scheduling", "register_goods_refusal": "delivery", "register_service_refusal": "delivery",
          "create_return": "returns", "send_clarification": "messaging", "send_status": "messaging",
          "enqueue_handoff": "operator", "transfer_owner": "operator"}
_ORIGINAL_READS = {"reschedule": ("scheduling", "read_schedule"), "register_goods_refusal": ("delivery", "read_refusal"),
                   "register_service_refusal": ("delivery", "read_refusal"), "create_return": ("returns", "read_return"),
                   "send_clarification": ("messaging", "read_message"), "send_status": ("messaging", "read_message"),
                   "enqueue_handoff": ("operator", "read_receipt"), "transfer_owner": ("operator", "read_owner")}
_AUTHORITY_READS = {"case": ("case", "read_case"), "customer": ("case", "read_principal"),
                    "delivery": ("delivery", "read_delivery"), "policy": ("case", "read_case"),
                    "ownership": ("operator", "read_owner"), "scheduling": ("scheduling", "list_permitted_slots"),
                    "goods": ("delivery", "read_refusal"), "service": ("delivery", "read_refusal"),
                    "returns": ("returns", "read_return_policy"), "messaging": ("messaging", "read_message"),
                    "operator": ("operator", "read_receipt")}


class ActionGateway:
    def __init__(self, profile, bundle, store, clock, auth=None):
        self.profile, self.bundle, self.store, self.clock, self.auth = profile, bundle, store, clock, auth
        self.gate = PolicyGate(profile)

    @staticmethod
    def _denied():
        return VerificationResult(status="rejected", reason="scope_denied")

    def _authenticated(self):
        if not isinstance(self.auth, AuthContext) or not callable(getattr(self.clock, "wait", None)):
            raise GateDenied("scope_denied")

    def _pace(self, deadline):
        self._authenticated()
        limits = [c.shared_limits.rate_per_second for c in self.profile.capabilities.values()
                  if c.shared_limits.account_id == self.profile.capabilities["read_authority"].shared_limits.account_id]
        if not limits or any(rate is None or not math.isfinite(rate) or rate <= 0 for rate in limits):
            raise GateDenied("scope_denied")
        delay = 1.0 / min(limits) + 0.000001
        now = self.clock.now()
        if now + timedelta(seconds=delay) >= deadline:
            raise GateDenied("scope_denied")
        self.clock.wait(delay)
        if self.clock.now() < now or self.clock.now() >= deadline:
            raise GateDenied("scope_denied")

    def _settle(self, lease, completed, admission=False):
        elapsed = (self.clock.now() - lease.started_at).total_seconds()
        if elapsed < 0 or not math.isfinite(elapsed):
            raise GateDenied("scope_denied")
        if elapsed > lease.reserved_seconds:
            finish = self.store.finish_admission_read if admission else self.store.finish_entry
            finish(lease.entry_id, elapsed)
            raise GateDenied("scope_denied")
        if completed:
            finish = self.store.finish_admission_read if admission else self.store.finish_entry
            finish(lease.entry_id, elapsed)
        if self.clock.now() >= lease.deadline:
            raise GateDenied("scope_denied")

    def _read(self, scope, target, port, method, *, purpose, action_id=None, attempt_id=None, deadline=None):
        limit = deadline or self.store.checkpoint(scope.case_id).deadline
        self._pace(limit)
        lease = (self.store.begin_admission_read(attempt_id, self.clock.now()) if attempt_id else
                 self.store.begin_read(scope.case_id, self.clock.now(), action_id=action_id))
        request = ReadRequest(case_id=scope.case_id, object_id=scope.object_id, caller_id=self.auth.caller_id,
            proof_reference=self.auth.proof_reference, purpose=purpose, deadline=min(limit, lease.deadline), target=target)
        reply = getattr(getattr(self.bundle, port), method)(request)
        reply = AuthorityReadback.model_validate(reply.model_dump())
        completed = bool(reply.evidence_refs) and reply.stage not in {"unknown", "unavailable"}
        # A definitive ACL rejection is a known read completion, not proof about an effect.
        completed = completed or reply.stage == "scope_rejected"
        self._settle(lease, completed, admission=attempt_id is not None)
        if (self.clock.now() >= request.deadline or reply.as_of < lease.started_at or reply.as_of > self.clock.now()
                or any(o.observed_at < lease.started_at or o.observed_at > reply.as_of for o in reply.observations)):
            raise GateDenied("scope_denied")
        return reply

    def _facts(self, scope, fields, *, attempt_id=None, deadline=None):
        observations = []
        for authority, (port, method) in _AUTHORITY_READS.items():
            facts = sorted(key.partition(".")[2] for key in fields if key.partition(".")[0] == authority)
            if not facts:
                continue
            target = ReadTarget(kind="authority_facts", authority=authority, facts=facts)
            reply = self._read(scope, target, port, method, purpose="bind_request" if attempt_id else "material_authority",
                               attempt_id=attempt_id, deadline=deadline)
            if (reply.object_id != scope.object_id or reply.stage != "observed" or not reply.evidence_refs
                    or {authority + "." + fact for fact in facts} != {o.authority + "." + o.fact for o in reply.observations}):
                raise GateDenied("scope_denied")
            observations.extend(reply.observations)
        indexed = qualified_observations(self.profile, scope.object_id, observations)
        if set(indexed) != set(fields):
            raise GateDenied("scope_denied")
        return tuple(observations)

    def read_material_authorities(self, intent):
        """Trusted host planning helper; every physical read reserves its own lease."""
        self._active(intent.binding.case_id, intent.binding, intent)
        return self._facts(intent.binding, required_fields(self.profile, intent.operation) | OWNER_FIELDS,
                           deadline=intent.deadline)

    def _active(self, case_id, binding=None, intent=None):
        self._authenticated()
        checkpoint = self.store.checkpoint(case_id)
        if (checkpoint.stop.requested or checkpoint.ownership_state in {"pending", "transfer_pending", "stopped"}
                or (binding is not None and checkpoint.binding != binding) or checkpoint.profile_version != self.profile.version
                or self.clock.now() >= checkpoint.deadline):
            raise GateDenied("scope_denied")
        if intent is not None and (self.clock.now() >= intent.deadline or intent.profile_version != checkpoint.profile_version
                or intent.process_version != checkpoint.process_version or intent.policy_version != checkpoint.policy_version):
            raise GateDenied("scope_denied")
        if self.store.original_request(case_id, checkpoint.binding.generation) is None:
            raise GateDenied("scope_denied")
        return checkpoint

    def _return_predecessor(self, intent):
        if intent.operation != "create_return":
            return
        predecessors = [r for r in self.store.intents(intent.binding.case_id) if r.intent.binding == intent.binding
                        and r.intent.operation == "register_goods_refusal" and r.state == "verified"
                        and r.verification is not None and r.verification.status == "verified"
                        and r.intent.arguments.get("inventory") == intent.arguments.get("inventory")]
        if not predecessors:
            raise GateDenied("scope_denied")

    def _run(self, intent, observations, *, is_resend=False):
        checkpoint = self._active(intent.binding.case_id, intent.binding, intent)
        original = self.store.original_request(intent.binding.case_id, intent.binding.generation)
        values = {key: obs.value for key, obs in qualified_observations(self.profile, intent.binding.object_id, observations).items()}
        if values.get("ownership.owner") != self.auth.caller_id:
            raise GateDenied("scope_denied")
        proposal = ActionProposal(operation=intent.operation, stage=intent.stage, arguments=intent.arguments, evidence_refs=[])
        decision = self.gate.evaluate(original, proposal, observations, checkpoint)
        if not decision.allowed or expected_facts(intent) is None:
            raise GateDenied("scope_denied")
        required = required_fields(self.profile, intent.operation)
        actual = {key: observation.revision for key, observation in qualified_observations(self.profile, intent.binding.object_id, observations).items()}
        if (any(intent.expected_revisions.revisions.get(key) != actual[key] for key in required)
                or intent.ownership_state_revision != values.get("ownership.state_revision")
                or intent.ownership_epoch != values.get("ownership.epoch")):
            raise GateDenied("scope_denied")
        self._return_predecessor(intent)
        if not is_resend:
            self.store.prepare(intent)
        self._pace(min(intent.deadline, self.store.checkpoint(intent.binding.case_id).deadline))
        lease = self.store.begin_dispatch(intent, self.clock.now(), is_resend=is_resend)
        try:
            dispatch = getattr(getattr(self.bundle, _PORTS[intent.operation]), intent.operation)(intent, deadline=lease.deadline)
        except Exception:
            dispatch = None
        if dispatch is not None:
            self._settle(lease, dispatch.status != "outcome_unknown")
        if dispatch is not None and dispatch.status == "rejected":
            result = VerificationResult(status="rejected", object_id=intent.binding.object_id, action_id=intent.action_id,
                fingerprint=intent.argument_fingerprint, postcondition=intent.postcondition, reason="provider_rejected")
            self.store.record_verification(intent.action_id, result)
            return result
        return self._read_and_verify(intent, dispatch.provider_request_id if dispatch is not None else None)[0]

    def _read_and_verify(self, intent, provider_request_id=None):
        port, method = _ORIGINAL_READS[intent.operation]
        target = ReadTarget(kind="original_effect", operation=intent.operation, generation=intent.binding.generation,
            action_id=intent.action_id, provider_key=intent.provider_key, fingerprint=intent.argument_fingerprint)
        try:
            read = self._read(intent.binding, target, port, method, purpose="reconcile_original", action_id=intent.action_id)
            if read.stage == "scope_rejected":
                return self._denied(), None
            if provider_request_id is not None and read.provider_request_id is not None and provider_request_id != read.provider_request_id:
                result = VerificationResult(status="conflict", object_id=intent.binding.object_id, action_id=intent.action_id,
                    fingerprint=intent.argument_fingerprint, postcondition=intent.postcondition, reason="provider_identity_conflict")
            else:
                result = verify(intent, read)
        except Exception:
            result = VerificationResult(status="outcome_unknown", reason="original_read_unavailable")
            read = None
        saved = self.store.intent(intent.action_id)
        if saved.state in {"verified", "conflict"}:
            # New ACL-qualified reads cannot rewrite an immutable verification receipt.
            if result.status == "verified":
                result = saved.verification
        else:
            self.store.record_verification(intent.action_id, result)
        return result, read

    def execute(self, intent):
        entered = False
        try:
            intent = EffectIntent.model_validate(intent.model_dump())
            self._authenticated()
            required_fields(self.profile, intent.operation)
            try:
                record = self.store.intent(intent.action_id)
            except JournalFailure:
                record = None
            if record is not None:
                if record.intent != intent:
                    return VerificationResult(status="conflict", reason="immutable_intent_conflict")
                if record.state != "prepared":
                    return self.reconcile(intent.action_id)
            observations = self.read_material_authorities(intent)
            return self._run(intent, observations)
        except Exception:
            # Never convert a failure after entry into an invented nonexecution result.
            try:
                entered = self.store.intent(intent.action_id).state != "prepared"
            except (JournalFailure, AttributeError):
                pass
            return VerificationResult(status="outcome_unknown", reason="entry_unresolved") if entered else self._denied()

    def reconcile(self, action_id):
        try:
            self._authenticated()
            record = self.store.intent(action_id)
            intent = record.intent
            if intent.operation not in _PORTS or intent.profile_version != self.profile.version or record.state == "prepared":
                raise GateDenied("scope_denied")
            if record.state in {"verified", "conflict"}:
                # Still check current public read ACL before disclosing a saved result.
                result, _ = self._read_and_verify(intent)
                return result
            result, read = self._read_and_verify(intent)
            if result.status not in {"outcome_unknown", "rejected"} or read is None:
                return result
            capability = self.profile.capabilities[intent.operation]
            idempotent = (capability.idempotency_scope.status == "supported" and capability.idempotency_scope.basis
                          and capability.idempotency_scope.evidence_ref)
            terminal = (result.status == "rejected" and read.nonexecution.status == "proven"
                        and read.nonexecution.basis == capability.terminal_nonexecution_basis.basis
                        and capability.terminal_nonexecution_basis.status == "supported")
            if not (idempotent or terminal):
                return result
            try:
                observations = self.read_material_authorities(intent)
                return self._run(intent, observations, is_resend=True)
            except Exception:
                return result
        except Exception:
            return self._denied()

    def execute_proposal(self, case_id, declared_operation, build_proposal):
        intent = None
        try:
            checkpoint = self._active(case_id)
            fields = required_fields(self.profile, declared_operation)
            observations = self._facts(checkpoint.binding, fields | OWNER_FIELDS)
            original = self.store.original_request(case_id, checkpoint.binding.generation)
            proposal, postcondition = build_proposal(original, observations)
            if not isinstance(proposal, ActionProposal) or proposal.operation != declared_operation:
                raise GateDenied("scope_denied")
            proposal = ActionProposal.model_validate(proposal.model_dump())
            indexed = qualified_observations(self.profile, checkpoint.binding.object_id, observations)
            action_id = stable_action_id(checkpoint.binding, proposal.operation, proposal.stage)
            intent = EffectIntent(binding=checkpoint.binding, operation=proposal.operation, stage=proposal.stage,
                action_id=action_id, provider_key=action_id, arguments=proposal.arguments, argument_fingerprint=fingerprint(proposal.arguments),
                profile_version=checkpoint.profile_version, process_version=checkpoint.process_version, policy_version=checkpoint.policy_version,
                consent_revision=checkpoint.binding.consent_revision, expected_revisions=RevisionVector(revisions={key: indexed[key].revision for key in fields}),
                postcondition=postcondition, deadline=checkpoint.deadline,
                ownership_state_revision=indexed["ownership.state_revision"].value, ownership_epoch=indexed["ownership.epoch"].value)
            return self._run(intent, observations)
        except Exception:
            if intent is not None:
                try:
                    if self.store.intent(intent.action_id).state != "prepared":
                        return VerificationResult(status="outcome_unknown", reason="entry_unresolved")
                except JournalFailure:
                    pass
            return self._denied()

    def bind_request(self, request, deadline):
        try:
            self._authenticated()
            request = CanonicalRequest.model_validate(request.model_dump())
            attempt = self.store.start_admission("attempt:" + uuid4().hex, self.auth, request, self.clock.now(), deadline)
            observations = self._facts(request, IDENTITY_FIELDS, attempt_id=attempt.attempt_id, deadline=attempt.deadline)
            binding = self.gate.bind_request(request, self.auth, observations)
            spec = self.profile.processes.get(request.kind)
            if spec is None:
                raise GateDenied("scope_denied")
            current = self.store.find_request(binding.case_id, binding.request_id, binding.request_revision, binding.consent_revision, binding.fingerprint)
            if current is not None:
                if current.generation != binding.generation:
                    raise GateDenied("scope_denied")
                binding = current
                checkpoint = self.store.checkpoint(binding.case_id)
            else:
                try:
                    previous = self.store.checkpoint(binding.case_id)
                except JournalFailure:
                    previous = None
                if previous is None:
                    structured = not (request.narrative and request.narrative.strip()) and not request.evidence_ids
                    planning_cap = 0 if structured else 4
                    checkpoint = PhaseCheckpoint(binding=binding, phase="intake", next_gate="intake", profile_version=self.profile.version,
                        process_version=spec.version, policy_version="v1", processing_status="pending",
                        budget={"case_id": binding.case_id, "deadline": attempt.deadline, "max_planner_calls": planning_cap,
                                "role_allowances": {"planning": {"max_invocations": planning_cap}}}, deadline=attempt.deadline)
                else:
                    binding = RequestBinding.model_validate({**binding.model_dump(), "supersedes_generation": previous.binding.generation})
                    checkpoint = PhaseCheckpoint.model_validate({**previous.model_dump(), "binding": binding,
                        "phase": "intake", "next_gate": "intake", "profile_version": self.profile.version,
                        "process_version": spec.version, "processing_status": "pending", "observations": []})
            self.store.admit_from_attempt(attempt.attempt_id, binding, request, checkpoint)
            return binding
        except Exception:
            raise GateDenied("scope_denied") from None
