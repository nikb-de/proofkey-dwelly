"""Rights-cleared private derivatives; no deletion or publication."""
from proofkey.evidence.catalog import EvidenceCatalog, EvidenceAccessDenied


def redact_derivative(record, rule_set, rights, *, catalog=None, auth=None):
    """Text derivative from reviewed policy and rights IDs in trusted constructor.

    Neither rules nor rights may be self-attested dictionaries. Media redaction
    needs a separate reviewed codec route; this implementation permits UTF-8
    text/transcript only. Derivative scope is intersected with original scope.
    """
    if not isinstance(catalog, EvidenceCatalog):
        raise EvidenceAccessDenied("Trusted catalog and scoped authorization required")
    record = catalog.resolve_record(record, auth, purpose="redact")
    policy = catalog.derivative_policies.get(rule_set) if isinstance(rule_set, str) else None
    if not policy or not isinstance(rights, str) or policy.get("rights_reference") != rights:
        raise EvidenceAccessDenied("Reviewed redaction rules and rights are required")
    replacements = policy.get("replacements")
    if not replacements or not all(isinstance(key, str) and key and isinstance(value, str)
                                   for key, value in replacements.items()):
        raise EvidenceAccessDenied("Specific reviewed text replacement rules required")
    if record.mime_type not in ("text/plain", "text/x-supplied-transcript"):
        raise EvidenceAccessDenied("Reviewed codec redaction route unavailable")
    payload = catalog.read_original(record.artifact_id, auth, purpose="redact")
    text = payload.decode("utf-8", errors="strict")
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    derivative = text.encode("utf-8")
    if len(derivative) > catalog.max_bytes:
        raise ValueError("Derivative byte ceiling exceeded")
    _, envelope = catalog._load(record.artifact_id)
    actors = [actor for actor in envelope["scope"]["allowed_actors"] if actor in policy.get("allowed_actors", ())]
    if not actors:
        raise EvidenceAccessDenied("Derivative scope would be empty")
    scope = {**envelope["scope"], "allowed_actors": actors}
    return catalog._persist(derivative, record.case_id, "redacted_derivative", scope, record.mime_type,
                            parents=[record.original_hash], policy={"rule_set": rule_set, "rights": rights})
