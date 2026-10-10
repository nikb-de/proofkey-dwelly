"""Host-owned finite packet snapshots; saved originals are never reconstructed."""
from dataclasses import dataclass

from .contracts import AuthorityObservation, OperatorPacket, RequestBinding
from .identity import fingerprint, stable_action_id
from .packet_contracts import (PacketAccessSnapshotV1, PacketCatalogV1, PacketContentV1,
    PacketEffectHistoryV1, PacketGenerationStopV1, PacketObservationRefV1, PacketPolicyRefV1,
    PacketSourceIdentityV1, PacketUntrustedRecordV1, PreparedPacketV1, packet_enabled,
    validate_packet_policy, validate_packet_scope)
from .policy import GateDenied, qualified_observations


@dataclass(frozen=True)
class PacketSources:
    """Internal current-read result, consumed by the same host entry, never a grant."""
    binding: RequestBinding
    observations: tuple[AuthorityObservation, ...]
    catalog: PacketCatalogV1
    access: PacketAccessSnapshotV1
    checkpoint_hash: str


class PacketService:
    def __init__(self, profile, store, source_reader, clock):
        self.profile, self.store, self.source_reader, self.clock = profile, store, source_reader, clock

    def prepare(self, case_id, auth, disposition):
        """Read and assemble locally; accepts no caller content or asserted authority."""
        try:
            if not packet_enabled(self.profile):
                raise GateDenied("scope_denied")
            binding = self.store.checkpoint(case_id).binding
            source = self.source_reader(binding, auth)
            if not isinstance(source, PacketSources) or source.binding != binding:
                raise GateDenied("scope_denied")
            checkpoint = self.store.checkpoint(case_id)
            if checkpoint.binding != binding or fingerprint(checkpoint.model_dump(mode="json")) != source.checkpoint_hash:
                raise GateDenied("scope_denied")
            facts = qualified_observations(self.profile, binding.object_id, source.observations)
            values = {key: item.value for key, item in facts.items()}
            now = self.clock.now()
            snapshot_at = max(facts[key].observed_at for key in
                ("operator.packet_catalog", "operator.packet_access"))
            catalog, access = validate_packet_scope(source.catalog, source.access,
                case_id=case_id, object_id=binding.object_id, sender=binding.principal_id,
                recipient=values["operator.recipient"], now=now)
            if (source.catalog != PacketCatalogV1.model_validate(values["operator.packet_catalog"])
                    or source.access != PacketAccessSnapshotV1.model_validate(values["operator.packet_access"])):
                raise GateDenied("scope_denied")
            unknowns, conflicts, stops, history = [], [], [], []
            bindings = self.store.request_bindings(case_id)
            if binding not in bindings:
                raise GateDenied("scope_denied")
            for prior in bindings:
                if prior.object_id != binding.object_id or prior.principal_id != binding.principal_id:
                    raise GateDenied("scope_denied")
                ref = "local:request:" + case_id + ":" + prior.generation
                original = self.store.original_request(case_id, prior.generation)
                if original is None:
                    unknowns.append(PacketUntrustedRecordV1(record_id="missing-original:" + prior.generation,
                        description="Local original request is missing; this generation's input history is incomplete.", source_refs=[ref]))
                if prior != binding:
                    unknowns.append(PacketUntrustedRecordV1(record_id="unknown-frozen:" + prior.generation,
                        description="Historical generation frozen checkpoint versions are unavailable through the public history API.", source_refs=[ref]))
                stop = self.store.generation_stop(prior)
                if stop.requested:
                    stops.append(PacketGenerationStopV1(generation=prior.generation,
                        requested_at=stop.requested_at, evidence_ref="local:stop:" + case_id + ":" + prior.generation))
            for record in self.store.intents(case_id):
                intent, verification = record.intent, record.verification
                if intent.binding not in bindings:
                    raise GateDenied("scope_denied")
                status = verification.status if verification is not None else "unverified"
                refs = list(verification.evidence_refs) if verification is not None else []
                history.append(PacketEffectHistoryV1(binding=intent.binding, action_id=intent.action_id,
                    provider_key=intent.provider_key, argument_fingerprint=intent.argument_fingerprint,
                    operation=intent.operation, stage=intent.stage, profile_version=intent.profile_version,
                    process_version=intent.process_version, policy_version=intent.policy_version,
                    dispatch_state=record.state if record.state in {"prepared", "dispatching"} else "unknown",
                    verification_state=status, as_of=verification.as_of if verification is not None and verification.as_of is not None else now,
                    evidence_refs=refs, unresolved=status not in {"verified", "rejected"}))
                local_ref = "local:intent:" + intent.action_id
                if record.state not in {"prepared", "dispatching"}:
                    unknowns.append(PacketUntrustedRecordV1(record_id="unknown-dispatch:" + intent.action_id,
                        description="The local journal retains verification separately; no independent dispatch acknowledgement is durably available.",
                        source_refs=[local_ref]))
                if status in {"unverified", "pending", "outcome_unknown"}:
                    unknowns.append(PacketUntrustedRecordV1(record_id="unresolved-effect:" + intent.action_id,
                        description="The original local effect has no resolved verification outcome.", source_refs=[local_ref, *refs]))
                if status == "conflict":
                    conflicts.append(PacketUntrustedRecordV1(record_id="effect-conflict:" + intent.action_id,
                        description="The original effect's independent verification recorded a conflict.", source_refs=[local_ref, *refs]))
            for extract in catalog.extracts:
                if extract.assertion.uncertainty == "conflicting":
                    conflicts.append(PacketUntrustedRecordV1(record_id="conflicting-extract:" + extract.extract_id,
                        description=extract.assertion.claim, source_refs=[facts["operator.packet_catalog"].evidence_ref,
                            extract.processing_receipt_reference]))
                elif extract.assertion.uncertainty in {"unverified", "uncertain"}:
                    unknowns.append(PacketUntrustedRecordV1(record_id="untrusted-extract:" + extract.extract_id,
                        description=extract.assertion.claim, source_refs=[facts["operator.packet_catalog"].evidence_ref,
                            extract.processing_receipt_reference]))
            action_id = stable_action_id(binding, "enqueue_handoff", "enqueue")
            identity = PacketSourceIdentityV1(binding=binding, packet_id=action_id,
                packet_revision=values["operator.packet_revision"], packet_hash=values["operator.packet_hash"],
                observations=[PacketObservationRefV1(identity=key, revision=obs.revision, evidence_ref=obs.evidence_ref)
                              for key, obs in facts.items()], recipient=values["operator.recipient"],
                owner=values["ownership.owner"], owner_state=values["ownership.state"],
                state_revision=values["ownership.state_revision"], epoch=values["ownership.epoch"])
            policy = PacketPolicyRefV1(profile_id=self.profile.profile_id, profile_version=self.profile.version,
                profile_hash=self.profile.release_hash, process_version=checkpoint.process_version,
                process_hash=self.profile.process_hash, policy_id="synthetic-test-policy-v1",
                policy_hash=self.profile.policy_hash, observed_version=values["policy.version"], references=["synthetic-test-policy-v1"])
            content = PacketContentV1(source=identity, catalog=catalog, access=access, as_of=snapshot_at,
                history=history, generation_stops=stops, policy=policy, conflicts=conflicts,
                unknowns=unknowns, disposition=disposition, expires_at=min(checkpoint.deadline, access.expires_at))
            validate_packet_policy(content, self.profile, process_version=checkpoint.process_version, policy_version=checkpoint.policy_version)
            packet = OperatorPacket(packet_id=action_id, case_id=case_id, object_id=binding.object_id, binding=binding,
                packet_hash=identity.packet_hash, packet_revision=identity.packet_revision, owner=identity.owner,
                owner_state=identity.owner_state, epoch=identity.epoch, state_revision=identity.state_revision,
                source_scope=[ref.identity for ref in identity.observations], expires_at=content.expires_at, replay_id=action_id)
            return PreparedPacketV1(packet=packet, content=content, content_hash=fingerprint(content.model_dump(mode="json")),
                checkpoint_hash=source.checkpoint_hash)
        except Exception:
            raise GateDenied("scope_denied") from None
