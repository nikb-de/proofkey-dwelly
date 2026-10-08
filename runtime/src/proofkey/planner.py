"""Strict finite step suggestions. Only the separate policy/gateway may dispatch."""
from types import MappingProxyType
from proofkey.contracts import ProposalOutput
from proofkey.journal import JournalFailure
from proofkey.providers.invocations import output_digest


def validated_proposal(store, receipt, expected_identity):
    attempt, saved = store.invocation(receipt.invocation_id)
    if (saved != receipt or attempt.identity != expected_identity or attempt.status != "completed"
            or receipt.role != "planning" or receipt.status != "completed"
            or receipt.mode not in {"synthetic", "actual"} or not isinstance(receipt.output, ProposalOutput)
            or receipt.output_hashes != [output_digest(receipt.output)]):
        raise JournalFailure("Proposal requires exact durable complete planning receipt")
    return receipt.output.proposal


class BoundedPlanner:
    def __init__(self, processor, service, *, allowed_steps, usage_ceiling):
        self.processor, self.service = processor, service
        self.allowed_steps = MappingProxyType({op: MappingProxyType({stage: frozenset(keys)
            for stage, keys in stages.items()}) for op, stages in allowed_steps.items()})
        self.usage_ceiling = dict(usage_ceiling)

    def propose(self, checkpoint, observations):
        identity = self.service.processor_identity
        if (checkpoint.binding.case_id, checkpoint.binding.generation, checkpoint.profile_version,
                checkpoint.process_version) != (identity.case_id, identity.generation,
                                                identity.profile_version, identity.process_version):
            raise JournalFailure("Planner checkpoint differs from frozen identity")
        def invoke():
            receipt = self.processor(checkpoint, observations)
            if not isinstance(receipt.output, ProposalOutput):
                raise ValueError("Planning output must be a typed proposal")
            proposal = receipt.output.proposal
            allowed = self.allowed_steps.get(proposal.operation, {}).get(proposal.stage)
            if allowed is None or not set(proposal.arguments) <= allowed:
                raise ValueError("Proposal expands allowed operation/stage/argument scope")
            refs = {item.evidence_ref for item in observations}
            if not set(proposal.evidence_refs) <= refs:
                raise ValueError("Proposal references absent observations")
            return receipt
        receipt = self.service.call("planning", identity.input_hashes, self.usage_ceiling, invoke)
        validated_proposal(self.service.store, receipt, identity)
        return receipt
