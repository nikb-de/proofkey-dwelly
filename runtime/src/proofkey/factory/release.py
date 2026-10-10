"""Simulation artifacts only; runtime activation is unavailable."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from ..contracts import HumanReviewApproval, ReleaseReceipt, EffectIntent, ReviewPacket
from ..identity import fingerprint
from .proposal import (FactoryDenied, HumanReviewEvent, OriginalInventory, canonical,
                       decode, wire, _contract_inventory)


class ReleaseDenied(FactoryDenied):
    pass


@dataclass(frozen=True)
class StagedRelease:
    status: str
    receipt_bytes: bytes
    manifest: bytes
    unmet_requirements: tuple[str, ...]

    @property
    def receipt(self):
        """Return a fresh detached wire object; nested mutation cannot edit artifact."""
        return ReleaseReceipt.model_validate_json(self.receipt_bytes)


def release_profile(review_packet, human_approval, pending_intents):
    raise ReleaseDenied("trusted_context_unavailable")


def stage_release(factory, review_packet, human_approval, pending_intents):
    try:
        if type(review_packet) is not ReviewPacket:
            raise ReleaseDenied("review_packet_mismatch")
        proposal = factory._proposal_hash(review_packet.proposal_hash)
        material, _, candidate, baseline, body = factory._resolve(proposal)
        expected = factory.check_proposal(proposal, review_packet.regression_hash)
        # The unsent packet is exact, except a matching independently supplied event.
        compared = review_packet.model_dump(mode="json")
        compared["approval"] = None
        if canonical(compared) != wire(expected):
            raise ReleaseDenied("review_packet_mismatch")
        if human_approval is None:
            raise ReleaseDenied("missing_approval")
        if type(human_approval) is not HumanReviewApproval:
            raise ReleaseDenied("approval_mismatch")
        approval = HumanReviewApproval.model_validate(human_approval.model_dump(mode="json"))
        if approval.mode == "actual":
            raise ReleaseDenied("activation_unavailable")
        if review_packet.approval is not None and wire(review_packet.approval) != wire(approval):
            raise ReleaseDenied("approval_mismatch")
        events = [event for event in factory.context.reviews if type(event) is HumanReviewEvent and
                  event.proof_reference == approval.proof_reference]
        if len(events) != 1:
            raise ReleaseDenied("approval_untrusted")
        event = events[0]
        if (event.actor_type != "human" or event.provenance != "synthetic_rehearsal" or
                canonical(decode(event.approval)) != wire(approval)):
            raise ReleaseDenied("approval_untrusted")
        if approval.proposal_hash != proposal.proposal_hash or approval.regression_hash != expected.regression_hash:
            raise ReleaseDenied("approval_binding_mismatch")
        if approval.decision != "approved":
            raise ReleaseDenied("approval_rejected")
        if set(approval.scope) != {"review_profile", "review_process"} or len(approval.scope) != 2:
            raise ReleaseDenied("approval_scope_inadequate")
        if not factory.context.now - timedelta(hours=24) <= approval.reviewed_at <= factory.context.now:
            raise ReleaseDenied("approval_stale")
        inventory = factory.context.inventory
        if (type(inventory) is not OriginalInventory or inventory.scope != "controlled_fixture" or
                type(inventory.pending) is not tuple or inventory.baseline_hash != baseline.release_hash or
                not inventory.inventory_id):
            raise ReleaseDenied("pending_inventory_unavailable")
        if type(pending_intents) not in (list, tuple):
            raise ReleaseDenied("pending_inventory_mismatch")
        caller = []
        for intent in pending_intents:
            if type(intent) is not EffectIntent:
                raise ReleaseDenied("pending_inventory_mismatch")
            caller.append(wire(EffectIntent.model_validate(intent.model_dump(mode="json"))))
        host = [wire(EffectIntent.model_validate(decode(raw))) for raw in inventory.pending]
        if sorted(caller) != sorted(host) or len(set(caller)) != len(caller):
            raise ReleaseDenied("pending_inventory_mismatch")
        if host:
            # No retained-version resolver, state inventory or migration transaction.
            raise ReleaseDenied("incompatible_pending_contract")
        unmet = ("atomic_activation_unavailable", "retained_version_resolution_unavailable",
                 "migration_unavailable", "authenticated_actual_review_unavailable",
                 "actual_coding_agent_unestablished", "http_transport_integration_unavailable",
                 "changed_process_adapter_dispatch_unavailable", "600_second_drill_unestablished")
        if "process_delta_registration" in body:
            unmet = tuple(item for item in unmet if item != "changed_process_adapter_dispatch_unavailable")
        manifest = dict(domain="proofkey-staged-simulation-v1", status="staged_simulation",
            proposal_hash=proposal.proposal_hash, regression_hash=expected.regression_hash,
            profile_hash=candidate.release_hash, profile_id=candidate.profile_id, profile_version=candidate.version,
            process_hash=candidate.process_hash, processes={key: {"id": spec.process_id, "version": spec.version,
                "hash": spec.release_hash} for key, spec in sorted(candidate.processes.items())},
            policy_hash=candidate.policy_hash, baseline_hash=baseline.release_hash, source_hash=proposal.source_hash,
            test_hash=proposal.test_hash, agent_hash=proposal.agent_hash, adapter_sources=body["adapter_sources"],
            original_contracts=body["original_contracts"], migration_declaration=proposal.migration.model_dump(mode="json"),
            migration_proof="unavailable", approval_hash=fingerprint(approval.model_dump(mode="json")),
            inventory_id=inventory.inventory_id, inventory_scope=inventory.scope, pending_inventory_hash=fingerprint({"pending": []}),
            unmet_requirements=list(unmet), staged_at=factory.context.now.isoformat())
        if "implementation_registration" in body:
            manifest["implementation_registration"] = body["implementation_registration"]
        if "process_delta_registration" in body:
            manifest["process_delta_registration"] = body["process_delta_registration"]
        receipt = ReleaseReceipt(version=candidate.version, release_hash=fingerprint(manifest),
            proposal_hash=proposal.proposal_hash, regression_hash=expected.regression_hash,
            profile_hash=candidate.release_hash, process_hash=candidate.process_hash, policy_hash=candidate.policy_hash,
            preserved_contract_hashes=[sha256(raw).hexdigest() for name, raw in _contract_inventory(baseline)
                if name in dict(_contract_inventory(candidate)) and raw == dict(_contract_inventory(candidate))[name]],
            approval=approval, released_at=factory.context.now)
        return StagedRelease("staged_simulation", wire(receipt), canonical(manifest), unmet)
    except ReleaseDenied:
        raise
    except FactoryDenied as error:
        raise ReleaseDenied(error.reason) from None
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ReleaseDenied("invalid_release_evidence") from None
