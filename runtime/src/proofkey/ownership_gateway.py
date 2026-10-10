"""Gateway-owned registered ownership composition; no caller-supplied authority."""
from .contracts import (HumanOwnership, ReadTarget, OperatorDecision, GateDecision, VerificationResult,
    Identifier, Revision, NonnegativeInt, OwnerState)
from .ownership_contracts import (OwnershipSourceReadV1, OwnershipCurrentReadV1, OwnershipPacketV1,
    TRANSFER_FIELDS_V1, ownership_enabled, OperatorDecisionSubmissionV1, OperatorDispositionV1,
    TransferSourceReceiptV1, TransferPendingV1)
from .policy import GateDenied, IDENTITY_FIELDS, OWNER_FIELDS, qualified_observations
from .identity import stable_action_id
from .journal import JournalFailure
from .budget import BudgetExceeded
from .verifier import verify_registered_transfer
from pydantic import TypeAdapter


class OwnershipGateway:
    def execute_operator_decision(self, decision_id, intent, auth):
        entered = False
        try:
            with self._auth_scope(auth):
                from .contracts import EffectIntent
                intent = EffectIntent.model_validate(intent.model_dump())
                if not ownership_enabled(self.profile) or intent.decision_id != decision_id:
                    raise GateDenied("scope_denied")
                try:
                    saved = self.store.intent(intent.action_id)
                except JournalFailure:
                    saved = None
                if saved is not None:
                    if saved.intent != intent:
                        raise GateDenied("scope_denied")
                    if saved.state != "prepared":
                        entered = True
                        return self.reconcile_read_only(intent.action_id)
                source = self._ownership_sources(intent.binding, "decision")
                submission = self.store.decision_record(intent.binding, decision_id)
                if (submission.decision.actor_id != self.auth.caller_id
                        or submission.decision.proof_reference != self.auth.proof_reference):
                    raise GateDenied("scope_denied")
                self.gate.validate_registered_decision(submission, intent, source, self.clock.now())
                observations = self.read_material_authorities(intent)
                return self._run(intent, observations, decision_source=source, decision_submission=submission)
        except Exception:
            try:
                entered = self.store.intent(intent.action_id).state != "prepared"
            except Exception:
                pass
            return VerificationResult(status="outcome_unknown", reason="entry_unresolved") if entered else self._denied()

    def execute_registered_transfer(self, transfer_id, auth):
        with self._auth_scope(auth):
            record = self.store.transfer_record(transfer_id)
            if self.store.intent(record.effect.action_id).state != "prepared":
                return self._reconcile_transfer(record)
            source = self._ownership_sources(record.intent.binding, "transfer", prepared=record)
            limit = min(record.intent.expires_at, source.grant.expires_at, source.checkpoint.deadline)
            self._pace(limit)
            anchor = self._timing.monotonic_anchor() if self._timing is not None else None
            lease = self.store.begin_registered_transfer(transfer_id, self.store.checkpoint(record.intent.case_id), self.clock.now())
            try:
                deadline = self._transport_deadline(min(limit, lease.deadline), lease, anchor)
                transport = self.bundle.operator.transfer_owner
                deadline = self._transport_deadline(deadline, lease, anchor)
                if self.clock.now() >= deadline:
                    raise GateDenied("scope_denied")
                dispatch = transport(record.effect, deadline=deadline, auth=self.auth)
                self._settle(lease, dispatch.status != "outcome_unknown", anchor=anchor)
            except Exception:
                self.store.mark_transfer_unknown_atomic(transfer_id, self.store.checkpoint(record.intent.case_id))
                raise GateDenied("entry_unresolved") from None
            return self._reconcile_transfer(record)

    def reconcile_registered_transfer(self, transfer_id, auth):
        with self._auth_scope(auth):
            record = self.store.transfer_record(transfer_id)
            if self.store.intent(record.effect.action_id).state == "prepared":
                raise GateDenied("scope_denied")
            return self._reconcile_transfer(record)

    def _reconcile_transfer(self, record):
        effect, binding = record.effect, record.intent.binding
        target = ReadTarget(kind="original_effect", operation=effect.operation, generation=binding.generation,
            action_id=effect.action_id, provider_key=effect.provider_key, fingerprint=effect.argument_fingerprint)
        try:
            read = self._read(binding, target, "operator", "read_owner", purpose="reconcile_original",
                action_id=effect.action_id, deadline=effect.deadline)
        except Exception:
            self.store.mark_transfer_unknown_atomic(record.intent.transfer_id, self.store.checkpoint(binding.case_id))
            raise GateDenied("original_read_unavailable") from None
        if read.stage == "scope_rejected":
            raise GateDenied("scope_denied")
        result = verify_registered_transfer(effect, read, profile=self.profile)
        saved = self.store.intent(effect.action_id)
        if saved.state not in {"verified", "conflict"}:
            self.store.record_verification(effect.action_id, result)
        if result.status not in {"verified", "rejected", "pending"}:
            if self.store.transfer_record(record.intent.transfer_id).lifecycle in {"accepted", "rejected"}:
                raise GateDenied("original_confirmation_unavailable")
            return self.store.mark_transfer_unknown_atomic(record.intent.transfer_id, self.store.checkpoint(binding.case_id))
        receipt = TypeAdapter(TransferSourceReceiptV1).validate_python(next(o.value for o in read.observations
            if o.authority+"."+o.fact == "operator.transfer_receipt"))
        try:
            current = self.read_current_ownership(binding, self.auth)
            return self.store.apply_transfer_receipt_atomic(record.intent.transfer_id, receipt, current,
                current.checkpoint, self.clock.now())
        except (GateDenied, JournalFailure, ValueError, BudgetExceeded):
            if self.store.transfer_record(record.intent.transfer_id).lifecycle in {"accepted", "rejected"}:
                raise GateDenied("current_confirmation_unavailable") from None
            return self.store.mark_transfer_unknown_atomic(record.intent.transfer_id, self.store.checkpoint(binding.case_id))

    def validate_operator_decision(self, submission, auth):
        try:
            with self._auth_scope(auth):
                legacy = isinstance(submission, OperatorDecision)
                decision = submission if legacy else submission.decision
                if (decision.actor_id != self.auth.caller_id or decision.proof_reference != self.auth.proof_reference
                        or legacy and decision.decision == "approve"):
                    raise GateDenied("scope_denied")
                source = self._ownership_sources(decision.binding, "decision")
                submission = (OperatorDecisionSubmissionV1(decision=decision, content_hash=source.packet.content_hash,
                    effect_scope=None) if legacy else OperatorDecisionSubmissionV1.model_validate(submission.model_dump()))
                result = self.gate.validate_registered_decision(submission, None, source, self.clock.now())
                self.store.record_decision_atomic(submission, source, self.clock.now())
                return result
        except Exception:
            return GateDecision(allowed=False, reason="scope_denied", verification=VerificationResult(status="rejected", reason="scope_denied"))

    def record_operator_disposition(self, disposition, auth):
        with self._auth_scope(auth):
            disposition = OperatorDispositionV1.model_validate(disposition.model_dump())
            if disposition.actor_id != self.auth.caller_id or disposition.proof_reference != self.auth.proof_reference:
                raise GateDenied("scope_denied")
            source = self._ownership_sources(disposition.binding, "disposition")
            packet, grant = source.packet, source.grant
            if (disposition.disposition not in grant.dispositions or disposition.content_hash != packet.content_hash
                    or (disposition.packet_id, disposition.packet_hash, disposition.packet_revision, disposition.owner,
                        disposition.epoch, disposition.state_revision) !=
                       (packet.packet_id, packet.packet_hash, packet.packet_revision, packet.accepted_owner,
                        packet.accepted_epoch, packet.accepted_state_revision)
                    or self.clock.now() >= min(disposition.expires_at, grant.expires_at)):
                raise GateDenied("scope_denied")
            self.store.record_disposition_atomic(disposition, source, self.clock.now())
            return disposition

    def _ownership_batch(self, binding, fields, purpose, checkpoint):
        from .gateway import _AUTHORITY_READS
        observations, entries = [], []
        validators = self._source_validators(binding, checkpoint)
        # Current packet confirms source transitions, not the old local fence.
        def typed_owner(read):
            values = {o.authority+"."+o.fact:o.value for o in read.observations}
            for key, schema in (("ownership.owner",Identifier), ("ownership.state",OwnerState),
                    ("ownership.state_revision",Revision), ("ownership.epoch",NonnegativeInt)):
                TypeAdapter(schema).validate_python(values[key], strict=True)
        validators["ownership"] = typed_owner
        for authority, (port, method) in _AUTHORITY_READS.items():
            facts = sorted(k.partition(".")[2] for k in fields if k.partition(".")[0] == authority)
            if not facts:
                continue
            if authority == "operator":
                method = "read_owner"
            read = self._leased_read(binding, ReadTarget(kind="authority_facts", authority=authority, facts=facts),
                port, method, purpose=purpose, validate=validators.get(authority))
            if read.reply.stage != "observed":
                raise GateDenied("scope_denied")
            observations.extend(read.reply.observations)
            entries.append(read.entry_id)
        if set(qualified_observations(self.profile, binding.object_id, observations)) != set(fields):
            raise GateDenied("scope_denied")
        return observations, entries

    def _ownership_checkpoint(self, binding):
        checkpoint, original = self._configured_original(binding)
        if (not ownership_enabled(self.profile) or checkpoint.stop.requested or self.clock.now() >= checkpoint.deadline
                or checkpoint.process_version != self.profile.processes[original.kind].version):
            raise GateDenied("scope_denied")
        return checkpoint

    def read_ownership_sources(self, binding, auth, purpose):
        with self._auth_scope(auth):
            return self._ownership_sources(binding, purpose)

    def _ownership_sources(self, binding, purpose, *, prepared=None):
        checkpoint = self._ownership_checkpoint(binding)
        if purpose not in {"transfer", "decision", "disposition"}:
            raise GateDenied("scope_denied")
        fields = TRANSFER_FIELDS_V1 if purpose == "transfer" else IDENTITY_FIELDS | OWNER_FIELDS | {
            "policy.version", "operator.ownership_packet", "operator.ownership_grant"}
        observations, entries = self._ownership_batch(binding, fields, purpose, checkpoint)
        current = self._ownership_checkpoint(binding)
        evaluated = current
        if prepared is not None:
            origin = prepared.origin_checkpoint
            if (current.model_copy(update={"budget": origin.budget, "ownership_state": origin.ownership_state}) != origin
                    or current.ownership_state != "transfer_pending"):
                raise GateDenied("scope_denied")
            evaluated = current.model_copy(update={"ownership_state": origin.ownership_state})
        packet, grant = self.gate.validate_registered_ownership(binding, self.auth, observations, evaluated,
            purpose=purpose, now=self.clock.now())
        if prepared is not None:
            saved = prepared.registration_source
            if (packet != saved.packet or grant != saved.grant
                    or {o.authority+"."+o.fact: o.revision for o in observations} != prepared.effect.expected_revisions.revisions):
                raise GateDenied("scope_denied")
        return OwnershipSourceReadV1(binding=binding, checkpoint=current, packet=packet, grant=grant,
            observations=observations, read_entry_ids=entries, as_of=max(o.observed_at for o in observations),
            profile_hash=self.profile.release_hash, process_hash=self.profile.process_hash, policy_hash=self.profile.policy_hash)

    def read_current_ownership(self, binding, auth):
        with self._auth_scope(auth):
            checkpoint = self._ownership_checkpoint(binding)
            fields = IDENTITY_FIELDS | OWNER_FIELDS | {"policy.version", "operator.ownership_packet"}
            observations, entries = self._ownership_batch(binding, fields, "current_owner", checkpoint)
            current = self._ownership_checkpoint(binding)
            values = {o.authority+"."+o.fact: o.value for o in observations}
            packet = OwnershipPacketV1.model_validate(values["operator.ownership_packet"])
            if values["policy.version"] != current.policy_version or packet.binding != binding:
                raise GateDenied("scope_denied")
            state = "transfer_pending" if values["ownership.state"] == "pending" else values["ownership.state"]
            transfer_id = None
            pending_evidence = None
            try:
                record = self.store.transfer_record(stable_action_id(binding, "transfer_owner", "request"))
                if record.intent.binding != binding:
                    raise GateDenied("scope_denied")
                transfer_id = record.intent.transfer_id
                if (isinstance(record.source_receipt, TransferPendingV1)
                        and record.source_receipt.pending_state_revision == values["ownership.state_revision"]):
                    pending_evidence = record.source_receipt.evidence_ref
            except JournalFailure as exc:
                if str(exc) != "No complete registered ownership transfer original" or state == "transfer_pending":
                    raise
            owner = HumanOwnership(binding=binding, owner=values["ownership.owner"], epoch=values["ownership.epoch"],
                state_revision=values["ownership.state_revision"], state=state, packet_id=packet.packet_id,
                packet_hash=packet.packet_hash, packet_revision=packet.packet_revision,
                acceptance_evidence=packet.acceptance_evidence if state == "accepted" else None,
                pending_evidence=pending_evidence, transfer_id=transfer_id)
            return OwnershipCurrentReadV1(binding=binding, checkpoint=current, packet=packet, ownership=owner,
                observations=observations, read_entry_ids=entries, as_of=max(o.observed_at for o in observations),
                profile_hash=self.profile.release_hash, process_hash=self.profile.process_hash, policy_hash=self.profile.policy_hash)
