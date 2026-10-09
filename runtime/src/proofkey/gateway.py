"""One durable, authenticated physical-effect path for all six ports."""
from datetime import timedelta
from contextlib import contextmanager, nullcontext
from threading import get_ident
import math
from uuid import uuid4
from dataclasses import dataclass

from pydantic import TypeAdapter

from .contracts import (ActionProposal, AuthContext, AuthorityReadback, CanonicalRequest, EffectIntent, Hash, Identifier,
                        NonnegativeInt, OwnerState, PhaseCheckpoint, ReadRequest, RequestBinding,
                        ReadTarget, Revision, RevisionVector, StopState, VerificationResult)
from .identity import fingerprint, request_fingerprint, stable_action_id
from .journal import JournalFailure
from .policy import (BUSINESS, GateDenied, IDENTITY_FIELDS, OWNER_FIELDS, PolicyGate,
                     qualified_observations, required_fields)
from .verifier import expected_facts, verify
from .packet_contracts import (packet_enabled, packet_postcondition, validate_packet_arguments,
                              validate_packet_policy, validate_packet_scope)
from .packets import PacketService, PacketSources
from .wait_contracts import WaitRecordV1
from .execution_consumer import ExecutionTiming
from .ownership_contracts import OwnershipPacketV1, OwnershipGrantV1, ownership_enabled
from .ownership_gateway import OwnershipGateway


@dataclass(frozen=True)
class _LeasedRead:
    reply: AuthorityReadback
    entry_id: str

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


class ActionGateway(OwnershipGateway):
    def __init__(self, profile, bundle, store, clock, auth=None):
        self.profile, self.bundle, self.store, self.clock, self.auth = profile, bundle, store, clock, auth
        self.gate = PolicyGate(profile)
        self._owner_thread = get_ident()
        self._execution_active = False
        self._timing = None

    @contextmanager
    def execution_scope(self, execution=None):
        """One creator-owned host cap, installed before caller authentication."""
        if get_ident() != self._owner_thread or self._execution_active:
            raise GateDenied("scope_denied")
        timing = ExecutionTiming(self.clock, execution)
        previous_timing, previous_auth = self._timing, self.auth
        self._execution_active = True
        try:
            with self.store.execution_scope(execution, self.clock) if execution is not None else nullcontext():
                self._timing = timing
                yield timing
        finally:
            self._timing = previous_timing
            if execution is not None:
                self.auth = previous_auth
            self._execution_active = False

    @staticmethod
    def _denied():
        return VerificationResult(status="rejected", reason="scope_denied")

    def _authenticated(self):
        if not isinstance(self.auth, AuthContext) or not callable(getattr(self.clock, "wait", None)):
            raise GateDenied("scope_denied")

    @contextmanager
    def _auth_scope(self, auth):
        if not isinstance(auth, AuthContext):
            raise GateDenied("scope_denied")
        previous = self.auth
        self.auth = AuthContext.model_validate(auth.model_dump())
        try:
            self._authenticated()
            yield
        finally:
            self.auth = previous

    def _pace(self, deadline):
        self._authenticated()
        limits = [c.shared_limits.rate_per_second for c in self.profile.capabilities.values()
                  if c.shared_limits.account_id == self.profile.capabilities["read_authority"].shared_limits.account_id]
        if not limits or any(rate is None or not math.isfinite(rate) or rate <= 0 for rate in limits):
            raise GateDenied("scope_denied")
        delay = 1.0 / min(limits) + 0.000001
        now, cutoff = (self._timing.window(deadline) if self._timing is not None
                       else (self.clock.now(), deadline))
        if now + timedelta(seconds=delay) >= cutoff:
            raise GateDenied("scope_denied")
        self.clock.wait(delay)
        after, cutoff = (self._timing.window(deadline) if self._timing is not None
                         else (self.clock.now(), deadline))
        if after < now or after >= cutoff:
            raise GateDenied("scope_denied")

    def _transport_deadline(self, deadline, lease, anchor):
        if self._timing is None or self._timing.execution is None:
            return deadline
        try:
            return self._timing._transport_deadline(deadline, lease, anchor)
        except ValueError:
            raise GateDenied("scope_denied") from None

    def _settle(self, lease, completed, admission=False, anchor=None):
        if anchor is not None:
            now, cutoff = self._timing.window(lease.deadline)
            elapsed = self._timing.elapsed_since(anchor)
        else:
            elapsed = (self.clock.now() - lease.started_at).total_seconds()
        if elapsed < 0 or not math.isfinite(elapsed):
            raise GateDenied("scope_denied")
        if elapsed > lease.reserved_seconds:
            finish = self.store.finish_admission_read if admission else self.store.finish_entry
            finish(lease.entry_id, elapsed)
            raise GateDenied("scope_denied")
        if anchor is not None and now >= cutoff:
            raise GateDenied("scope_denied")
        if completed:
            finish = self.store.finish_admission_read if admission else self.store.finish_entry
            finish(lease.entry_id, elapsed)
        if self.clock.now() >= lease.deadline:
            raise GateDenied("scope_denied")

    def _read(self, scope, target, port, method, *, purpose, action_id=None, attempt_id=None, deadline=None, control=False, validate=None):
        return self._leased_read(scope, target, port, method, purpose=purpose, action_id=action_id,
            attempt_id=attempt_id, deadline=deadline, control=control, validate=validate).reply

    def _leased_read(self, scope, target, port, method, *, purpose, action_id=None, attempt_id=None, deadline=None, control=False, validate=None):
        limit = deadline or self.store.checkpoint(scope.case_id).deadline
        self._pace(limit)
        anchor = self._timing.monotonic_anchor() if self._timing is not None else None
        lease = (self.store.begin_control_read(scope, target, purpose, self.clock.now()) if control else
                 self.store.begin_admission_read(attempt_id, self.clock.now()) if attempt_id else
                 self.store.begin_read(scope.case_id, self.clock.now(), action_id=action_id))
        request = ReadRequest(case_id=scope.case_id, object_id=scope.object_id, caller_id=self.auth.caller_id,
            proof_reference=self.auth.proof_reference, purpose=purpose,
            deadline=self._transport_deadline(min(limit, lease.deadline), lease, anchor), target=target)
        try:
            transport = getattr(getattr(self.bundle, port), method)
        except Exception:
            self._settle(lease, False, admission=attempt_id is not None, anchor=anchor)
            raise GateDenied("scope_denied") from None
        request = request.model_copy(update={"deadline": self._transport_deadline(request.deadline, lease, anchor)})
        try:
            reply = transport(request)
            reply = AuthorityReadback.model_validate(reply.model_dump())
            if (self.clock.now() >= request.deadline or reply.as_of < lease.started_at or reply.as_of > self.clock.now()
                    or any(o.observed_at < lease.started_at or o.observed_at > reply.as_of for o in reply.observations)):
                raise GateDenied("scope_denied")
            try:
                indexed = qualified_observations(self.profile, scope.object_id, reply.observations)
                valid_observations = True
            except GateDenied:
                if target.kind == "authority_facts":
                    raise
                # The independent verifier records malformed original identity
                # as conflict; its reservation is retained rather than refunded.
                indexed, valid_observations = {}, False
            scoped = reply.object_id == scope.object_id
            rejection = (scoped and reply.operation == method and reply.stage == "scope_rejected"
                         and not reply.observations and reply.action_id is None and reply.fingerprint is None)
            completed = False
            if target.kind == "authority_facts":
                expected = {target.authority + "." + fact for fact in target.facts}
                if not rejection and (not scoped or reply.operation != method or reply.stage != "observed"
                        or not reply.evidence_refs or set(indexed) != expected):
                    raise GateDenied("scope_denied")
                completed = rejection or (set(indexed) == expected and bool(reply.evidence_refs))
            else:
                # Invalid original evidence can still produce an honest conflict,
                # but cannot refund a source read reservation.
                completed = rejection or (scoped and valid_observations and bool(reply.evidence_refs)
                    and reply.stage not in {"unknown", "unavailable"}
                    and reply.operation == target.operation and reply.action_id == target.action_id
                    and reply.fingerprint == target.fingerprint)
                if completed and not rejection:
                    original = self.store.intent(action_id).intent
                    completed = verify(original, reply, profile=self.profile).status in {"verified", "rejected", "pending"}
            if validate is not None and not rejection:
                validate(reply)
            if not rejection and target.kind == "authority_facts" and ownership_enabled(self.profile):
                registered = {}
                for key, schema in (("operator.ownership_packet", OwnershipPacketV1),
                                    ("operator.ownership_grant", OwnershipGrantV1)):
                    if key in indexed:
                        item = indexed[key]
                        value = schema.model_validate(item.value)
                        registered[key] = value
                        if value.binding != scope or value.simulated is not True:
                            raise GateDenied("scope_denied")
                        if key.endswith("packet") and value.accepted_at > item.observed_at:
                            raise GateDenied("scope_denied")
                        if key.endswith("grant") and (value.actor_id != self.auth.caller_id
                                or value.evidence_ref != item.evidence_ref
                                or not value.issued_at <= self.clock.now() < value.expires_at):
                            raise GateDenied("scope_denied")
                packet = registered.get("operator.ownership_packet")
                grant = registered.get("operator.ownership_grant")
                if packet is not None:
                    for key, field, schema in (("operator.packet_hash", "packet_hash", Hash),
                                               ("operator.packet_revision", "packet_revision", Revision)):
                        if key in indexed:
                            actual = TypeAdapter(schema).validate_python(indexed[key].value, strict=True)
                            if actual != getattr(packet, field):
                                raise GateDenied("scope_denied")
                if packet is not None and grant is not None and (grant.packet_id, grant.packet_hash,
                        grant.packet_revision, grant.content_hash, grant.owner, grant.epoch, grant.state_revision) != (
                        packet.packet_id, packet.packet_hash, packet.packet_revision, packet.content_hash,
                        packet.accepted_owner, packet.accepted_epoch, packet.accepted_state_revision):
                    raise GateDenied("scope_denied")
        except Exception:
            self._settle(lease, False, admission=attempt_id is not None, anchor=anchor)
            raise GateDenied("scope_denied") from None
        self._settle(lease, completed, admission=attempt_id is not None, anchor=anchor)
        return _LeasedRead(reply=reply, entry_id=lease.entry_id)

    def _facts(self, scope, fields, *, attempt_id=None, deadline=None, purpose=None, validators=None):
        observations = []
        for authority, (port, method) in _AUTHORITY_READS.items():
            facts = sorted(key.partition(".")[2] for key in fields if key.partition(".")[0] == authority)
            if not facts:
                continue
            target = ReadTarget(kind="authority_facts", authority=authority, facts=facts)
            reply = self._read(scope, target, port, method, purpose=purpose or ("bind_request" if attempt_id else "material_authority"),
                               attempt_id=attempt_id, deadline=deadline,
                               validate=(validators or {}).get(authority))
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
        checkpoint = self._active(intent.binding.case_id, intent.binding, intent)
        dynamic = intent.operation == "enqueue_handoff" and packet_enabled(self.profile)
        return self._facts(intent.binding, required_fields(self.profile, intent.operation) | OWNER_FIELDS,
                           deadline=intent.deadline, purpose=self._material_purpose(intent.operation),
                           validators=self._source_validators(intent.binding, checkpoint, packet=True) if dynamic else None)

    def _material_purpose(self, operation):
        return "operator_packet" if operation == "enqueue_handoff" and packet_enabled(self.profile) else "material_authority"

    def read_packet_sources(self, binding, auth, *, include_wait_context=False):
        """Host-only fresh material/catalog scope, read with individually paced leases."""
        with self._auth_scope(auth):
            self._configured_original(binding)
            checkpoint = self._active(binding.case_id, binding)
            if not packet_enabled(self.profile) or self.auth.caller_id != binding.principal_id:
                raise GateDenied("scope_denied")
            fields = required_fields(self.profile, "enqueue_handoff") | OWNER_FIELDS
            if type(include_wait_context) is not bool:
                raise GateDenied("scope_denied")
            if include_wait_context:
                fields |= {"case.question_revision"}
            observations = self._facts(binding, fields, purpose="operator_packet",
                validators=self._source_validators(binding, checkpoint, packet=True))
            values = {o.authority + "." + o.fact: o.value for o in observations}
            self._current_identity(binding, values)
            if (values["customer.consent_revision"] != binding.consent_revision
                    or values["ownership.owner"] != self.auth.caller_id
                    or values["ownership.state"] != checkpoint.ownership_state
                    or values["ownership.state_revision"] != checkpoint.ownership_state_revision
                    or values["ownership.epoch"] != checkpoint.ownership_epoch
                    or values["policy.version"] != checkpoint.policy_version):
                raise GateDenied("scope_denied")
            catalog, access = validate_packet_scope(values["operator.packet_catalog"], values["operator.packet_access"],
                case_id=binding.case_id, object_id=binding.object_id, sender=binding.principal_id,
                recipient=values["operator.recipient"], now=self.clock.now())
            refreshed = self._active(binding.case_id, binding)
            if include_wait_context and refreshed.model_copy(update={"budget": checkpoint.budget}) != checkpoint:
                raise GateDenied("scope_denied")
            return PacketSources(binding, observations, catalog, access, fingerprint(refreshed.model_dump(mode="json")))

    @staticmethod
    def _packet_sources_hash(sources):
        return fingerprint({"binding": sources.binding.model_dump(mode="json"),
            "observations": [o.model_dump(mode="json") for o in sources.observations],
            "catalog": sources.catalog.model_dump(mode="json"), "access": sources.access.model_dump(mode="json"),
            "checkpoint_hash": sources.checkpoint_hash})

    def _operator_wait(self, binding, intent=None, sources=None):
        question_id = "question:" + stable_action_id(binding, "enqueue_handoff", "enqueue")
        if self.store.wait(question_id) is None:
            return None
        record = WaitRecordV1.model_validate(self.store.load_wait_record(question_id).model_dump())
        checkpoint, original = self._configured_original(binding)
        saved = record.communication_intent
        origin = record.origin_checkpoint
        if (saved is None or record.lifecycle != "pending" or record.wait.binding != binding
                or record.profile_hash != self.profile.release_hash or record.policy_hash != self.profile.policy_hash
                or record.process != self.profile.processes[original.kind]
                or self.store.generation_stop(binding).requested or checkpoint.stop.requested
                or self.clock.now() >= record.wait.expires_at
                or checkpoint.model_copy(update={"budget": origin.budget, "observations": origin.observations}) != origin
                or (intent is not None and intent != saved)):
            raise GateDenied("scope_denied")
        content = validate_packet_arguments(saved.arguments, binding=binding)
        validate_packet_policy(content, self.profile, process_version=checkpoint.process_version,
                               policy_version=checkpoint.policy_version)
        if self.clock.now() >= content.expires_at:
            raise GateDenied("scope_denied")
        if sources is not None:
            current = qualified_observations(self.profile, binding.object_id, sources.observations)
            previous = qualified_observations(self.profile, binding.object_id, origin.observations)
            if (current["case.question_revision"].value != previous["case.question_revision"].value
                    or current["case.question_revision"].revision != previous["case.question_revision"].revision
                    or current["ownership.owner"].value != record.owner_id):
                raise GateDenied("scope_denied")
        return record

    def _before_packet_prepare(self, intent, sources, before_prepare):
        checkpoint = self._active(intent.binding.case_id, intent.binding, intent)
        if fingerprint(checkpoint.model_dump(mode="json")) != sources.checkpoint_hash:
            raise GateDenied("scope_denied")
        original = self.store.original_request(intent.binding.case_id, intent.binding.generation)
        proposal = ActionProposal(operation=intent.operation, stage=intent.stage, arguments=intent.arguments, evidence_refs=[])
        if not self.gate.evaluate(original, proposal, sources.observations, checkpoint,
                journal_predecessor=self._service_predecessor(intent.binding, intent.operation, checkpoint.phase)).allowed:
            raise GateDenied("scope_denied")
        current = qualified_observations(self.profile, intent.binding.object_id, sources.observations)
        if any(key not in current or intent.expected_revisions.revisions.get(key) != current[key].revision
               for key in required_fields(self.profile, intent.operation)):
            raise GateDenied("scope_denied")
        # Detached immutable inputs protect the actual transport payload even
        # against a host callback bypassing Python's normal frozen setters.
        detached_intent = EffectIntent.model_validate(intent.model_dump())
        detached_sources = PacketSources(RequestBinding.model_validate(sources.binding.model_dump()),
            tuple(type(o).model_validate(o.model_dump()) for o in sources.observations),
            type(sources.catalog).model_validate(sources.catalog.model_dump()),
            type(sources.access).model_validate(sources.access.model_dump()), sources.checkpoint_hash)
        detached_checkpoint = PhaseCheckpoint.model_validate(checkpoint.model_dump())
        intent_hash = fingerprint(detached_intent.model_dump(mode="json"))
        source_hash = self._packet_sources_hash(detached_sources)
        before_prepare(detached_intent, detached_sources, detached_checkpoint)
        if (fingerprint(detached_intent.model_dump(mode="json")) != intent_hash
                or self._packet_sources_hash(detached_sources) != source_hash
                or detached_checkpoint != checkpoint):
            raise GateDenied("scope_denied")
        current = self._active(intent.binding.case_id, intent.binding, intent)
        allowed = checkpoint.model_copy(update={"observations": list(sources.observations)})
        if current != checkpoint and current != allowed:
            raise GateDenied("scope_denied")
        validate_packet_scope(sources.catalog, sources.access, case_id=intent.binding.case_id,
            object_id=intent.binding.object_id, sender=intent.binding.principal_id,
            recipient=intent.arguments["recipient"], now=self.clock.now())
        # An envelope, if created, must retain this exact pre-send intent.
        self._operator_wait(intent.binding, intent, sources)

    def enqueue_operator_packet(self, case_id, disposition, *, before_prepare=None):
        """Owned v1.3 construction or exact immutable original recovery."""
        intent = None
        try:
            self._authenticated()
            if not packet_enabled(self.profile):
                raise GateDenied("scope_denied")
            binding = self.store.checkpoint(case_id).binding
            records = [record for record in self.store.intents(case_id)
                       if record.intent.binding == binding and record.intent.operation == "enqueue_handoff"]
            if records:
                if len(records) != 1:
                    return VerificationResult(status="conflict", reason="immutable_intent_conflict")
                record, intent = records[0], records[0].intent
                if record.state != "prepared":
                    return self.reconcile(intent.action_id)
                saved_wait = self._operator_wait(binding, intent)
                if before_prepare is not None and saved_wait is None:
                    raise GateDenied("scope_denied")
                sources = (self.read_packet_sources(binding, self.auth, include_wait_context=True)
                           if before_prepare is not None or saved_wait is not None
                           else self.read_packet_sources(binding, self.auth))
                if fingerprint(self.store.checkpoint(case_id).model_dump(mode="json")) != sources.checkpoint_hash:
                    raise GateDenied("scope_denied")
                if saved_wait is not None:
                    self._operator_wait(binding, intent, sources)
                return self._run(intent, sources.observations)
            self._active(case_id, binding)
            if before_prepare is not None and not callable(before_prepare):
                raise GateDenied("scope_denied")
            saved_wait = self._operator_wait(binding)
            if saved_wait is not None:
                intent = saved_wait.communication_intent
                sources = self.read_packet_sources(binding, self.auth, include_wait_context=True)
                self._operator_wait(binding, intent, sources)
                if fingerprint(self.store.checkpoint(case_id).model_dump(mode="json")) != sources.checkpoint_hash:
                    raise GateDenied("scope_denied")
                if before_prepare is not None:
                    self._before_packet_prepare(intent, sources, before_prepare)
                return self._run(intent, sources.observations)
            snapshots = []
            def read_owned(current, auth):
                snapshot = (self.read_packet_sources(current, auth, include_wait_context=True)
                            if before_prepare is not None else self.read_packet_sources(current, auth))
                snapshots.append(snapshot)
                return snapshot
            prepared = PacketService(self.profile, self.store, read_owned, self.clock).prepare(case_id, self.auth, disposition)
            checkpoint = self._active(case_id, binding)
            if fingerprint(checkpoint.model_dump(mode="json")) != prepared.checkpoint_hash or len(snapshots) != 1:
                raise GateDenied("scope_denied")
            content = prepared.content.model_dump(mode="json")
            args = {"packet_id": prepared.packet.packet_id, "packet_revision": prepared.packet.packet_revision,
                "packet_hash": prepared.packet.packet_hash, "recipient": prepared.content.source.recipient,
                "packet_contract": "packet-content-v1", "content_hash": prepared.content_hash, "content": content}
            indexed = qualified_observations(self.profile, binding.object_id, snapshots[0].observations)
            fields = required_fields(self.profile, "enqueue_handoff")
            action_id = stable_action_id(binding, "enqueue_handoff", "enqueue")
            intent = EffectIntent(binding=binding, operation="enqueue_handoff", stage="enqueue", action_id=action_id,
                provider_key=action_id, arguments=args, argument_fingerprint=fingerprint(args),
                profile_version=checkpoint.profile_version, process_version=checkpoint.process_version,
                policy_version=checkpoint.policy_version, consent_revision=binding.consent_revision,
                expected_revisions=RevisionVector(revisions={key: indexed[key].revision for key in fields}),
                postcondition=packet_postcondition(args), deadline=checkpoint.deadline,
                ownership_state_revision=indexed["ownership.state_revision"].value, ownership_epoch=indexed["ownership.epoch"].value)
            if before_prepare is not None:
                self._before_packet_prepare(intent, snapshots[0], before_prepare)
            return self._run(intent, snapshots[0].observations)
        except Exception:
            if intent is not None:
                try:
                    if self.store.intent(intent.action_id).state != "prepared":
                        return VerificationResult(status="outcome_unknown", reason="entry_unresolved")
                except JournalFailure:
                    pass
            return self._denied()

    def _configured_original(self, binding):
        checkpoint = self.store.checkpoint(binding.case_id)
        original = self.store.original_request(binding.case_id, binding.generation)
        spec = self.profile.processes.get(original.kind) if original is not None else None
        if (checkpoint.binding != binding or original is None or spec is None
                or checkpoint.profile_version != self.profile.version or checkpoint.process_version != spec.version
                or request_fingerprint(original) != binding.fingerprint):
            raise GateDenied("scope_denied")
        return checkpoint, original

    @staticmethod
    def _current_identity(binding, values):
        source = values.get("case.binding")
        fields = ("case_id", "object_id", "principal_id", "request_id")
        if (not isinstance(source, dict) or any(source.get(key) != getattr(binding, key) for key in fields)
                or values.get("case.authorization") != "verified"
                or values.get("case.request_revision") != binding.request_revision
                or values.get("case.generation") != binding.generation):
            raise GateDenied("scope_denied")

    def _source_validators(self, binding, checkpoint, *, recipient_key=None, packet=False):
        """Validate each complete physical authority reply before settling its lease."""
        def values(read):
            return {o.authority + "." + o.fact: o.value for o in read.observations}
        def case(read):
            current = values(read)
            self._current_identity(binding, current)
            if "case.completeness" in current and (not isinstance(current["case.completeness"], str)
                    or not current["case.completeness"].strip()):
                raise GateDenied("scope_denied")
            if "case.question_revision" in current and (not isinstance(current["case.question_revision"], str)
                    or not current["case.question_revision"].strip()):
                raise GateDenied("scope_denied")
            if packet and "case.question_revision" in current:
                TypeAdapter(Revision).validate_python(current["case.question_revision"], strict=True)
        def customer(read):
            if values(read)["customer.consent_revision"] != binding.consent_revision:
                raise GateDenied("scope_denied")
        def owner(read):
            current = values(read)
            if packet:
                for key, schema in (("ownership.owner", Identifier), ("ownership.state", OwnerState),
                                    ("ownership.state_revision", Revision), ("ownership.epoch", NonnegativeInt)):
                    TypeAdapter(schema).validate_python(current[key], strict=True)
            if (current["ownership.state"] != checkpoint.ownership_state
                    or current["ownership.state_revision"] != checkpoint.ownership_state_revision
                    or current["ownership.epoch"] != checkpoint.ownership_epoch
                    or packet and current["ownership.owner"] != self.auth.caller_id):
                raise GateDenied("scope_denied")
        def policy(read):
            if values(read)["policy.version"] != checkpoint.policy_version:
                raise GateDenied("scope_denied")
        def recipient(read):
            if values(read)[recipient_key] != self.auth.caller_id:
                raise GateDenied("scope_denied")
        def packet_scope(read):
            current = values(read)
            for key, schema in (("operator.packet_hash", Hash), ("operator.packet_revision", Revision),
                                ("operator.recipient", Identifier)):
                TypeAdapter(schema).validate_python(current[key], strict=True)
            validate_packet_scope(current["operator.packet_catalog"], current["operator.packet_access"],
                case_id=binding.case_id, object_id=binding.object_id, sender=binding.principal_id,
                recipient=current["operator.recipient"], now=self.clock.now())
        validators = {"case": case, "customer": customer, "ownership": owner}
        if packet:
            validators.update({"operator": packet_scope, "policy": policy})
        elif recipient_key is not None:
            validators[recipient_key.partition(".")[0]] = recipient
        return validators

    def authenticate_control(self, binding, auth, *, purpose):
        """Fresh current initiator control; returns checkpoint AFTER read accounting."""
        with self._auth_scope(auth):
            binding = RequestBinding.model_validate(binding.model_dump())
            self._configured_original(binding)
            if purpose not in {"stop", "recorded_state"} or self.auth.caller_id != binding.principal_id:
                raise GateDenied("scope_denied")
            target = ReadTarget(kind="authority_facts", authority="case",
                facts=["authorization", "binding", "generation", "request_revision"])
            read = self._read(binding, target, "case", "read_case", purpose=purpose, control=True,
                validate=lambda read: self._current_identity(binding, {o.authority + "." + o.fact: o.value for o in read.observations}))
            if read.stage != "observed":
                raise GateDenied("scope_denied")
            self._current_identity(binding, {o.authority + "." + o.fact: o.value for o in read.observations})
            return self._configured_original(binding)[0]

    def read_reply_sources(self, binding, auth, *, recipient_role):
        """Active facts-only actor ACL/metadata; observations never constitute consent."""
        with self._auth_scope(auth):
            checkpoint, _ = self._configured_original(binding)
            if checkpoint.stop.requested or self.clock.now() >= checkpoint.deadline:
                raise GateDenied("scope_denied")
            if recipient_role not in {"customer", "operator"}:
                raise GateDenied("scope_denied")
            recipient_key = "messaging.recipient" if recipient_role == "customer" else "operator.recipient"
            fields = IDENTITY_FIELDS | OWNER_FIELDS | {"case.question_revision", "case.completeness", recipient_key}
            observations = self._facts(binding, fields, purpose="reply",
                validators=self._source_validators(binding, checkpoint, recipient_key=recipient_key))
            values = {o.authority + "." + o.fact: o.value for o in observations}
            self._current_identity(binding, values)
            if (values[recipient_key] != self.auth.caller_id or values["customer.consent_revision"] != binding.consent_revision
                    or values["ownership.state"] != checkpoint.ownership_state
                    or values["ownership.state_revision"] != checkpoint.ownership_state_revision
                    or values["ownership.epoch"] != checkpoint.ownership_epoch):
                raise GateDenied("scope_denied")
            self._configured_original(binding)
            return observations

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

    def _service_predecessor(self, binding, operation, phase):
        if operation != "enqueue_handoff" or phase != "refusal_complete":
            return None
        records = [record for record in self.store.intents(binding.case_id)
                   if record.intent.binding == binding and record.intent.operation == "register_service_refusal"]
        return records[0] if len(records) == 1 else None

    def _communication_wait_expiry(self, intent):
        """Recheck a tagged pre-send scope after pacing; not a sent receipt."""
        if intent.operation not in {"send_clarification", "enqueue_handoff"}:
            return None
        question_id = (intent.arguments.get("question_id") if intent.operation == "send_clarification"
                       else "question:" + intent.action_id)
        if question_id is None or self.store.wait(question_id) is None:
            return None
        record = self.store.load_wait_record(question_id)
        checkpoint, original = self._configured_original(intent.binding)
        if (record.lifecycle != "pending" or record.wait.binding != intent.binding
                or record.communication_action_id != intent.action_id
                or record.communication_edge.operation != intent.operation or record.communication_stage != intent.stage
                or record.wait.recipient != intent.arguments.get("recipient") or record.owner_id != self.auth.caller_id
                or (record.owner_state, record.owner_revision, record.owner_epoch) !=
                   (checkpoint.ownership_state, checkpoint.ownership_state_revision, checkpoint.ownership_epoch)
                or (intent.ownership_state_revision, intent.ownership_epoch) != (record.owner_revision, record.owner_epoch)
                or any(getattr(intent, key) != getattr(record.origin_checkpoint, key) for key in
                       ("profile_version", "process_version", "policy_version", "deadline"))
                or record.profile_hash != self.profile.release_hash or record.policy_hash != self.profile.policy_hash
                or record.process != self.profile.processes[original.kind]
                or checkpoint.model_copy(update={"budget": record.origin_checkpoint.budget,
                    "observations": record.origin_checkpoint.observations}) != record.origin_checkpoint
                or self.clock.now() >= record.wait.expires_at
                or intent.operation == "enqueue_handoff" and record.communication_intent != intent):
            raise GateDenied("scope_denied")
        return record.wait.expires_at

    def _run(self, intent, observations, *, is_resend=False, decision_source=None, decision_submission=None):
        decision_limit = None
        if intent.decision_id is not None and ownership_enabled(self.profile):
            if decision_source is None or decision_submission is None or is_resend:
                raise GateDenied("scope_denied")
            self.gate.validate_registered_decision(decision_submission, intent, decision_source, self.clock.now())
            decision_limit = min(decision_submission.decision.expires_at, decision_source.grant.expires_at)
        checkpoint = self._active(intent.binding.case_id, intent.binding, intent)
        original = self.store.original_request(intent.binding.case_id, intent.binding.generation)
        values = {key: obs.value for key, obs in qualified_observations(self.profile, intent.binding.object_id, observations).items()}
        if values.get("ownership.owner") != self.auth.caller_id:
            raise GateDenied("scope_denied")
        proposal = ActionProposal(operation=intent.operation, stage=intent.stage, arguments=intent.arguments, evidence_refs=[])
        decision = self.gate.evaluate(original, proposal, observations, checkpoint,
            journal_predecessor=self._service_predecessor(intent.binding, intent.operation, checkpoint.phase))
        if not decision.allowed or expected_facts(intent, profile=self.profile) is None:
            raise GateDenied("scope_denied")
        required = required_fields(self.profile, intent.operation)
        actual = {key: observation.revision for key, observation in qualified_observations(self.profile, intent.binding.object_id, observations).items()}
        if (any(intent.expected_revisions.revisions.get(key) != actual[key] for key in required)
                or intent.ownership_state_revision != values.get("ownership.state_revision")
                or intent.ownership_epoch != values.get("ownership.epoch")):
            raise GateDenied("scope_denied")
        self._return_predecessor(intent)
        if intent.operation in BUSINESS and intent.binding.supersedes_generation is not None:
            for record in self.store.intents(intent.binding.case_id):
                if (record.intent.binding.generation != intent.binding.generation
                        and record.intent.operation in BUSINESS and record.state != "prepared"
                        and (record.verification is None or record.verification.status not in {"verified", "rejected"})):
                    raise GateDenied("scope_denied")
        if not is_resend:
            self.store.prepare(intent)
        self._pace(min(intent.deadline, self.store.checkpoint(intent.binding.case_id).deadline,
            decision_limit or intent.deadline))
        wait_expiry = self._communication_wait_expiry(intent)
        anchor = self._timing.monotonic_anchor() if self._timing is not None else None
        lease = self.store.begin_dispatch(intent, self.clock.now(), is_resend=is_resend)
        try:
            deadline = self._transport_deadline(min(lease.deadline, wait_expiry or lease.deadline,
                decision_limit or lease.deadline), lease, anchor)
            if decision_limit is not None and self.clock.now() >= deadline:
                raise GateDenied("scope_denied")
        except (GateDenied, ValueError):
            result = VerificationResult(status="outcome_unknown", reason="entry_unresolved")
            self.store.record_verification(intent.action_id, result)
            return result
        try:
            transport = getattr(getattr(self.bundle, _PORTS[intent.operation]), intent.operation)
        except Exception:
            return self._read_and_verify(intent)[0]
        try:
            deadline = self._transport_deadline(deadline, lease, anchor)
            if decision_limit is not None and self.clock.now() >= deadline:
                raise GateDenied("scope_denied")
        except (GateDenied, ValueError):
            result = VerificationResult(status="outcome_unknown", reason="entry_unresolved")
            self.store.record_verification(intent.action_id, result)
            return result
        try:
            dispatch = transport(intent, deadline=deadline)
        except Exception:
            dispatch = None
        if dispatch is not None:
            self._settle(lease, dispatch.status != "outcome_unknown", anchor=anchor)
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
            read = self._read(intent.binding, target, port, method, purpose="reconcile_original", action_id=intent.action_id,
                              deadline=intent.deadline)
            if read.stage == "scope_rejected":
                return self._denied(), None
            if provider_request_id is not None and read.provider_request_id is not None and provider_request_id != read.provider_request_id:
                result = VerificationResult(status="conflict", object_id=intent.binding.object_id, action_id=intent.action_id,
                    fingerprint=intent.argument_fingerprint, postcondition=intent.postcondition, reason="provider_identity_conflict")
            else:
                result = verify(intent, read, profile=self.profile)
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
            if ownership_enabled(self.profile) and (intent.operation == "transfer_owner" or intent.decision_id is not None):
                raise GateDenied("scope_denied")
            try:
                record = self.store.intent(intent.action_id)
            except JournalFailure:
                record = None
            if record is not None:
                if record.intent != intent:
                    return VerificationResult(status="conflict", reason="immutable_intent_conflict")
                if record.state != "prepared":
                    return self.reconcile(intent.action_id)
            if intent.operation == "enqueue_handoff" and packet_enabled(self.profile):
                raise GateDenied("scope_denied")
            observations = self.read_material_authorities(intent)
            return self._run(intent, observations)
        except Exception:
            # Never convert a failure after entry into an invented nonexecution result.
            try:
                entered = self.store.intent(intent.action_id).state != "prepared"
            except (JournalFailure, AttributeError):
                pass
            return VerificationResult(status="outcome_unknown", reason="entry_unresolved") if entered else self._denied()

    def reconcile_read_only(self, action_id):
        """Read the exact entered original with fresh public ACL; never resend."""
        return self.reconcile(action_id, read_only=True)

    def reconcile(self, action_id, *, read_only=False):
        try:
            self._authenticated()
            if type(read_only) is not bool:
                raise GateDenied("scope_denied")
            record = self.store.intent(action_id)
            intent = record.intent
            if intent.operation not in _PORTS or intent.profile_version != self.profile.version or record.state == "prepared":
                raise GateDenied("scope_denied")
            if record.state in {"verified", "conflict"}:
                # Still check current public read ACL before disclosing a saved result.
                result, _ = self._read_and_verify(intent)
                return result
            result, read = self._read_and_verify(intent)
            if read_only or self.store.generation_stop(intent.binding).requested:
                return result
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
            if declared_operation == "transfer_owner" and ownership_enabled(self.profile):
                raise GateDenied("scope_denied")
            if declared_operation == "enqueue_handoff" and packet_enabled(self.profile):
                raise GateDenied("scope_denied")
            checkpoint = self._active(case_id)
            fields = required_fields(self.profile, declared_operation)
            observations = self._facts(checkpoint.binding, fields | OWNER_FIELDS, purpose=self._material_purpose(declared_operation))
            original = self.store.original_request(case_id, checkpoint.binding.generation)
            proposal, postcondition = build_proposal(original, observations)
            if not isinstance(proposal, ActionProposal) or proposal.operation != declared_operation:
                raise GateDenied("scope_denied")
            proposal = ActionProposal.model_validate(proposal.model_dump())
            existing = [record for record in self.store.intents(case_id)
                        if record.intent.binding == checkpoint.binding and record.intent.operation == declared_operation]
            if existing:
                if len(existing) != 1:
                    return VerificationResult(status="conflict", reason="immutable_intent_conflict")
                record = existing[0]
                if (proposal.stage != record.intent.stage or fingerprint(proposal.arguments) != record.intent.argument_fingerprint
                        or fingerprint(postcondition) != fingerprint(record.intent.postcondition)):
                    return VerificationResult(status="conflict", reason="immutable_intent_conflict")
                intent = record.intent
                if record.state != "prepared":
                    return self.reconcile(intent.action_id)
                return self._run(intent, observations)
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

    def bind_request(self, request, deadline, *, initialize_process=False):
        try:
            self._authenticated()
            request = CanonicalRequest.model_validate(request.model_dump())
            fields = IDENTITY_FIELDS
            if type(initialize_process) is not bool:
                raise GateDenied("scope_denied")
            if initialize_process:
                fields |= {"case.completeness", "customer.consent", "customer.consent_mode", "customer.request_fingerprint"}
                if any(self.profile.authorities.get(key) != key.partition(".")[0] for key in fields | OWNER_FIELDS):
                    raise GateDenied("scope_denied")
                # A transferred admission attempt is immutable. A matching saved
                # current input may instead consume the existing case's read
                # leases; storage lookup itself confers no disclosure authority.
                try:
                    saved_checkpoint = self.store.checkpoint(request.case_id)
                except JournalFailure:
                    saved_checkpoint = None
                current = self.store.find_request(request.case_id, request.request_id, request.request_revision,
                    request.consent_revision, request_fingerprint(request))
                if current is not None and saved_checkpoint is not None and current == saved_checkpoint.binding:
                    spec = self.profile.processes.get(request.kind)
                    if (self.store.original_request(request.case_id, current.generation) != request or spec is None
                            or saved_checkpoint.profile_version != self.profile.version
                            or saved_checkpoint.process_version != spec.version or saved_checkpoint.stop.requested):
                        raise GateDenied("scope_denied")
                    limit = min(saved_checkpoint.deadline, deadline)
                    observations = self._facts(current, fields, deadline=limit, purpose="bind_request")
                    fresh_binding = self.gate.bind_request(request, self.auth, observations)
                    if RequestBinding.model_validate({**fresh_binding.model_dump(), "supersedes_generation": current.supersedes_generation}) != current:
                        raise GateDenied("scope_denied")
                    observations += self._facts(current, OWNER_FIELDS, deadline=limit, purpose="bind_request")
                    checkpoint = self.store.checkpoint(request.case_id)
                    if checkpoint.binding != current:
                        raise GateDenied("scope_denied")
                    saved = qualified_observations(self.profile, request.object_id, checkpoint.observations)
                    saved.update(qualified_observations(self.profile, request.object_id, observations))
                    self.store.save_checkpoint(PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "observations": list(saved.values())}))
                    return current
            attempt = self.store.start_admission("attempt:" + uuid4().hex, self.auth, request, self.clock.now(), deadline)
            observations = self._facts(request, fields, attempt_id=attempt.attempt_id, deadline=attempt.deadline)
            binding = self.gate.bind_request(request, self.auth, observations)
            if initialize_process:
                observations += self._facts(request, OWNER_FIELDS, attempt_id=attempt.attempt_id, deadline=attempt.deadline)
                values = {key: obs.value for key, obs in qualified_observations(self.profile, request.object_id, observations).items()}
            spec = self.profile.processes.get(request.kind)
            if spec is None:
                raise GateDenied("scope_denied")
            current = self.store.find_request(binding.case_id, binding.request_id, binding.request_revision, binding.consent_revision, binding.fingerprint)
            if current is not None:
                if current.generation != binding.generation:
                    raise GateDenied("scope_denied")
                binding = current
                checkpoint = self.store.checkpoint(binding.case_id)
                if initialize_process:
                    if checkpoint.profile_version != self.profile.version or checkpoint.process_version != spec.version:
                        raise GateDenied("scope_denied")
                    saved = qualified_observations(self.profile, request.object_id, checkpoint.observations)
                    saved.update(qualified_observations(self.profile, request.object_id, observations))
                    checkpoint = PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "observations": list(saved.values())})
            else:
                try:
                    previous = self.store.checkpoint(binding.case_id)
                except JournalFailure:
                    previous = None
                if previous is None:
                    if initialize_process and values["ownership.owner"] != self.auth.caller_id:
                        raise GateDenied("scope_denied")
                    structured = not (request.narrative and request.narrative.strip()) and not request.evidence_ids
                    planning_cap = 0 if structured else 4
                    checkpoint = PhaseCheckpoint(binding=binding, phase="intake", next_gate="intake", profile_version=self.profile.version,
                        process_version=spec.version, policy_version="v1", processing_status="pending",
                        budget={"case_id": binding.case_id, "deadline": attempt.deadline, "max_planner_calls": planning_cap,
                                "role_allowances": {"planning": {"max_invocations": planning_cap}}}, deadline=attempt.deadline)
                    if initialize_process:
                        checkpoint = PhaseCheckpoint.model_validate({**checkpoint.model_dump(), "observations": list(observations),
                            "ownership_state": values["ownership.state"], "ownership_state_revision": values["ownership.state_revision"],
                            "ownership_epoch": values["ownership.epoch"]})
                else:
                    if initialize_process and previous.profile_version != self.profile.version:
                        raise GateDenied("scope_denied")
                    binding = RequestBinding.model_validate({**binding.model_dump(), "supersedes_generation": previous.binding.generation})
                    checkpoint = PhaseCheckpoint.model_validate({**previous.model_dump(), "binding": binding,
                        "phase": "intake", "next_gate": "intake", "profile_version": self.profile.version,
                        "process_version": spec.version, "processing_status": "pending", "observations": list(observations) if initialize_process else []})
                    predecessor = self.store.original_request(binding.case_id, previous.binding.generation)
                    if (initialize_process and previous.stop.requested and predecessor is not None
                            and predecessor.kind in {"reschedule_window", "reschedule_exact"}
                            and request.kind in {"goods_refusal", "service_refusal"}):
                        if (binding.request_id == previous.binding.request_id or binding.generation == previous.binding.generation
                                or values["ownership.owner"] != self.auth.caller_id
                                or values["ownership.state"] != "accepted"
                                or values["customer.consent"] != "granted"
                                or values["customer.consent_mode"] != request.consent_mode
                                or values["customer.request_fingerprint"] != binding.fingerprint):
                            raise GateDenied("scope_denied")
                        checkpoint = checkpoint.model_copy(update={"next_gate": "extract_input", "stop": StopState(),
                            "question_id": None, "awaited_fields": [], "observations": [],
                            "ownership_state": values["ownership.state"], "ownership_state_revision": values["ownership.state_revision"],
                            "ownership_epoch": values["ownership.epoch"], "deadline": min(previous.deadline, attempt.deadline)})
                        self.store.admit_refusal_after_stopped_reschedule(attempt.attempt_id, binding, request, checkpoint, previous.binding)
                        current_checkpoint = self.store.checkpoint(binding.case_id)
                        self.store.save_checkpoint(current_checkpoint.model_copy(update={"observations": list(observations)}))
                        return binding
            self.store.admit_from_attempt(attempt.attempt_id, binding, request, checkpoint)
            return binding
        except Exception:
            raise GateDenied("scope_denied") from None
