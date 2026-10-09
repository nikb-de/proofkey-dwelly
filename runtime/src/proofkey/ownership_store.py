"""Private journal composition; one database/transaction and no source authority.

The trusted gateway must produce fresh source snapshots. Existing read leases
prove local accounting, not the target or contents of a provider response.
"""
from datetime import timedelta

from .budget import BudgetExceeded, check_time
from .contracts import EffectIntent, HumanOwnership, PhaseCheckpoint, RequestBinding, TransferIntent
from .identity import fingerprint
from .ownership_contracts import (DecisionConsumedV1, DecisionRecordedV1, DispositionRecordedV1,
    OperatorDecisionSubmissionV1, OperatorDispositionV1, OwnershipCurrentReadV1, OwnershipSourceReadV1,
    TransferAcceptedV1, TransferArgumentsV1, TransferPendingV1, TransferRecordV1, TransferRegisteredV1,
    TransferRejectedV1, TransferResolvedV1, TransferReceiptRecordedV1, OwnerObservedV1, TRANSFER_FIELDS_V1)
from .policy import IDENTITY_FIELDS, OWNER_FIELDS


class OwnershipStore:
    def __init__(self, store):
        self.store = store

    @property
    def db(self):
        return self.store._db

    @staticmethod
    def fail(message):
        from .journal import JournalFailure
        raise JournalFailure(message)

    @staticmethod
    def typed(model, value):
        from .journal import _typed
        return _typed(model, value)

    def rows(self, case_id=None):
        from .journal import _json, _read
        rows = self.db.execute("SELECT * FROM transfers" + (" WHERE case_id=?" if case_id else ""),
                               (case_id,) if case_id else ()).fetchall()
        result = []
        for row in rows:
            raw = _json(row["transfer_json"])
            if raw.get("kind") == "transfer_record_v1":
                value = _read(TransferRecordV1, row["transfer_json"])
                if (value.intent.transfer_id, value.intent.case_id, value.intent.binding.generation, value.lifecycle) != (
                        row["transfer_id"], row["case_id"], row["generation"], row["state"]):
                    self.fail("Registered transfer index mismatch")
                result.append(value)
            elif "kind" in raw:
                self.fail("Unknown stored transfer tag")
        return result

    def is_tagged(self, transfer_id):
        return any(record.intent.transfer_id == transfer_id for record in self.rows())

    def check_fence(self, checkpoint):
        records = [record for record in self.rows(checkpoint.binding.case_id)
                   if record.lifecycle in {"prepared", "pending", "outcome_unknown"}]
        if len(records) > 1:
            self.fail("More than one unresolved ownership original")
        for record in records:
            if (checkpoint.binding != record.intent.binding or checkpoint.ownership_state != "transfer_pending"
                    or checkpoint.ownership_epoch != record.intent.expected_epoch
                    or checkpoint.ownership_state_revision != record.intent.expected_state_revision):
                self.fail("Unresolved registered original fences checkpoint ownership/generation")

    def _registry(self, binding, source=None):
        registry = self.store._ownership_processes
        if registry is None:
            self.fail("Ownership configuration_unavailable: trusted ProcessSpec registry required")
        request = self.store.original_request(binding.case_id, binding.generation)
        if request is None or request.kind not in registry.processes:
            self.fail("Original request has no registered ProcessSpec")
        spec = registry.processes[request.kind]
        if source is not None and (source.profile_hash, source.process_hash, source.policy_hash) != (
                registry.profile_hash, registry.process_hash, registry.policy_hash):
            self.fail("Ownership snapshot differs from frozen host registry hashes")
        return registry, spec

    def _leases(self, source):
        authorities = {item.authority for item in source.observations}
        if len(source.read_entry_ids) != len(authorities):
            self.fail("Ownership snapshot requires one accounted completed read per authority")
        leases = [self.store.entry(entry_id) for entry_id in source.read_entry_ids]
        for lease in leases:
            if (lease.kind != "read" or lease.state != "settled" or lease.control_scope is not None
                    or (lease.case_id, lease.generation) != (source.binding.case_id, source.binding.generation)
                    or lease.started_at > source.as_of or source.as_of > lease.deadline):
                self.fail("Ownership source read lacks matching bounded settled lease")
        if any(not any(lease.started_at <= item.observed_at <= lease.deadline for lease in leases)
               or item.provider_at is None or item.provider_at > item.observed_at
               for item in source.observations):
            self.fail("Ownership observation time/provenance differs from read accounting")

    def _source(self, source, now, *, transfer=False, current=False, durable=False):
        source = self.typed(OwnershipCurrentReadV1 if current else OwnershipSourceReadV1, source)
        self.store._assert_binding(source.binding)
        if durable and self.store._ownership_processes is None:
            registry, spec = None, None
        else:
            registry, spec = self._registry(source.binding, source)
        cp = source.checkpoint
        if (cp.profile_version != "v1.4" or (registry is not None and cp.profile_version != registry.profile_version)
                or (spec is not None and cp.process_version != spec.version)
                or cp.policy_version != "v1"):
            self.fail("Ownership snapshot frozen versions mismatch")
        if now < source.as_of or now > source.as_of + timedelta(seconds=10):
            self.fail("Ownership source snapshot not immediately fresh at original recording")
        if not durable:
            if self.store.checkpoint(source.binding.case_id) != cp:
                self.fail("Ownership source checkpoint CAS mismatch after read accounting")
        self._leases(source)
        if source.packet.accepted_at > source.as_of:
            self.fail("Packet acceptance cannot occur after source observation")
        facts = {item.authority + "." + item.fact: item for item in source.observations}
        required = TRANSFER_FIELDS_V1 if transfer else IDENTITY_FIELDS | OWNER_FIELDS | {"policy.version", "operator.ownership_packet"}
        if not current:
            required |= {"operator.ownership_grant"}
        if set(facts) != set(required):
            self.fail("Ownership source requires exact designated observations")
        values = {key: item.value for key, item in facts.items()}
        b = source.binding
        if (values["case.binding"] != {"case_id": b.case_id, "object_id": b.object_id,
                "principal_id": b.principal_id, "request_id": b.request_id}
                or values["case.request_revision"] != b.request_revision or values["case.authorization"] != "verified"
                or values["case.generation"] != b.generation or values["customer.consent_revision"] != b.consent_revision
                or values["policy.version"] != cp.policy_version
                or values["operator.ownership_packet"] != source.packet.model_dump(mode="json")):
            self.fail("Ownership source identity/policy/packet mismatch")
        owner = source.ownership if current else HumanOwnership(binding=b, owner=source.packet.accepted_owner,
            epoch=source.packet.accepted_epoch, state_revision=source.packet.accepted_state_revision,
            packet_id=source.packet.packet_id, packet_hash=source.packet.packet_hash,
            packet_revision=source.packet.packet_revision, state="accepted", acceptance_evidence=source.packet.acceptance_evidence)
        if ((values["ownership.owner"], values["ownership.state"], values["ownership.state_revision"], values["ownership.epoch"]) !=
                (owner.owner, owner.state, owner.state_revision, owner.epoch)):
            self.fail("Ownership observations disagree with typed current tuple")
        if not current and (values["operator.ownership_grant"] != source.grant.model_dump(mode="json")
                or source.grant.actor_id != owner.owner or source.packet.content_hash is None
                or (not durable and not source.grant.issued_at <= now < source.grant.expires_at)):
            self.fail("Ownership grant/actor/content interval mismatch")
        return source, spec, facts

    def _events(self, case_id=None):
        from .journal import _read, CheckpointAudit
        rows = self.db.execute("SELECT case_id,event_json FROM audit" + (" WHERE case_id=?" if case_id else "") + " ORDER BY sequence",
                               (case_id,) if case_id else ()).fetchall()
        events = []
        for row in rows:
            audit = _read(CheckpointAudit, row["event_json"])
            if audit.ownership_event is not None:
                events.append((row["case_id"], audit.ownership_event))
        return events

    def record(self, transfer_id):
        matches = [record for record in self.rows() if record.intent.transfer_id == transfer_id]
        if len(matches) != 1:
            self.fail("No complete registered ownership transfer original")
        record = matches[0]
        self.store._assert_binding(record.intent.binding)
        original = self.store.original_request(record.intent.case_id, record.intent.binding.generation)
        if original is None or record.original_input_hash != fingerprint(original.model_dump(mode="json")):
            self.fail("Registered transfer original input hash mismatch")
        intent_record = self.store.intent(record.effect.action_id)
        if intent_record.intent != record.effect:
            self.fail("Registered transfer differs from exact prepared effect")
        if self.store._versions(record.effect) != self.store._versions(record.origin_checkpoint):
            self.fail("Registered transfer frozen versions differ")
        if not self.store._audited_checkpoint_hash(record.intent.case_id, record.origin_checkpoint_hash):
            self.fail("Registered transfer origin checkpoint lacks durable audit")
        # Reopening without host configuration remains inventory-only; registration
        # and entry require the current trusted registry.
        _, spec, facts = self._source(record.registration_source, record.registered_at, transfer=True, durable=True)
        if spec is not None and not any(edge.origin == record.origin_checkpoint.phase
                and edge.target == record.origin_checkpoint.phase and edge.operation == "transfer_owner" for edge in spec.edges):
            self.fail("Registered transfer origin has no saved graph self edge")
        args = TransferArgumentsV1.model_validate(record.effect.arguments)
        if (record.effect.expected_revisions.revisions != {key: item.revision for key, item in facts.items()}
                or args.grant_revision != facts["operator.ownership_grant"].revision):
            self.fail("Registered transfer original revision vector/source grant mismatch")
        self.store.checkpoint(record.intent.case_id)
        registrations = [event for _, event in self._events(record.intent.case_id)
                         if isinstance(event, TransferRegisteredV1) and event.transfer_id == transfer_id]
        if len(registrations) != 1 or registrations[0] != TransferRegisteredV1(binding=record.intent.binding,
                transfer_id=transfer_id, original_effect_hash=fingerprint(record.effect.model_dump(mode="json")),
                origin_checkpoint_hash=record.origin_checkpoint_hash):
            self.fail("Registered transfer durable registration event mismatch")
        if record.source_receipt is not None and intent_record.state == "prepared":
            self.fail("Unentered local transfer cannot claim source execution evidence")
        if intent_record.state != "prepared":
            self._entered(record)
        history = [event for _, event in self._events(record.intent.case_id)
                   if isinstance(event, TransferReceiptRecordedV1) and event.transfer_id == transfer_id]
        for event in history:
            pending_record = record.model_copy(update={"lifecycle": "pending", "source_receipt": event.receipt})
            self._source(event.source_current, event.source_current.as_of, current=True, durable=True)
            self._confirm(pending_record, event.source_current)
        if isinstance(record.source_receipt, TransferPendingV1) and (not history or history[-1].receipt != record.source_receipt):
            self.fail("Current pending receipt lacks exact durable source-current audit")
        if isinstance(record.source_receipt, TransferAcceptedV1) and history and (
                record.source_receipt.pending_state_revision != history[-1].receipt.pending_state_revision):
            self.fail("Accepted original omitted/substituted durable pending revision history")
        if record.lifecycle in {"accepted", "rejected"}:
            events = [event for _, event in self._events(record.intent.case_id)
                      if isinstance(event, TransferResolvedV1) and event.transfer_id == transfer_id]
            if (len(events) != 1 or events[0].receipt_hash != fingerprint(record.source_receipt.model_dump(mode="json"))):
                self.fail("Terminal transfer lacks exact durable receipt event")
            event = events[0]
            self._source(event.source_current, event.source_current.as_of, current=True, durable=True)
            if event.ownership != self._project(record):
                self.fail("Terminal ownership event projection mismatch")
            self._confirm(record, event.source_current)
        return record

    def _unused_source(self, source):
        used = set()
        for record in self.rows(source.binding.case_id):
            used.update(record.registration_source.read_entry_ids)
        for _, event in self._events(source.binding.case_id):
            if isinstance(event, (DecisionRecordedV1, DispositionRecordedV1)):
                used.update(event.source.read_entry_ids)
            elif isinstance(event, (TransferResolvedV1, TransferReceiptRecordedV1)):
                used.update(event.source_current.read_entry_ids)
        if used.intersection(source.read_entry_ids):
            self.fail("Distinct ownership event requires fresh accounted source reads")

    def register(self, intent, effect, source, now):
        intent, effect = self.typed(TransferIntent, intent), self.typed(EffectIntent, effect)
        with self.store._transaction():
            self.store._admission.require_imported(intent.case_id)
            if self.is_tagged(intent.transfer_id):
                old = self.record(intent.transfer_id)
                if old.intent != intent or old.effect != effect:
                    self.fail("Immutable registered transfer conflict")
                return old
            if self.db.execute("SELECT 1 FROM transfers WHERE case_id=? AND generation=?", (intent.case_id, intent.binding.generation)).fetchone():
                self.fail("One transfer original per binding/stage forever")
            source, spec, facts = self._source(source, now, transfer=True)
            self._unused_source(source)
            cp = source.checkpoint
            if (cp.stop.requested or cp.ownership_state != "accepted" or source.binding != intent.binding
                    or cp.ownership_epoch != intent.expected_epoch or cp.ownership_state_revision != intent.expected_state_revision
                    or not source.grant.may_initiate_transfer or intent.target_owner not in source.grant.target_owners
                    or not any(edge.origin == cp.phase and edge.target == cp.phase and edge.operation == "transfer_owner"
                               for edge in spec.edges)):
                self.fail("Transfer requires current accepted source grant and saved self edge")
            check_time(cp.budget, now)
            args = TransferArgumentsV1.model_validate(effect.arguments)
            if (effect.expected_revisions.revisions != {key: observation.revision for key, observation in facts.items()}
                    or args.grant_revision != facts["operator.ownership_grant"].revision):
                self.fail("Registered transfer conditional revision vector mismatch")
            record = TransferRecordV1(intent=intent, effect=effect, origin_checkpoint=cp,
                origin_checkpoint_hash=fingerprint(cp.model_dump(mode="json")),
                original_input_hash=fingerprint(self.store.original_request(intent.case_id, intent.binding.generation).model_dump(mode="json")),
                profile_hash=source.profile_hash, process_hash=source.process_hash, policy_hash=source.policy_hash,
                registration_source=source, registered_at=now, lifecycle="prepared", source_receipt=None)
            self.store.prepare(effect)
            if self.store.intent(effect.action_id).state != "prepared":
                self.fail("Transfer original was already entered outside registration")
            self.db.execute("INSERT INTO transfers VALUES(?,?,?,?,?)", (intent.transfer_id, intent.case_id,
                intent.binding.generation, record.model_dump_json(), record.lifecycle))
            event = TransferRegisteredV1(binding=intent.binding, transfer_id=intent.transfer_id,
                original_effect_hash=fingerprint(effect.model_dump(mode="json")), origin_checkpoint_hash=record.origin_checkpoint_hash)
            self.store._write_checkpoint(cp.model_copy(update={"ownership_state": "transfer_pending"}), ownership_event=event)
            return record

    def begin(self, transfer_id, expected_current, now):
        expected_current = self.typed(PhaseCheckpoint, expected_current)
        with self.store._transaction():
            record = self.record(transfer_id)
            self._registry(record.intent.binding, record.registration_source)
            current = self.store.checkpoint(record.intent.case_id)
            intent_record = self.store.intent(record.effect.action_id)
            if (current != expected_current or current.binding != record.intent.binding or current.stop.requested
                    or current.phase != record.origin_checkpoint.phase or current.next_gate != record.origin_checkpoint.next_gate
                    or self.store._versions(current) != self.store._versions(record.origin_checkpoint)
                    or record.lifecycle != "prepared" or intent_record.state != "prepared"):
                self.fail("Registered transfer entry requires exact current original prepared scope")
            if now >= min(record.intent.expires_at, record.registration_source.grant.expires_at):
                raise BudgetExceeded("Registered transfer original grant/deadline expired")
            return self.store._enter_effect(intent_record, current, now)

    def consume(self, decision_id, effect, expected_current, now):
        event = next((event for _, event in self._events(effect.binding.case_id)
                      if isinstance(event, DecisionRecordedV1) and event.submission.decision.decision_id == decision_id), None)
        if event is None:
            self.fail("Unknown durable ownership decision association")
        decision, scope = event.submission.decision, event.submission.effect_scope
        current = self.store.checkpoint(effect.binding.case_id)
        if (current != expected_current or current.stop.requested or current.ownership_state != "accepted"
                or decision.binding != effect.binding or decision.decision != "approve" or scope is None
                or effect.decision_id != decision_id or effect.provider_key != effect.action_id
                or (scope.operation, scope.stage, scope.action_id, scope.argument_fingerprint) !=
                   (effect.operation, effect.stage, effect.action_id, effect.argument_fingerprint)
                or (effect.ownership_state_revision, effect.ownership_epoch) != (decision.state_revision, decision.epoch)
                or (current.ownership_state_revision, current.ownership_epoch) != (decision.state_revision, decision.epoch)
                or self.store._versions(effect) != self.store._versions(event.source.checkpoint)
                or now >= min(decision.expires_at, event.source.grant.expires_at, current.deadline)):
            self.fail("Decision cannot authorize substituted, stale, expired or broader entry")
        if any(isinstance(old, DecisionConsumedV1) and old.decision_id == decision_id
               for _, old in self._events(effect.binding.case_id)):
            self.fail("Decision entry already consumed")
        consume = DecisionConsumedV1(binding=effect.binding, decision_id=decision_id, replay_id=decision.replay_id,
            payload_hash=event.payload_hash, action_id=effect.action_id, argument_fingerprint=effect.argument_fingerprint, consumed_at=now)
        self.store._write_checkpoint(current, ownership_event=consume)

    def _put(self, record):
        self.db.execute("UPDATE transfers SET transfer_json=?,state=? WHERE transfer_id=?",
                        (record.model_dump_json(), record.lifecycle, record.intent.transfer_id))

    def _project(self, record):
        receipt = record.source_receipt
        packet = record.registration_source.packet
        accepted = isinstance(receipt, TransferAcceptedV1) and record.lifecycle == "accepted"
        rejected = isinstance(receipt, TransferRejectedV1) and record.lifecycle == "rejected"
        return HumanOwnership(binding=record.intent.binding,
            owner=receipt.target_owner if accepted else record.intent.expected_owner,
            epoch=receipt.accepted_epoch if accepted else record.intent.expected_epoch,
            state_revision=receipt.accepted_state_revision if accepted else
                receipt.retained_state_revision if rejected else record.intent.expected_state_revision,
            packet_id=packet.packet_id, packet_hash=packet.packet_hash, packet_revision=packet.packet_revision,
            state="accepted" if accepted or rejected else "transfer_pending",
            acceptance_evidence=receipt.acceptance_evidence if accepted else packet.acceptance_evidence,
            pending_evidence=(receipt.evidence_ref if isinstance(receipt, TransferPendingV1) else record.intent.transfer_id)
                            if not accepted and not rejected else None,
            transfer_id=record.intent.transfer_id)

    def human(self, binding):
        binding = self.typed(RequestBinding, binding)
        self.store._assert_binding(binding)
        self.validate_events(binding.case_id)
        records = [record for record in self.rows(binding.case_id) if record.intent.binding == binding]
        if records:
            return self._project(self.record(records[0].intent.transfer_id))
        events = [event for _, event in self._events(binding.case_id) if isinstance(event, (DecisionRecordedV1, DispositionRecordedV1))
                  and event.source.binding == binding]
        if not events:
            self.fail("No source-observed local ownership inventory")
        packet = events[-1].source.packet
        return HumanOwnership(binding=binding, owner=packet.accepted_owner, epoch=packet.accepted_epoch,
            state_revision=packet.accepted_state_revision, packet_id=packet.packet_id,
            packet_hash=packet.packet_hash, packet_revision=packet.packet_revision, state="accepted",
            acceptance_evidence=packet.acceptance_evidence)

    def unknown(self, transfer_id, expected_current):
        expected_current = self.typed(PhaseCheckpoint, expected_current)
        with self.store._transaction():
            record = self.record(transfer_id)
            current = self.store.checkpoint(record.intent.case_id)
            if current != expected_current or current.binding != record.intent.binding:
                self.fail("Unknown original checkpoint CAS mismatch")
            if record.lifecycle in {"accepted", "rejected"}:
                return self._project(record)
            unknown = record.model_copy(update={"lifecycle": "outcome_unknown"})
            self._put(unknown)
            self.store._write_checkpoint(current)
            return self._project(unknown)

    def _entered(self, record):
        if self.store.intent(record.effect.action_id).state == "prepared":
            self.fail("Source receipt requires durably entered exact original")
        lease = self.store.entry("effect:" + record.effect.action_id + ":1")
        if (lease.kind, lease.subject_id, lease.case_id, lease.generation) != (
                "effect", record.effect.action_id, record.intent.case_id, record.intent.binding.generation):
            self.fail("Transfer original lacks exact entered ledger evidence")

    def apply(self, transfer_id, receipt, source_current, expected_current, now):
        if not isinstance(receipt, (TransferPendingV1, TransferAcceptedV1, TransferRejectedV1)):
            self.fail("Expected closed typed source receipt")
        receipt = self.typed(type(receipt), receipt)
        expected_current = self.typed(PhaseCheckpoint, expected_current)
        with self.store._transaction():
            record = self.record(transfer_id)
            self._entered(record)
            source, _, _ = self._source(source_current, now, current=True)
            current = self.store.checkpoint(record.intent.case_id)
            if (current != expected_current or source.checkpoint != current or source.binding != record.intent.binding
                    or (source.profile_hash, source.process_hash, source.policy_hash) !=
                       (record.profile_hash, record.process_hash, record.policy_hash)):
                self.fail("Transfer receipt current/source/CAS mismatch")
            lifecycle = "accepted" if isinstance(receipt, TransferAcceptedV1) else "rejected" if isinstance(receipt, TransferRejectedV1) else "pending"
            result = record.model_copy(update={"source_receipt": receipt, "lifecycle": lifecycle})
            at = receipt.accepted_at if lifecycle == "accepted" else receipt.rejected_at if lifecycle == "rejected" else receipt.pending_at
            if at > source.as_of:
                self.fail("Receipt occurs after current confirmation")
            if record.lifecycle in {"accepted", "rejected"}:
                if record.source_receipt != receipt or record.lifecycle != lifecycle:
                    self.fail("Conflicting terminal ownership evidence")
                if source.ownership != self._project(record):
                    self.fail("Repeated terminal receipt lacks exact current owner confirmation")
                return self._project(record)
            if isinstance(record.source_receipt, TransferPendingV1):
                pending = record.source_receipt
                if isinstance(receipt, TransferPendingV1) and receipt != pending:
                    self.fail("Conflicting source pending original receipt")
                if isinstance(receipt, TransferAcceptedV1) and receipt.pending_state_revision != pending.pending_state_revision:
                    self.fail("Acceptance omitted/substituted observed pending revision")
            projected = self._project(result)
            packet = source.packet
            self._confirm(result, source)
            if lifecycle == "pending" and any(isinstance(event, TransferReceiptRecordedV1)
                    and event.transfer_id == transfer_id and event.receipt == receipt and event.source_current == source
                    for _, event in self._events(record.intent.case_id)):
                return projected
            self._unused_source(source)
            self._put(result)
            if lifecycle in {"accepted", "rejected"}:
                cp = current.model_copy(update={"ownership_state": "accepted", "ownership_epoch": projected.epoch,
                                               "ownership_state_revision": projected.state_revision})
                event = TransferResolvedV1(binding=record.intent.binding, transfer_id=transfer_id,
                    receipt_hash=fingerprint(receipt.model_dump(mode="json")), ownership=projected, source_current=source)
                self.store._write_checkpoint(cp, ownership_event=event)
            else:
                event = TransferReceiptRecordedV1(binding=record.intent.binding, transfer_id=transfer_id, receipt=receipt,
                    receipt_hash=fingerprint(receipt.model_dump(mode="json")), source_current=source)
                self.store._write_checkpoint(current, ownership_event=event)
            return projected

    def _confirm(self, record, source):
        receipt, packet = record.source_receipt, source.packet
        if (source.profile_hash, source.process_hash, source.policy_hash) != (record.profile_hash, record.process_hash, record.policy_hash):
            self.fail("Receipt current source hashes differ from frozen original")
        at = receipt.accepted_at if isinstance(receipt, TransferAcceptedV1) else receipt.rejected_at if isinstance(receipt, TransferRejectedV1) else receipt.pending_at
        if at > source.as_of:
            self.fail("Receipt occurs after current confirmation")
        if isinstance(receipt, TransferAcceptedV1):
            if (source.ownership != self._project(record) or packet.packet_id != receipt.packet.packet_id
                    or packet.packet_hash != receipt.packet.packet_hash or packet.packet_revision != receipt.packet.packet_revision
                    or packet.content_hash != receipt.packet.content_hash
                    or (packet.accepted_owner, packet.accepted_epoch, packet.accepted_state_revision,
                        packet.acceptance_evidence, packet.accepted_at) !=
                       (receipt.target_owner, receipt.accepted_epoch, receipt.accepted_state_revision,
                        receipt.acceptance_evidence, receipt.accepted_at)):
                self.fail("Acceptance requires matching fresh current target packet and owner")
        elif isinstance(receipt, TransferRejectedV1):
            if (source.ownership.owner, source.ownership.epoch, source.ownership.state_revision, source.ownership.state) != (
                    record.intent.expected_owner, record.intent.expected_epoch, receipt.retained_state_revision, "accepted") or packet != receipt.packet:
                self.fail("Rejection lacks fresh retained owner and exact packet")
        else:
            if (source.ownership.owner, source.ownership.epoch, source.ownership.state_revision, source.ownership.state) != (
                    record.intent.expected_owner, record.intent.expected_epoch, receipt.pending_state_revision, "transfer_pending") or packet != receipt.packet:
                self.fail("Pending receipt lacks current source pending predecessor")

    def _current_record_scope(self, payload, source, now):
        source, _, _ = self._source(source, now)
        cp, packet = source.checkpoint, source.packet
        if (cp.stop.requested or cp.ownership_state != "accepted"
                or (cp.ownership_state_revision, cp.ownership_epoch) != (packet.accepted_state_revision, packet.accepted_epoch)
                or payload.binding != source.binding or payload.owner != source.grant.actor_id
                or payload.actor_id != source.grant.actor_id
                or (payload.packet_id, payload.packet_hash, payload.packet_revision, payload.owner, payload.epoch, payload.state_revision) !=
                   (packet.packet_id, packet.packet_hash, packet.packet_revision, packet.accepted_owner,
                    packet.accepted_epoch, packet.accepted_state_revision)
                or now >= payload.expires_at or payload.expires_at > min(source.grant.expires_at, cp.deadline)):
            self.fail("Operator record requires exact fresh accepted source owner/packet/grant interval")
        check_time(cp.budget, now)
        return source

    def _replay(self, case_id, identifier, replay_id, payload, *, decision):
        matches = []
        for _, event in self._events(case_id):
            if isinstance(event, DecisionRecordedV1):
                value, ident = event.submission, event.submission.decision.decision_id
                replay = value.decision.replay_id
                same_kind = decision
            elif isinstance(event, DispositionRecordedV1):
                value, ident = event.disposition, event.disposition.record_id
                replay = value.replay_id
                same_kind = not decision
            else:
                continue
            if ident == identifier or replay == replay_id:
                if not same_kind or ident != identifier or replay != replay_id or value != payload:
                    self.fail("Immutable operator record/replay collision")
                matches.append(value)
        if len(matches) > 1:
            self.fail("Duplicate durable operator record")
        return matches[0] if matches else None

    def decision(self, submission, source, now):
        submission = self.typed(OperatorDecisionSubmissionV1, submission)
        with self.store._transaction():
            value = submission.decision
            source = self._current_record_scope(value, source, now)
            if submission.content_hash != source.packet.content_hash:
                self.fail("Operator decision content digest mismatch")
            if value.decision == "approve":
                if submission.effect_scope.operation not in source.grant.decision_operations:
                    self.fail("Source grant does not permit decision operation")
            elif not source.grant.may_record_nonaction_decision:
                self.fail("Source grant does not permit nonaction decisions")
            old = self._replay(value.binding.case_id, value.decision_id, value.replay_id, submission, decision=True)
            if old is not None:
                return old
            self._unused_source(source)
            event = DecisionRecordedV1(submission=submission, payload_hash=fingerprint(submission.model_dump(mode="json")),
                source=source, recorded_at=now)
            self.store._write_checkpoint(source.checkpoint, ownership_event=event)
            return submission

    def decision_record(self, binding, decision_id):
        self.store._assert_binding(binding)
        if self.store.original_request(binding.case_id, binding.generation) is None:
            self.fail("Decision inventory requires immutable original request")
        self.validate_events(binding.case_id)
        matches = [event.submission for _, event in self._events(binding.case_id)
                   if isinstance(event, DecisionRecordedV1)
                   and event.submission.decision.binding == binding
                   and event.submission.decision.decision_id == decision_id]
        if len(matches) != 1:
            self.fail("No unique complete recorded decision in exact binding")
        return self.typed(OperatorDecisionSubmissionV1, matches[0])

    def disposition(self, disposition, source, now):
        value = self.typed(OperatorDispositionV1, disposition)
        with self.store._transaction():
            source = self._current_record_scope(value, source, now)
            if value.content_hash != source.packet.content_hash or value.disposition not in source.grant.dispositions:
                self.fail("Source grant does not permit this exact content-bound disposition")
            old = self._replay(value.binding.case_id, value.record_id, value.replay_id, value, decision=False)
            if old is not None:
                return old
            self._unused_source(source)
            event = DispositionRecordedV1(disposition=value, payload_hash=fingerprint(value.model_dump(mode="json")),
                source=source, recorded_at=now)
            self.store._write_checkpoint(source.checkpoint, ownership_event=event)
            return value

    def validate_events(self, case_id=None):
        # Full audit validation uses existing original getters, which in turn
        # read the current checkpoint. Their nested reads share this validation
        # pass rather than recursively starting another scan.
        if getattr(self, "_validating_events", False):
            return
        self._validating_events = True
        try:
            self._validate_events(case_id)
        finally:
            self._validating_events = False

    def _validate_events(self, case_id):
        transfers = {record.intent.transfer_id: record for record in self.rows(case_id)}
        used_reads = set()
        for transfer in transfers.values():
            scope = {(transfer.intent.case_id, item) for item in transfer.registration_source.read_entry_ids}
            if scope.intersection(used_reads):
                self.fail("Distinct transfers reuse ownership source reads")
            used_reads.update(scope)
        for record in transfers.values():
            self.record(record.intent.transfer_id)
        recorded, consumed, replays = {}, set(), {}
        for case_id, event in self._events(case_id):
            snapshot = (event.source if isinstance(event, (DecisionRecordedV1, DispositionRecordedV1)) else
                        event.source_current if isinstance(event, (TransferResolvedV1, TransferReceiptRecordedV1)) else None)
            if snapshot is not None:
                scope = {(case_id, item) for item in snapshot.read_entry_ids}
                if scope.intersection(used_reads):
                    self.fail("Distinct ownership audit events reuse source read accounting")
                used_reads.update(scope)
            if isinstance(event, (DecisionRecordedV1, DispositionRecordedV1)):
                value = event.submission.decision if isinstance(event, DecisionRecordedV1) else event.disposition
                ident = value.decision_id if isinstance(event, DecisionRecordedV1) else value.record_id
                if value.binding.case_id != case_id or (case_id, ident) in recorded or (case_id, value.replay_id) in replays:
                    self.fail("Durable operator record/replay duplicate or case substitution")
                self.store._assert_binding(value.binding)
                self._source(event.source, event.recorded_at, durable=True)
                self._validate_recorded_scope(event)
                if not self.store._audited_checkpoint_hash(case_id, fingerprint(event.source.checkpoint.model_dump(mode="json"))):
                    self.fail("Operator record lacks exact accounted origin checkpoint")
                recorded[(case_id, ident)] = event
                replays[(case_id, value.replay_id)] = ident
            elif isinstance(event, DecisionConsumedV1):
                old = recorded.get((case_id, event.decision_id))
                if not isinstance(old, DecisionRecordedV1) or (case_id, event.decision_id) in consumed:
                    self.fail("Decision consumption lacks unique original recording")
                intent = self.store.intent(event.action_id)
                value, scope = old.submission.decision, old.submission.effect_scope
                if (scope is None or intent.state == "prepared" or intent.intent.decision_id != event.decision_id
                        or event.binding != value.binding or event.replay_id != value.replay_id
                        or event.payload_hash != old.payload_hash or event.action_id != scope.action_id
                        or event.argument_fingerprint != scope.argument_fingerprint
                        or event.consumed_at >= min(value.expires_at, old.source.grant.expires_at)):
                    self.fail("Decision consumption immutable original linkage mismatch")
                lease = self.store.entry("effect:" + event.action_id + ":1")
                if lease.started_at != event.consumed_at or lease.subject_id != event.action_id:
                    self.fail("Decision consumption differs from same-transaction entry ledger")
                consumed.add((case_id, event.decision_id))
            elif isinstance(event, (TransferRegisteredV1, TransferResolvedV1, TransferReceiptRecordedV1)):
                original = transfers.get(event.transfer_id)
                if original is None or event.binding.case_id != case_id or event.binding != original.intent.binding:
                    self.fail("Ownership transfer audit lacks its exact durable original binding")
                if isinstance(event, TransferRegisteredV1):
                    if (event.original_effect_hash != fingerprint(original.effect.model_dump(mode="json"))
                            or event.origin_checkpoint_hash != original.origin_checkpoint_hash):
                        self.fail("Ownership registration audit differs from immutable original hashes")
                elif isinstance(event, TransferResolvedV1):
                    if (original.lifecycle not in {"accepted", "rejected"}
                            or event.receipt_hash != fingerprint(original.source_receipt.model_dump(mode="json"))
                            or event.ownership != self._project(original)):
                        self.fail("Ownership resolution audit differs from exact terminal original")
                    self._source(event.source_current, event.source_current.as_of, current=True, durable=True)
                    self._confirm(original, event.source_current)
                else:
                    pending = original.model_copy(update={"lifecycle": "pending", "source_receipt": event.receipt})
                    self._entered(original)
                    self._source(event.source_current, event.source_current.as_of, current=True, durable=True)
                    self._confirm(pending, event.source_current)
            elif isinstance(event, OwnerObservedV1):
                # Task8A has no authenticated initial-owner producer/public
                # recording API. A typed injected observation cannot activate it.
                self.fail("Initial owner-observed audit producer unavailable in storage stage")
            else:
                self.fail("Unsupported ownership audit event")

    def _validate_recorded_scope(self, event):
        payload = event.submission.decision if isinstance(event, DecisionRecordedV1) else event.disposition
        source, packet, now = event.source, event.source.packet, event.recorded_at
        if ((payload.packet_id, payload.packet_hash, payload.packet_revision, payload.owner, payload.epoch, payload.state_revision,
             payload.actor_id) != (packet.packet_id, packet.packet_hash, packet.packet_revision, packet.accepted_owner,
                                  packet.accepted_epoch, packet.accepted_state_revision, source.grant.actor_id)
                or source.checkpoint.stop.requested or source.checkpoint.ownership_state != "accepted"
                or (source.checkpoint.ownership_state_revision, source.checkpoint.ownership_epoch) !=
                   (packet.accepted_state_revision, packet.accepted_epoch)
                or not source.grant.issued_at <= now < payload.expires_at <= min(source.grant.expires_at, source.checkpoint.deadline)):
            self.fail("Durable operator recording source/current/expiry linkage mismatch")
        if isinstance(event, DecisionRecordedV1):
            if event.submission.content_hash != packet.content_hash or (
                    payload.decision == "approve" and event.submission.effect_scope.operation not in source.grant.decision_operations) or (
                    payload.decision != "approve" and not source.grant.may_record_nonaction_decision):
                self.fail("Durable decision source scope mismatch")
        elif payload.content_hash != packet.content_hash or payload.disposition not in source.grant.dispositions:
            self.fail("Durable disposition source scope mismatch")
