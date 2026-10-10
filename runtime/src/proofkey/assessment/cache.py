"""Exact content-domain assessment cache identities; old scores remain history."""
from proofkey.identity import fingerprint
from .contracts import require_hash


def cache_key(candidate_hash, input_hash, output_hash, grader_hash, label_hash, rubric_hash, lineage_hash):
    values = (candidate_hash, input_hash, output_hash, grader_hash, label_hash, rubric_hash, lineage_hash)
    names = ("candidate", "input", "output", "grader", "label", "rubric", "lineage")
    return fingerprint({"domain": "proofkey-offline-assessment-cache-v1",
                        **{name: require_hash(value) for name, value in zip(names, values)}})
