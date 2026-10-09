"""Tagged internal storage contracts; stored scope is never source authority."""
from datetime import timedelta
from typing import Literal

from pydantic import model_validator

from .contracts import (Hash, Identifier, NonnegativeInt, OwnerState, PhaseCheckpoint,
                        ProcessEdge, ProcessSpec, ReadTarget, RequestBinding, Revision, ScopedReply,
                        Timestamp, WaitState, WireModel)
from .identity import fingerprint, stable_action_id


class ControlReadScopeV1(WireModel):
    kind: Literal["control_read_v1"] = "control_read_v1"
    binding: RequestBinding
    original_input_hash: Hash
    target: ReadTarget
    purpose: Literal["stop", "reply", "recorded_state"]

    @model_validator(mode="after")
    def narrow_target(self):
        allowed = {"case": {"binding", "request_revision", "authorization", "generation"},
                   "customer": {"consent_revision"},
                   "ownership": {"state", "state_revision", "epoch", "owner"}}
        if (self.target.kind != "authority_facts" or self.target.authority not in allowed
                or not set(self.target.facts) <= allowed[self.target.authority]
                or len(set(self.target.facts)) != len(self.target.facts)):
            raise ValueError("Control read requires a narrow identity/owner fact target")
        return self


class RefusalAdmissionHistoryV1(WireModel):
    kind: Literal["stopped_reschedule_refusal_v1"] = "stopped_reschedule_refusal_v1"
    predecessor: PhaseCheckpoint
    predecessor_input_hash: Hash
    successor_binding: RequestBinding

    @model_validator(mode="after")
    def exact_predecessor(self):
        old, new = self.predecessor.binding, self.successor_binding
        if (not self.predecessor.stop.requested or new.supersedes_generation != old.generation
                or new.generation == old.generation or new.request_id == old.request_id
                or (new.case_id, new.object_id, new.principal_id) != (old.case_id, old.object_id, old.principal_id)):
            raise ValueError("Refusal history requires an exact stopped predecessor")
        return self


class WaitRecordV1(WireModel):
    kind: Literal["wait_record_v1"] = "wait_record_v1"
    wait: WaitState
    origin_checkpoint: PhaseCheckpoint
    origin_hash: Hash
    process: ProcessSpec
    profile_hash: Hash
    policy_hash: Hash
    owner_id: Identifier
    owner_state: OwnerState
    owner_revision: Revision
    owner_epoch: NonnegativeInt
    recipient_role: Identifier
    wait_phase: Identifier
    communication_edge: ProcessEdge
    communication_stage: Literal["send", "enqueue"]
    communication_action_id: Identifier
    accept_edge: ProcessEdge
    expiry_edge: ProcessEdge
    created_at: Timestamp
    lifecycle: Literal["pending", "answered", "expired", "stopped"] = "pending"
    accepted_reply_hash: Hash | None = None
    accepted_actor: Identifier | None = None
    accepted_reply: ScopedReply | None = None
    successor_hash: Hash | None = None

    @model_validator(mode="after")
    def complete_scope(self):
        from .process import validate_process
        validate_process(self.process)
        process_data = self.process.model_dump(mode="json")
        cp, wait = self.origin_checkpoint, self.wait
        if (self.process.release_hash != fingerprint({k: v for k, v in process_data.items() if k != "release_hash"})
                or self.process.version != cp.process_version
                or self.origin_hash != fingerprint(cp.model_dump(mode="json"))):
            raise ValueError("Wait origin/process hash or version mismatch")
        if (wait.binding != cp.binding or wait.origin != cp.phase or wait.budget != cp.budget
                or cp.stop.requested or cp.question_id is not None
                or (self.owner_state, self.owner_revision, self.owner_epoch) !=
                   (cp.ownership_state, cp.ownership_state_revision, cp.ownership_epoch)
                or wait.owner_state_revision != self.owner_revision):
            raise ValueError("Wait differs from immutable original control context")
        expected_stage = {"send_clarification": "send", "enqueue_handoff": "enqueue"}
        edge = self.communication_edge
        if (edge not in self.process.edges or edge.origin != cp.phase or edge.target != self.wait_phase
                or edge.operation not in expected_stage or expected_stage[edge.operation] != self.communication_stage
                or self.communication_action_id != stable_action_id(cp.binding, edge.operation, self.communication_stage)):
            raise ValueError("Wait requires the exact declared physical communication edge")
        matching = [w for w in self.process.waits if w.phase == self.wait_phase]
        if len(matching) != 1:
            raise ValueError("Wait phase requires an unambiguous declared scope")
        contract = matching[0]
        if (wait.next_gate != contract.next_gate or wait.awaited_fields != contract.awaited_fields
                or self.recipient_role != contract.recipient_role
                or wait.expires_at <= self.created_at or wait.expires_at > cp.deadline
                or wait.expires_at > self.created_at + timedelta(seconds=contract.expiry_seconds)):
            raise ValueError("Wait fields/role/finite expiry differ from graph contract")
        if (self.accept_edge not in self.process.edges or self.accept_edge.origin != self.wait_phase
                or self.accept_edge.target != wait.next_gate or not self.accept_edge.operation.startswith("accept_")
                or self.expiry_edge not in self.process.edges or self.expiry_edge.origin != self.wait_phase
                or self.expiry_edge.operation != "expire_wait"):
            raise ValueError("Wait continuation must retain its declared accept/expiry edges")
        if self.lifecycle == "pending" and any((self.accepted_reply_hash, self.accepted_actor, self.accepted_reply, self.successor_hash)):
            raise ValueError("Pending question cannot claim a disposition")
        if self.lifecycle == "answered" and not all((self.accepted_reply_hash, self.accepted_actor, self.accepted_reply, self.successor_hash)):
            raise ValueError("Answered question requires its reply/actor/successor receipt")
        if self.lifecycle == "answered":
            reply = self.accepted_reply
            if (self.accepted_reply_hash != fingerprint(reply.model_dump(mode="json"))
                    or self.accepted_actor != reply.actor_id or reply.actor_id != wait.recipient
                    or reply.question_id != wait.question_id or reply.binding != wait.binding
                    or reply.request_revision != wait.binding.request_revision
                    or reply.consent_revision != wait.binding.consent_revision
                    or reply.owner_state_revision != self.owner_revision
                    or set(reply.fields) != set(wait.awaited_fields)
                    or not self.created_at <= reply.received_at < wait.expires_at):
                raise ValueError("Private accepted reply must match its exact canonical receipt and question scope")
        if self.lifecycle in {"expired", "stopped"} and (self.successor_hash is None or self.accepted_reply_hash is not None
                                                        or self.accepted_actor is not None or self.accepted_reply is not None):
            raise ValueError("Expiry/stop cannot synthesize an accepted reply")
        return self
