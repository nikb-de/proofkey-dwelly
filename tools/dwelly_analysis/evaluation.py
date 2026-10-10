"""Literal, non-scoring comparison against separate, unvalidated author labels."""
from .widget import check_json


def compare(candidate, reference):
    check_json(candidate); check_json(reference)
    if type(candidate) is not dict or type(reference) is not dict:
        raise ValueError("Invalid comparison object")
    if candidate.get("schema_version") != "proofkey-step-candidate-v1" or reference.get("schema_version") != "proofkey-step-reference-v1":
        raise ValueError("Invalid comparison schema")
    input_hash = candidate.get("input_hash")
    if type(input_hash) is not str or len(input_hash) != 64 or input_hash != reference.get("input_hash"):
        raise ValueError("Comparison input binding mismatch")
    for value in (candidate, reference):
        if type(value.get("waiting_for")) is not list or any(type(x) is not str for x in value["waiting_for"]):
            raise ValueError("Invalid wait targets")
    return {"schema_version": "proofkey-step-comparison-v1", "input_hash": input_hash,
            "state_agreement": candidate.get("state") == reference.get("state"),
            "wait_target_agreement": sorted(candidate["waiting_for"]) == sorted(reference["waiting_for"]),
            "qualification": "mechanical_comparison_only", "accuracy_score": None}
