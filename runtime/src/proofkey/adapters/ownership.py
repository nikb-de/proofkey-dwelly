"""Closed synthetic source authority; hashes are integrity, never authentication.

All transitions run inside the independent provider's existing transaction.
No journal joins, caller-owned grants, or native participation are implied.
"""
import json
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ..contracts import (AuthContext, AuthorityObservation, CanonicalRequest, EffectIntent, Hash, Identifier,
                         NonexecutionProof, Revision, RevisionVector, Timestamp)
from ..identity import fingerprint, request_fingerprint
from ..ownership_contracts import (OWNERSHIP_BASES_V1, OwnershipModel, OwnershipGrantV1,
    OwnershipPacketV1, OriginalTransferIdentityV1, SyntheticTargetAcceptanceV1,
    TransferArgumentsV1, TransferPostconditionV1, TransferPendingV1, TransferAcceptedV1,
    TransferRejectedV1, TransferSourceReceiptV1)


def strict_fixture_pairs(pairs):
    """Source files are trusted inputs, but duplicate claims are ambiguous."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate synthetic source fixture field")
        result[key] = value
    return result


class SyntheticOwnershipFixtureV1(OwnershipModel):
    kind: Literal["synthetic_ownership_fixture_v1"]
    profile_id: Identifier
    profile_version: Literal["v1.4"]
    profile_hash: Hash
    process_hash: Hash
    policy_hash: Hash
    request: CanonicalRequest
    case_deadline: Timestamp
    packet: OwnershipPacketV1
    grant_revision: Revision
    grant: OwnershipGrantV1
    target_acceptances: Annotated[list[SyntheticTargetAcceptanceV1], Field(max_length=16)]
    fixture_hash: Hash
    simulated: Literal[True]

    @model_validator(mode="after")
    def integrity(self):
        data = self.model_dump(mode="json")
        data.pop("fixture_hash")
        data["grant"].pop("fixture_hash")
        for instruction in data["target_acceptances"]:
            instruction.pop("fixture_hash")
        if fingerprint(data) != self.fixture_hash or self.grant.fixture_hash != self.fixture_hash:
            raise ValueError("Synthetic ownership fixture integrity mismatch")
        if any(item.fixture_hash != self.fixture_hash for item in self.target_acceptances):
            raise ValueError("Target instruction fixture mismatch")
        if len({fingerprint(item.model_dump(mode="json")) for item in self.target_acceptances}) != len(self.target_acceptances):
            raise ValueError("Duplicate target instruction")
        return self


class SourceTransferRecordV1(OwnershipModel):
    kind: Literal["synthetic_source_transfer_record_v1"] = "synthetic_source_transfer_record_v1"
    effect: EffectIntent
    grant: OwnershipGrantV1
    receipt: TransferSourceReceiptV1
    history: Annotated[list[TransferSourceReceiptV1], Field(min_length=1, max_length=2)]
    pending_revisions: RevisionVector | None
    fixture_hash: Hash
    simulated: Literal[True]

    @staticmethod
    def next_revision(revision, value):
        # Exact independent provider _update rule, not a reconstruction from
        # mutable current facts. A missing saved vector is never synthesized.
        return ("v" + str(int(revision[1:]) + 1) if revision.startswith("v") and revision[1:].isdigit()
                else fingerprint({"revision": revision, "value": value}))

    @model_validator(mode="after")
    def original_history(self):
        effect = self.effect
        args = TransferArgumentsV1.model_validate(effect.arguments)
        condition = TransferPostconditionV1.model_validate(effect.postcondition)
        original = OriginalTransferIdentityV1(binding=effect.binding, transfer_id=args.intent.transfer_id,
            action_id=effect.action_id, provider_key=effect.provider_key, argument_fingerprint=effect.argument_fingerprint)
        if (condition.original != original or self.history[-1] != self.receipt
                or self.fixture_hash != self.grant.fixture_hash):
            raise ValueError("Stored transfer original/history identity mismatch")
        for item in self.history:
            event_at = (item.pending_at if isinstance(item, TransferPendingV1) else
                        item.accepted_at if isinstance(item, TransferAcceptedV1) else item.rejected_at)
            if ((item.original, item.packet, item.target_owner, item.expected_revisions) != (
                    original, condition.packet, condition.target_owner, effect.expected_revisions)
                    or not self.grant.issued_at <= event_at < min(effect.deadline, self.grant.expires_at)):
                raise ValueError("Stored receipt differs from original source scope")
        pending = self.history[0] if isinstance(self.history[0], TransferPendingV1) else None
        if pending:
            expected = effect.expected_revisions.revisions
            saved = self.pending_revisions.revisions if self.pending_revisions else {}
            if set(saved) != set(expected) or not {"ownership.state", "ownership.state_revision"} <= expected.keys():
                raise ValueError("Incomplete stored pending revision vector")
            for key, revision in expected.items():
                derived = self.next_revision(revision, "pending") if key in {"ownership.state", "ownership.state_revision"} else revision
                if saved[key] != derived:
                    raise ValueError("Stored pending vector differs from original transition")
            if (pending.pending_state_revision != saved["ownership.state_revision"]
                    or pending.evidence_ref != "synthetic-provider:effect:" + effect.action_id
                    or (len(self.history) == 2 and not isinstance(self.receipt, TransferAcceptedV1))):
                raise ValueError("Stored pending history mismatch")
        elif len(self.history) != 1 or self.pending_revisions is not None:
            raise ValueError("Unexpected stored transfer history/vector")
        if isinstance(self.receipt, TransferAcceptedV1):
            accepted = self.receipt
            prior = pending.pending_state_revision if pending else effect.expected_revisions.revisions.get("ownership.state_revision")
            if (prior is None or accepted.pending_state_revision != (pending.pending_state_revision if pending else None)
                    or accepted.accepted_state_revision != self.next_revision(prior, "accepted")
                    or (pending and accepted.accepted_at < pending.pending_at)):
                raise ValueError("Stored acceptance history mismatch")
        elif isinstance(self.receipt, TransferRejectedV1):
            if (pending or self.receipt.retained_state_revision != condition.packet.accepted_state_revision
                    or self.receipt.evidence_ref != self.receipt.nonexecution.evidence_ref):
                raise ValueError("Stored rejection history mismatch")
        elif len(self.history) != 1:
            raise ValueError("Unexpected pending history")
        return self


class SyntheticOwnershipSource:
    def __init__(self, world, raw):
        self.world = world
        self.fixture = SyntheticOwnershipFixtureV1.model_validate(raw)
        fixture, profile = self.fixture, world._profile
        if (fixture.profile_id, fixture.profile_version, fixture.profile_hash, fixture.process_hash, fixture.policy_hash) != (
                profile.profile_id, profile.version, profile.release_hash, profile.process_hash, profile.policy_hash):
            raise ValueError("Ownership fixture profile identity mismatch")
        packet, grant, request = fixture.packet, fixture.grant, fixture.request
        if (packet.content_hash is None or request.kind not in profile.processes or packet.binding.fingerprint != request_fingerprint(request)
                or any(getattr(request, field) != getattr(packet.binding, field) for field in (
                    "case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision"))
                or not self._grant_matches(grant, packet) or grant.actor_id != packet.accepted_owner
                or grant.issued_at > packet.accepted_at or packet.accepted_at >= grant.expires_at
                or grant.expires_at > fixture.case_deadline):
            raise ValueError("Ownership fixture initial scope mismatch")

    @staticmethod
    def _grant_matches(grant, packet):
        return (grant.binding, grant.packet_id, grant.packet_hash, grant.packet_revision,
            grant.content_hash, grant.owner, grant.epoch, grant.state_revision) == (
            packet.binding, packet.packet_id, packet.packet_hash, packet.packet_revision,
            packet.content_hash, packet.accepted_owner, packet.accepted_epoch, packet.accepted_state_revision)

    def seed(self, connection):
        fixture, packet = self.fixture, self.fixture.packet
        marker = connection.execute("SELECT value FROM metadata WHERE key='ownership_fixture'").fetchone()
        canonical = fixture.model_dump_json()
        if marker:
            if marker[0] != canonical:
                raise ValueError("Provider ownership registration changed")
            self.validate_records(connection)
            return
        facts = self.world._facts(connection, packet.binding.case_id, packet.binding.object_id)
        values = {key: json.loads(row["value"]) for key, row in facts.items()}
        if (values.get("ownership.owner"), values.get("ownership.epoch"), values.get("ownership.state_revision"),
                values.get("ownership.state"), values.get("operator.packet_hash"), values.get("operator.packet_revision")) != (
                packet.accepted_owner, packet.accepted_epoch, packet.accepted_state_revision, "accepted", packet.packet_hash, packet.packet_revision):
            raise ValueError("Initial packet differs from provider facts")
        for identity, value, revision, evidence in (
                ("operator.ownership_grant", fixture.grant, fixture.grant_revision, fixture.grant.evidence_ref),
                ("operator.ownership_packet", packet, "v1", packet.acceptance_evidence)):
            connection.execute("INSERT INTO facts VALUES(?,?,?,?,?,?)", (packet.binding.case_id, packet.binding.object_id,
                identity, value.model_dump_json(), revision, evidence))
        connection.execute("INSERT INTO metadata VALUES('ownership_fixture',?)", (canonical,))

    def authenticated(self, connection, auth, binding):
        if auth is None:
            return False
        try:
            auth = AuthContext.model_validate(auth.model_dump())
        except (ValueError, AttributeError):
            return False
        scope = connection.execute("SELECT readers FROM scopes WHERE case_id=? AND object_id=?",
            (binding.case_id, binding.object_id)).fetchone()
        return bool(scope and json.loads(scope[0]).get(auth.caller_id) == auth.proof_reference
                    and auth.caller_id == self.fixture.grant.actor_id == self.fixture.packet.accepted_owner)

    def parse(self, effect):
        args = TransferArgumentsV1.model_validate(effect.arguments)
        condition = TransferPostconditionV1.model_validate(effect.postcondition)
        original = OriginalTransferIdentityV1(binding=effect.binding, transfer_id=args.intent.transfer_id,
            action_id=effect.action_id, provider_key=effect.provider_key, argument_fingerprint=effect.argument_fingerprint)
        if (effect.operation != "transfer_owner" or effect.stage != "request" or args.intent.binding != effect.binding
                or effect.binding != self.fixture.packet.binding or condition.original != original
                or condition.packet != self.fixture.packet or condition.target_owner != args.intent.target_owner
                or args.content_hash != self.fixture.packet.content_hash
                or (args.intent.packet_id, args.intent.packet_hash, args.intent.packet_revision,
                    args.intent.expected_owner, args.intent.expected_epoch, args.intent.expected_state_revision) != (
                    condition.packet.packet_id, condition.packet.packet_hash, condition.packet.packet_revision,
                    condition.packet.accepted_owner, condition.packet.accepted_epoch, condition.packet.accepted_state_revision)
                or args.grant_id != self.fixture.grant.grant_id or args.grant_revision != self.fixture.grant_revision
                or effect.profile_version != self.fixture.profile_version
                or effect.process_version != self.world._profile.processes[self.fixture.request.kind].version
                or effect.policy_version != "v1" or effect.consent_revision != effect.binding.consent_revision
                or effect.ownership_epoch != condition.packet.accepted_epoch
                or effect.ownership_state_revision != condition.packet.accepted_state_revision
                or effect.deadline != args.intent.expires_at or args.intent.expires_at > self.fixture.case_deadline
                or args.intent.expires_at > self.fixture.grant.expires_at):
            raise ValueError("Transfer differs from original source scope")
        return args, condition

    def current_allowed(self, connection, effect):
        try:
            args, condition = self.parse(effect)
            facts = self.world._facts(connection, effect.binding.case_id, effect.binding.object_id)
            values = {key: json.loads(row["value"]) for key, row in facts.items()}
            packet = OwnershipPacketV1.model_validate(values["operator.ownership_packet"])
            grant = OwnershipGrantV1.model_validate(values["operator.ownership_grant"])
            now = self.world._now()
            expected = effect.expected_revisions.revisions
            # Every saved source revision is compared, not just a caller-chosen
            # subset of the mandatory conditional material contract.
            if (not self.world._write_identity_allowed(connection, effect)
                    or any(key not in facts or facts[key]["revision"] != revision for key, revision in expected.items())
                    or packet != condition.packet or grant != self.fixture.grant
                    or not self._grant_matches(grant, packet) or not grant.may_initiate_transfer
                    or args.intent.target_owner not in grant.target_owners or args.intent.target_owner == grant.owner
                    or not grant.issued_at <= now < min(grant.expires_at, args.intent.expires_at, effect.deadline)
                    or values.get("customer.request_fingerprint") != effect.binding.fingerprint
                    or values.get("customer.consent_mode") != self.fixture.request.consent_mode
                    or values.get("customer.consent") != "granted"
                    or (values.get("ownership.state"), values.get("ownership.owner"), values.get("ownership.epoch"),
                        values.get("ownership.state_revision")) != ("accepted", grant.owner, grant.epoch, grant.state_revision)
                    or values.get("operator.packet_hash") != packet.packet_hash
                    or values.get("operator.packet_revision") != packet.packet_revision
                    or values.get("delivery.risk") != "safe" or values.get("delivery.stage") != "eligible"
                    or values.get("policy.version") != effect.policy_version):
                return False
            return True
        except (ValueError, KeyError, TypeError):
            return False

    @staticmethod
    def _key(original):
        return "ownership_original:" + fingerprint(original.model_dump(mode="json"))

    def save(self, connection, record):
        connection.execute("INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (self._key(record.receipt.original), record.model_dump_json()))

    def load(self, connection, original):
        row = connection.execute("SELECT value FROM metadata WHERE key=?", (self._key(original),)).fetchone()
        if not row:
            return None
        record = SourceTransferRecordV1.model_validate_json(row[0])
        self.validate_record(connection, self._key(original), record)
        return record

    def validate_record(self, connection, key, record):
        """Join only this provider's durable rows, never the journal/current grants."""
        effect, receipt = record.effect, record.receipt
        args, _ = self.parse(effect)
        required = self.world._profile.capabilities["transfer_owner"].conditional_coverage.covered_fields
        marker = connection.execute("SELECT value FROM metadata WHERE key='ownership_fixture'").fetchone()
        if (key != self._key(receipt.original) or record.fixture_hash != self.fixture.fixture_hash
                or record.grant != self.fixture.grant or not marker or marker[0] != self.fixture.model_dump_json()
                or not set(required) <= effect.expected_revisions.revisions.keys()):
            raise ValueError("Stored transfer fixture/grant/complete original mismatch")
        account = self.world._profile.capabilities["transfer_owner"].shared_limits.account_id
        rows = connection.execute("SELECT * FROM effects WHERE account_id=? AND provider_key=?",
            (account, effect.provider_key)).fetchall()
        terminal = connection.execute("SELECT * FROM final_rejections WHERE account_id=? AND provider_key=?",
            (account, effect.provider_key)).fetchall()
        rejected = isinstance(receipt, TransferRejectedV1)
        if (rejected and (len(terminal) != 1 or rows)) or (not rejected and (len(rows) != 1 or terminal)):
            raise ValueError("Stored transfer lacks exactly one original provider outcome")
        row = terminal[0] if rejected else rows[0]
        expected = {"account_id": account, "provider_key": effect.provider_key, "case_id": effect.binding.case_id,
            "object_id": effect.binding.object_id, "operation": "transfer_owner", "generation": effect.binding.generation,
            "action_id": effect.action_id, "fingerprint": effect.argument_fingerprint,
            "identity_hash": fingerprint(effect.model_dump(mode="json")),
            "request_id": "provider:" + fingerprint({"account": account, "provider_key": effect.provider_key})[:24]}
        if any(row[name] != value for name, value in expected.items()):
            raise ValueError("Stored transfer differs from durable original identity")
        if rejected:
            if receipt.evidence_ref != "synthetic-provider:terminal-rejection:" + row["request_id"]:
                raise ValueError("Stored rejection differs from terminal row")
        else:
            stage = "accepted" if isinstance(receipt, TransferAcceptedV1) else "pending"
            observations = [AuthorityObservation.model_validate(item) for item in
                json.loads(row["observations"], object_pairs_hook=strict_fixture_pairs)]
            event_at = receipt.accepted_at if stage == "accepted" else receipt.pending_at
            if (row["stage"] != stage or row["transfer_id"] != args.intent.transfer_id
                    or row["question_id"] is not None or row["packet_id"] is not None or row["packet_revision"] is not None
                    or len(observations) != 1):
                raise ValueError("Stored transfer effect projection mismatch")
            observation = observations[0]
            if ((observation.authority, observation.fact, observation.object_id, observation.value,
                    observation.provider_at, observation.observed_at, observation.evidence_ref) != (
                    "operator", "transfer_receipt", effect.binding.object_id, receipt.model_dump(mode="json"),
                    event_at, event_at, "synthetic-provider:effect:" + effect.action_id)):
                raise ValueError("Stored receipt differs from durable effect projection")

    def validate_records(self, connection):
        originals = set()
        for row in connection.execute("SELECT key,value FROM metadata WHERE key LIKE 'ownership_original:%'"):
            record = SourceTransferRecordV1.model_validate_json(row["value"])
            self.validate_record(connection, row["key"], record)
            originals.add((self.world._profile.capabilities["transfer_owner"].shared_limits.account_id, record.effect.provider_key))
        for table in ("effects", "final_rejections"):
            for row in connection.execute("SELECT account_id,provider_key FROM " + table + " WHERE operation='transfer_owner'"):
                if (row["account_id"], row["provider_key"]) not in originals:
                    raise ValueError("Provider transfer outcome lacks its full original")

    def reject(self, connection, effect, request_id):
        _, condition = self.parse(effect)
        receipt = TransferRejectedV1(original=condition.original, packet=condition.packet, target_owner=condition.target_owner,
            expected_revisions=effect.expected_revisions, retained_state_revision=condition.packet.accepted_state_revision,
            evidence_ref="synthetic-provider:terminal-rejection:" + request_id,
            rejected_at=self.world._now(), nonexecution=NonexecutionProof(status="proven",
                basis=OWNERSHIP_BASES_V1["terminal_nonexecution_basis"],
                evidence_ref="synthetic-provider:terminal-rejection:" + request_id), simulated=True)
        self.save(connection, SourceTransferRecordV1(effect=effect, grant=self.fixture.grant, receipt=receipt,
            history=[receipt], pending_revisions=None, fixture_hash=self.fixture.fixture_hash, simulated=True))

    def apply(self, connection, effect):
        _, condition = self.parse(effect)
        for instruction in self.fixture.target_acceptances:
            if self.instruction_matches(instruction, effect, condition):
                receipt = self.accept(connection, effect, instruction, pending=None)
                self.save(connection, SourceTransferRecordV1(effect=effect, grant=self.fixture.grant, receipt=receipt,
                    history=[receipt], pending_revisions=None, fixture_hash=self.fixture.fixture_hash, simulated=True))
                return "accepted", self.outcome(receipt)
        binding = effect.binding
        self.world._update(connection, binding.case_id, binding.object_id, "ownership.state", "pending")
        revision = self.state_revision(connection, binding, "pending")
        receipt = TransferPendingV1(original=condition.original, packet=condition.packet, target_owner=condition.target_owner,
            expected_revisions=effect.expected_revisions, pending_state_revision=revision, pending_at=self.world._now(),
            evidence_ref="synthetic-provider:effect:" + effect.action_id, simulated=True)
        facts = self.world._facts(connection, binding.case_id, binding.object_id)
        pending_revisions = RevisionVector(revisions={key: facts[key]["revision"] for key in effect.expected_revisions.revisions})
        self.save(connection, SourceTransferRecordV1(effect=effect, grant=self.fixture.grant, receipt=receipt,
            history=[receipt], pending_revisions=pending_revisions, fixture_hash=self.fixture.fixture_hash, simulated=True))
        return "pending", self.outcome(receipt)

    def state_revision(self, connection, binding, state):
        revision = self.world._update(connection, binding.case_id, binding.object_id, "ownership.state_revision", state)
        connection.execute("UPDATE facts SET value=? WHERE case_id=? AND object_id=? AND identity='ownership.state_revision'",
            (json.dumps(revision), binding.case_id, binding.object_id))
        return revision

    def instruction_matches(self, instruction, effect, condition):
        return (instruction.fixture_hash == self.fixture.fixture_hash and instruction.original == condition.original
            and instruction.packet == condition.packet and instruction.target_owner == condition.target_owner
            and instruction.expected_revisions == effect.expected_revisions
            and self.world._now() < instruction.expires_at <= min(effect.deadline, self.fixture.grant.expires_at)
            and instruction.target_owner in self.fixture.grant.target_owners)

    def accept(self, connection, effect, instruction, *, pending):
        binding, packet = effect.binding, instruction.packet
        now = self.world._now()
        self.world._update(connection, binding.case_id, binding.object_id, "ownership.state", "accepted")
        revision = self.state_revision(connection, binding, "accepted")
        self.world._update(connection, binding.case_id, binding.object_id, "ownership.owner", instruction.target_owner)
        self.world._update(connection, binding.case_id, binding.object_id, "ownership.epoch", packet.accepted_epoch + 1)
        successor = OwnershipPacketV1.model_validate({**packet.model_dump(), "accepted_owner": instruction.target_owner,
            "accepted_epoch": packet.accepted_epoch + 1, "accepted_state_revision": revision,
            "acceptance_evidence": instruction.evidence_ref, "accepted_at": now})
        self.world._update(connection, binding.case_id, binding.object_id, "operator.ownership_packet", successor.model_dump(mode="json"))
        connection.execute("UPDATE facts SET evidence_ref=? WHERE case_id=? AND object_id=? AND identity='operator.ownership_packet'",
            (instruction.evidence_ref, binding.case_id, binding.object_id))
        return TransferAcceptedV1(original=instruction.original, packet=packet, target_owner=instruction.target_owner,
            expected_revisions=effect.expected_revisions, pending_state_revision=pending.pending_state_revision if pending else None,
            accepted_state_revision=revision, accepted_epoch=packet.accepted_epoch + 1, accepted_at=now,
            acceptance_evidence=instruction.evidence_ref, target_instruction_hash=fingerprint(instruction.model_dump(mode="json")), simulated=True)

    @staticmethod
    def outcome(receipt):
        return {"operator.transfer_receipt": receipt.model_dump(mode="json")}

    def deliver(self, connection, instruction):
        instruction = SyntheticTargetAcceptanceV1.model_validate(instruction.model_dump())
        try:
            record = self.load(connection, instruction.original)
        except (ValueError, KeyError, TypeError):
            return False
        if not record:
            return False
        effect, receipt = record.effect, record.receipt
        _, condition = self.parse(effect)
        if not self.instruction_matches(instruction, effect, condition):
            return False
        if isinstance(receipt, TransferAcceptedV1):
            return receipt.target_instruction_hash == fingerprint(instruction.model_dump(mode="json"))
        if not isinstance(receipt, TransferPendingV1):
            return False
        facts = self.world._facts(connection, effect.binding.case_id, effect.binding.object_id)
        values = {key: json.loads(row["value"]) for key, row in facts.items()}
        if (not self.world._write_identity_allowed(connection, effect) or record.fixture_hash != self.fixture.fixture_hash
                or self.world._now() >= min(effect.deadline, record.grant.expires_at)
                or any(key not in facts or facts[key]["revision"] != revision
                       for key, revision in record.pending_revisions.revisions.items())
                or values.get("operator.ownership_packet") != condition.packet.model_dump(mode="json")
                or values.get("operator.ownership_grant") != record.grant.model_dump(mode="json")
                or (values.get("ownership.state"), values.get("ownership.state_revision"), values.get("ownership.owner"),
                    values.get("ownership.epoch")) != ("pending", receipt.pending_state_revision,
                        condition.packet.accepted_owner, condition.packet.accepted_epoch)):
            return False
        accepted = self.accept(connection, effect, instruction, pending=receipt)
        if self.world._now() >= min(effect.deadline, record.grant.expires_at, instruction.expires_at):
            connection.rollback()
            return False
        self.save(connection, SourceTransferRecordV1(effect=effect, grant=record.grant, receipt=accepted,
            history=[receipt, accepted], pending_revisions=record.pending_revisions,
            fixture_hash=record.fixture_hash, simulated=True))
        observations = self.world._effect_observations(connection, effect, self.outcome(accepted))
        connection.execute("UPDATE effects SET stage='accepted',observations=? WHERE operation='transfer_owner' AND provider_key=? AND generation=? AND action_id=? AND fingerprint=?",
            (json.dumps([obs.model_dump(mode="json") for obs in observations]), effect.provider_key,
             effect.binding.generation, effect.action_id, effect.argument_fingerprint))
        # Projection/history work can itself consume the remaining window.
        # Equality is ineligible; roll back every source mutation before commit.
        if self.world._now() >= min(effect.deadline, record.grant.expires_at, instruction.expires_at):
            connection.rollback()
            return False
        return True

    def disclosure_allowed(self, facts, request):
        if request.purpose not in {"transfer", "decision", "disposition"}:
            return False
        try:
            grant = OwnershipGrantV1.model_validate(json.loads(facts["operator.ownership_grant"]["value"]))
            packet = OwnershipPacketV1.model_validate(json.loads(facts["operator.ownership_packet"]["value"]))
            state = {key: json.loads(facts[key]["value"]) for key in (
                "ownership.state", "ownership.owner", "ownership.epoch", "ownership.state_revision")}
            return (request.caller_id == grant.actor_id == packet.accepted_owner
                and self._grant_matches(grant, packet) and grant == self.fixture.grant
                and (state["ownership.state"], state["ownership.owner"], state["ownership.epoch"],
                    state["ownership.state_revision"]) == ("accepted", grant.owner, grant.epoch, grant.state_revision)
                and grant.issued_at <= self.world._now() < grant.expires_at)
        except (KeyError, ValueError, TypeError):
            return False
