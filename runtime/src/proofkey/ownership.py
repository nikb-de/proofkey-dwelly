"""Explicitly synthetic registered ownership consumers over an injected gateway."""
from dataclasses import dataclass
from typing import Literal

from .contracts import EffectIntent, HumanOwnership, RevisionVector, TransferIntent
from .identity import fingerprint, stable_action_id
from .journal import JournalFailure
from .ownership_contracts import TransferArgumentsV1, TransferPostconditionV1, OriginalTransferIdentityV1
from .policy import GateDenied


@dataclass(frozen=True)
class OwnershipConsumerResult:
    ownership: HumanOwnership
    simulated: Literal[True] = True

    def __post_init__(self):
        if self.simulated is not True:
            raise ValueError("Only synthetic ownership consumers are registered")
        object.__setattr__(self, "ownership", HumanOwnership.model_validate(self.ownership.model_dump()))


class OwnershipService:
    def __init__(self, profile, bundle, store, clock, *, gateway):
        if (gateway.profile != profile or gateway.bundle is not bundle or gateway.store is not store or gateway.clock is not clock):
            raise ValueError("Exact injected gateway required")
        self.profile, self.store, self.clock, self.gateway = profile, store, clock, gateway

    def transfer_result(self, intent, auth):
        with self.gateway.execution_scope():
            return self._transfer_result(intent, auth)

    def transfer(self, intent, auth):
        """Synthetic-only compatibility projection; never native acceptance."""
        return self.transfer_result(intent, auth).ownership

    def _transfer_result(self, intent, auth):
        intent = TransferIntent.model_validate(intent.model_dump())
        if intent.transfer_id != stable_action_id(intent.binding, "transfer_owner", "request"):
            raise GateDenied("scope_denied")
        try:
            saved = self.store.transfer_record(intent.transfer_id)
        except JournalFailure as exc:
            if str(exc) != "No complete registered ownership transfer original":
                raise
            saved = None
        if saved is not None:
            if saved.intent != intent:
                raise GateDenied("immutable_intent_conflict")
            owner = self.gateway.execute_registered_transfer(intent.transfer_id, auth)
            return OwnershipConsumerResult(owner)
        source = self.gateway.read_ownership_sources(intent.binding, auth, "transfer")
        packet, grant = source.packet, source.grant
        if ((intent.packet_id, intent.packet_hash, intent.packet_revision, intent.expected_owner,
                intent.expected_state_revision, intent.expected_epoch) !=
            (packet.packet_id, packet.packet_hash, packet.packet_revision, packet.accepted_owner,
                packet.accepted_state_revision, packet.accepted_epoch)
                or intent.target_owner not in grant.target_owners or intent.target_owner == intent.expected_owner
                or self.clock.now() >= intent.expires_at or intent.expires_at > min(grant.expires_at, source.checkpoint.deadline)):
            raise GateDenied("scope_denied")
        args = TransferArgumentsV1(intent=intent, content_hash=packet.content_hash, grant_id=grant.grant_id,
            grant_revision=next(o.revision for o in source.observations if o.authority+"."+o.fact == "operator.ownership_grant"))
        original = OriginalTransferIdentityV1(binding=intent.binding, transfer_id=intent.transfer_id,
            action_id=intent.transfer_id, provider_key=intent.transfer_id, argument_fingerprint=fingerprint(args.model_dump(mode="json")))
        post = TransferPostconditionV1(original=original, packet=packet, target_owner=intent.target_owner,
            accepted_epoch=intent.expected_epoch+1)
        cp = source.checkpoint
        effect = EffectIntent(binding=intent.binding, operation="transfer_owner", stage="request",
            action_id=original.action_id, provider_key=original.provider_key, arguments=args.model_dump(mode="json"),
            argument_fingerprint=original.argument_fingerprint, profile_version=cp.profile_version,
            process_version=cp.process_version, policy_version=cp.policy_version, consent_revision=intent.binding.consent_revision,
            ownership_state_revision=intent.expected_state_revision, ownership_epoch=intent.expected_epoch,
            expected_revisions=RevisionVector(revisions={o.authority+"."+o.fact:o.revision for o in source.observations}),
            postcondition=post.model_dump(mode="json"), deadline=intent.expires_at)
        try:
            self.store.register_transfer_atomic(intent, effect, source, self.clock.now())
        except JournalFailure as exc:
            if "configuration_unavailable" in str(exc) or "registry" in str(exc):
                raise GateDenied("configuration_unavailable") from None
            raise
        return OwnershipConsumerResult(self.gateway.execute_registered_transfer(intent.transfer_id, auth))

    def reconcile_result(self, transfer_id, auth):
        with self.gateway.execution_scope():
            return self._reconcile_result(transfer_id, auth)

    def _reconcile_result(self, transfer_id, auth):
        return OwnershipConsumerResult(self.gateway.reconcile_registered_transfer(transfer_id, auth))

    def reconcile(self, transfer_id, auth):
        """Synthetic-only compatibility projection."""
        return self.reconcile_result(transfer_id, auth).ownership

    def validate_decision(self, submission, auth):
        with self.gateway.execution_scope():
            return self.gateway.validate_operator_decision(submission, auth)

    def record_disposition(self, disposition, auth):
        with self.gateway.execution_scope():
            return self.gateway.record_operator_disposition(disposition, auth)

    def execute_decision(self, decision_id, intent, auth):
        with self.gateway.execution_scope():
            return self.gateway.execute_operator_decision(decision_id, intent, auth)
