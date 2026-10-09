"""Escaped deterministic explanatory projections; never activation input."""
from html import escape
import json
from ..contracts import ProcessSpec
from ..identity import fingerprint
from ..process import validate_process


def derive_view(process, release_hash):
    spec = ProcessSpec.model_validate(process.model_dump(mode="json"))
    validate_process(spec)
    raw = spec.model_dump(mode="json")
    digest = fingerprint({key: value for key, value in raw.items() if key != "release_hash"})
    def label(value):
        return escape(str(value), quote=True).replace("\n", "&#10;").replace("\r", "&#13;")
    lines = ["Process view (explanatory; no approval or activation)",
             "Process: " + label(spec.process_id) + " / " + label(spec.version),
             "Computed process/source hash: " + digest, "Declared process hash reference: " + label(spec.release_hash),
             "Release context reference: " + label(release_hash), "Source identity: " + label(spec.process_id)]
    for phase in spec.phases:
        lines.append("Phase: " + label(phase))
    for operation in spec.operations:
        lines.append("Operation: " + label(operation))
    for edge in spec.edges:
        lines.append("Edge: " + label(edge.origin) + " -- " + label(edge.operation) + " --> " + label(edge.target)
                     + ("; condition=" + label(edge.condition) if edge.condition is not None else ""))
    for req in spec.prerequisites:
        lines.append("Readiness: " + label(req.phase) + "; " + label(req.authority + "." + req.fact)
                     + " == " + label(json.dumps(req.expected, sort_keys=True, ensure_ascii=False)))
    for wait in spec.waits:
        lines.append("Wait: " + label(wait.phase) + " -> " + label(wait.next_gate) + "; recipient role="
                     + label(wait.recipient_role) + "; fields=" + label(", ".join(wait.awaited_fields))
                     + "; expiry seconds=" + label(wait.expiry_seconds))
    for approval in spec.approvals:
        lines.append("Approval: " + label(approval.operation) + "; approver role=" + label(approval.approver_role)
                     + "; scope=" + label(", ".join(approval.required_scope)))
    for name, contracts in (("Acknowledgement", spec.acknowledgements), ("Readback", spec.readbacks)):
        for operation, contract in sorted(contracts.items()):
            lines.append(name + ": " + label(operation) + "; " + label(json.dumps(contract.model_dump(mode="json"), sort_keys=True)))
    lines.append("Completion: " + label(spec.completion.phase) + "; required operations="
                 + label(", ".join(spec.completion.required_operations)))
    return "\n".join(lines) + "\n"
