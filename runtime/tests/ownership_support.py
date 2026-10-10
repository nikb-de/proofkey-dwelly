"""Trusted, task-local synthetic setup; never runtime initial-owner activation."""
from datetime import timedelta
import json
import os
from pathlib import Path

from proofkey.adapters.world import SimulatedWorld
from proofkey.contracts import TransferIntent, RevisionVector
from proofkey.gateway import ActionGateway
from proofkey.identity import fingerprint, stable_action_id
from proofkey.journal import CaseStore
from proofkey.ownership_contracts import (OwnershipPacketV1, OwnershipProcessRegistryV1,
    TransferArgumentsV1, OriginalTransferIdentityV1, TransferPostconditionV1)
from proofkey.ownership_contracts import SyntheticTargetAcceptanceV1, TRANSFER_FIELDS_V1
from proofkey.profiles import load_profile
from support import NOW, DEADLINE, FakeClock, make_auth, make_binding, make_checkpoint, make_request, make_intent

ROOT = Path(__file__).resolve().parents[1]


def fixture(profile, *, direct=False):
    raw = json.loads((ROOT / "fixtures/development/packet-world-v1.json").read_text())
    raw["facts"]["ownership.owner"]["value"] = "OP1"
    packet = OwnershipPacketV1(binding=make_binding(), packet_id="P1", packet_hash="b" * 64,
        packet_revision="v1", content_hash="c" * 64, accepted_owner="OP1", accepted_epoch=0,
        accepted_state_revision="v1", acceptance_evidence="synthetic-initial-packet-acceptance",
        accepted_at=NOW, simulated=True).model_dump(mode="json")
    authority = dict(kind="synthetic_ownership_fixture_v1", profile_id=profile.profile_id,
        profile_version=profile.version, profile_hash=profile.release_hash,
        process_hash=profile.process_hash, policy_hash=profile.policy_hash,
        request=make_request().model_dump(mode="json"), case_deadline=DEADLINE.isoformat().replace("+00:00", "Z"),
        packet=packet, grant_revision="v1", target_acceptances=[], fixture_hash="0" * 64, simulated=True)
    authority["grant"] = dict(kind="ownership_grant_v1", grant_id="synthetic-owner-grant",
        binding=make_binding().model_dump(mode="json"), actor_id="OP1", actor_type="human",
        packet_id="P1", packet_hash="b" * 64, packet_revision="v1", content_hash="c" * 64,
        owner="OP1", epoch=0, state_revision="v1", may_initiate_transfer=True, target_owners=["OP2"],
        decision_operations=["reschedule"], may_record_nonaction_decision=True,
        dispositions=["refund_review"], issued_at=(NOW-timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        expires_at=DEADLINE.isoformat().replace("+00:00", "Z"), evidence_ref="synthetic-owner-grant-evidence",
        fixture_hash="0" * 64, simulated=True)
    payload = {k: v for k, v in authority.items() if k != "fixture_hash"}
    payload["grant"] = {k: v for k, v in authority["grant"].items() if k != "fixture_hash"}
    digest = fingerprint(payload)
    authority["fixture_hash"] = authority["grant"]["fixture_hash"] = digest
    raw["ownership_authority"] = authority
    if direct:
        effect = fixture_effect(raw, profile)
        condition = TransferPostconditionV1.model_validate(effect.postcondition)
        instruction = SyntheticTargetAcceptanceV1(original=condition.original, packet=condition.packet,
            target_owner=condition.target_owner, expected_revisions=effect.expected_revisions, expires_at=DEADLINE,
            fixture_hash="0"*64, evidence_ref="synthetic-exact-target-acceptance", simulated=True).model_dump(mode="json")
        authority["target_acceptances"] = [instruction]
        payload = {k:v for k,v in authority.items() if k != "fixture_hash"}
        payload["grant"] = {k:v for k,v in authority["grant"].items() if k != "fixture_hash"}
        payload["target_acceptances"] = [{k:v for k,v in instruction.items() if k != "fixture_hash"}]
        digest = fingerprint(payload)
        authority["fixture_hash"] = authority["grant"]["fixture_hash"] = instruction["fixture_hash"] = digest
    return raw


def fixture_effect(raw, profile, revisions=None):
    packet = OwnershipPacketV1.model_validate(raw["ownership_authority"]["packet"])
    key = stable_action_id(packet.binding, "transfer_owner", "request")
    intent = TransferIntent(transfer_id=key, binding=packet.binding, case_id="C1", packet_id=packet.packet_id,
        packet_hash=packet.packet_hash, packet_revision=packet.packet_revision, expected_owner="OP1",
        expected_state_revision="v1", expected_epoch=0, target_owner="OP2", expires_at=DEADLINE)
    args = TransferArgumentsV1(intent=intent, content_hash=packet.content_hash,
        grant_id=raw["ownership_authority"]["grant"]["grant_id"], grant_revision="v1").model_dump(mode="json")
    original = OriginalTransferIdentityV1(binding=packet.binding, transfer_id=key,
        action_id=key, provider_key=key, argument_fingerprint=fingerprint(args))
    post = TransferPostconditionV1(original=original, packet=packet, target_owner="OP2", accepted_epoch=1)
    vector = {k:v["revision"] for k,v in raw["facts"].items() if k in TRANSFER_FIELDS_V1}
    vector.update({"operator.ownership_grant":"v1", "operator.ownership_packet":"v1"})
    return make_intent(operation="transfer_owner", stage="request", arguments=args,
        postcondition=post.model_dump(mode="json"), profile_version=profile.version,
        process_version=profile.processes["reschedule_window"].version,
        expected_revisions=revisions or RevisionVector(revisions=vector), ownership_state_revision="v1", ownership_epoch=0)


class Harness:
    def __init__(self, folder, *, registry=True, patch=None, direct=False, phase="wait_operator", clock=None):
        self.profile = load_profile("flat-v1.4")
        self.clock = clock or FakeClock()
        self.raw = fixture(self.profile, direct=direct)
        if patch:
            patch(self.raw)
        self.fixture_path = Path(folder) / "source.json"
        self.fixture_path.write_text(json.dumps(self.raw))
        self.world = SimulatedWorld(Path(folder) / "source.sqlite", self.fixture_path,
                                    profile=self.profile, clock=self.clock)
        self.registry = OwnershipProcessRegistryV1(profile_id=self.profile.profile_id,
            profile_version=self.profile.version, profile_hash=self.profile.release_hash,
            process_hash=self.profile.process_hash, policy_hash=self.profile.policy_hash,
            processes=self.profile.processes)
        self.journal_path = Path(folder) / "journal.sqlite"
        self.store = CaseStore(self.journal_path, ownership_processes=self.registry if registry else None)
        spec = self.profile.processes["reschedule_window"]
        self.store.admit(make_binding(), make_request(), make_checkpoint(profile_version=self.profile.version,
            process_version=spec.version, phase=phase, next_gate=phase,
            ownership_state="accepted", ownership_state_revision="v1", ownership_epoch=0))
        self.auth = make_auth(caller_id="OP1", proof_reference="synthetic-operator-proof")
        self.bundle = self.world.bundle()
        self.gateway = ActionGateway(self.profile, self.bundle, self.store, self.clock, self.auth)

    def transfer(self, **changes):
        packet = OwnershipPacketV1.model_validate(self.raw["ownership_authority"]["packet"])
        data = dict(transfer_id=stable_action_id(packet.binding, "transfer_owner", "request"),
            binding=packet.binding.model_dump(), case_id="C1", packet_id=packet.packet_id,
            packet_hash=packet.packet_hash, packet_revision=packet.packet_revision,
            expected_owner="OP1", expected_state_revision="v1", expected_epoch=0,
            target_owner="OP2", expires_at=DEADLINE)
        return TransferIntent.model_validate({**data, **changes})

    def effect(self):
        return fixture_effect(self.raw, self.profile)


class MonotonicClock(FakeClock):
    def __init__(self):
        super().__init__()
        self.seconds = 0.0

    def monotonic(self):
        return self.seconds

    def advance(self, seconds, *, utc=True):
        self.seconds += seconds
        if utc:
            super().advance(seconds)


def crash_driver(folder, boundary):
    """Genuine os._exit after actual forwarded public durable boundaries."""
    from proofkey.ownership import OwnershipService
    h = Harness(folder, direct=True)
    target, name, code = {
        "registration": (h.store, "register_transfer_atomic", 81),
        "debit": (h.store, "begin_registered_transfer", 82),
        "source_acceptance": (h.bundle.operator, "transfer_owner", 83),
        "terminal": (h.store, "apply_transfer_receipt_atomic", 84),
    }[boundary]
    actual = getattr(target, name)
    def exit_after(*args, **kwargs):
        actual(*args, **kwargs)
        import sys
        consumed = sorted({str(Path(m.__file__).resolve()) for m in sys.modules.values()
            if getattr(m,"__file__",None) and str(Path(m.__file__).resolve()).startswith(str(ROOT)+os.sep)})
        cp = h.store.checkpoint("C1")
        print(json.dumps({"genuine_exit_boundary":boundary,"exit_code":code,
            "tool_calls":cp.budget.tool_calls,"active_seconds_reserved_debt":cp.budget.active_seconds,
            "effects":cp.budget.effects,"actual_checkout_modules_before_exit":consumed}), flush=True)
        os._exit(code)
    setattr(target, name, exit_after)
    OwnershipService(h.profile, h.bundle, h.store, h.clock, gateway=h.gateway).transfer_result(h.transfer(), h.auth)
    raise AssertionError("Genuine exit boundary not reached")


def approval(h, *, decision_id="D1", expires_at=DEADLINE):
    from proofkey.contracts import OperatorDecision
    from proofkey.ownership_contracts import OperatorDecisionSubmissionV1, DecisionEffectScopeV1
    from proofkey.policy import required_fields, OWNER_FIELDS
    fields = required_fields(h.profile, "reschedule") | OWNER_FIELDS
    revisions = h.world.material_revisions().revisions
    effect = make_intent(profile_version=h.profile.version,
        process_version=h.profile.processes["reschedule_window"].version, ownership_state_revision="v1",
        ownership_epoch=0, decision_id=decision_id, deadline=expires_at,
        expected_revisions=RevisionVector(revisions={k:revisions[k] for k in fields}))
    decision = OperatorDecision(decision_id=decision_id, replay_id="R:"+decision_id, packet_id="P1",
        packet_hash="b"*64, packet_revision="v1", binding=make_binding(), owner="OP1", epoch=0,
        state_revision="v1", actor_id="OP1", proof_reference="synthetic-operator-proof", decision="approve",
        scope=["reschedule"], expires_at=expires_at, simulated=True)
    submission = OperatorDecisionSubmissionV1(decision=decision, content_hash="c"*64,
        effect_scope=DecisionEffectScopeV1(operation="reschedule", stage="commit", action_id=effect.action_id,
            argument_fingerprint=effect.argument_fingerprint))
    return submission, effect


if __name__ == "__main__":
    import sys
    crash_driver(sys.argv[1], sys.argv[2])
