"""Immutable private synthetic companions; constructing one grants no authority."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Callable, Literal
from pydantic import TypeAdapter
from proofkey.contracts import (ArtifactRecord, AuthContext, AuthorityObservation, CanonicalRequest, EvidenceAssertion,
    EnvironmentProfile, Identifier, InvocationReservation, PhaseCheckpoint, ProcessingReceipt, RequestBinding)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def json_bytes(payload):
    if type(payload) is not bytes or not 0 < len(payload) <= 8388608:
        raise ValueError("Finite canonical bytes required")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def reject(value):
        raise ValueError("Nonfinite JSON")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)
        if canonical(value) != payload:
            raise ValueError("Canonical JSON required")
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("Finite UTF-8 canonical JSON required") from exc
    return value


def model_bytes(model, payload):
    value = model.model_validate(json_bytes(payload))
    if canonical(value.model_dump(mode="json")) != payload:
        raise ValueError("Exact typed canonical snapshot required")
    return value


def hash_value(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Exact SHA256 required")


def byte_tuple(value, model, ceiling):
    if type(value) is not tuple or len(value) > ceiling:
        raise ValueError("Finite immutable tuple required")
    for payload in value:
        model_bytes(model, payload)


class ProcessingPublicationError(ValueError):
    def __init__(self, code):
        if code not in {"scope_denied", "input_unavailable", "not_reserved", "not_complete",
                "identity_mismatch", "output_invalid", "partial_publication", "publication_conflict"}:
            raise ValueError("Unknown publication error code")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SavedOriginalScope:
    binding_bytes: bytes
    original_request_hash: str
    scope_id: str
    scope_bytes: bytes
    policy_id: str
    provenance: Literal["synthetic_host_registration"]
    authorization_reference: str
    expires_at: datetime

    def __post_init__(self):
        binding, scope = self.binding(), self.scope()
        keys = {"allowed_actors", "case_id", "object_id", "binding_hash", "original_request_hash",
            "scope_id", "policy_id", "authorization_reference", "provenance", "expires_at"}
        if type(scope) is not dict or set(scope) != keys:
            raise ValueError("Closed saved-original scope required")
        actors = scope["allowed_actors"]
        if (type(actors) is not list or not 1 <= len(actors) <= 16
                or any(type(a) is not str or not a or a == "*" for a in actors)
                or actors != sorted(set(actors))):
            raise ValueError("Finite registered actor set required")
        for actor in actors:
            TypeAdapter(Identifier).validate_python(actor)
        if (not isinstance(self.expires_at, datetime) or self.expires_at.utcoffset() is None
                or self.provenance != "synthetic_host_registration"
                or any(type(getattr(self, n)) is not str or not getattr(self, n)
                       for n in ("scope_id", "policy_id", "authorization_reference"))):
            raise ValueError("Exact synthetic scope identity required")
        for name in ("scope_id", "policy_id", "authorization_reference"):
            TypeAdapter(Identifier).validate_python(getattr(self, name))
        hash_value(self.original_request_hash)
        expected = dict(case_id=binding.case_id, object_id=binding.object_id,
            binding_hash=digest(self.binding_bytes), original_request_hash=self.original_request_hash,
            scope_id=self.scope_id, policy_id=self.policy_id, provenance=self.provenance,
            authorization_reference=self.authorization_reference, expires_at=self.expires_at.isoformat())
        if any(scope[k] != v for k, v in expected.items()):
            raise ValueError("Scope identity differs from immutable companion")

    def binding(self):
        return model_bytes(RequestBinding, self.binding_bytes)

    def scope(self):
        return json_bytes(self.scope_bytes)


@dataclass(frozen=True, slots=True)
class ProcessingCatalogBindings:
    original_lookup: Callable[[RequestBinding], CanonicalRequest]
    checkpoint_lookup: Callable[[RequestBinding], PhaseCheckpoint]
    invocation_lookup: Callable[[str], tuple[InvocationReservation, ProcessingReceipt | None]]
    original_scope: Callable[[RequestBinding, CanonicalRequest, AuthContext, str], SavedOriginalScope | None]
    max_publication_bytes: int = 8388608
    max_inputs: int = 16
    max_output_items: int = 256
    max_claim_bytes: int = 65536
    max_ancestry_depth: int = 16
    max_ancestry_records: int = 64
    profile_lookup: Callable[[RequestBinding, CanonicalRequest], EnvironmentProfile] | None = None

    def __post_init__(self):
        if self.profile_lookup is not None and not callable(self.profile_lookup):
            raise TypeError("Trusted profile lookup required")
        for name in ("original_lookup", "checkpoint_lookup", "invocation_lookup", "original_scope"):
            if not callable(getattr(self, name)):
                raise TypeError("Trusted constructor-owned callable required")
        for name, ceiling in (("max_publication_bytes", 8388608), ("max_inputs", 16),
            ("max_output_items", 256), ("max_claim_bytes", 65536),
            ("max_ancestry_depth", 16), ("max_ancestry_records", 64)):
            if type(getattr(self, name)) is not int or not 0 < getattr(self, name) <= ceiling:
                raise ValueError("Finite positive tightened limit required")


@dataclass(frozen=True, slots=True)
class InputPublication:
    binding_bytes: bytes
    invocation_id: str
    reservation_identity_hash: str
    input_record_bytes: tuple[bytes, ...]
    envelope_bytes: bytes
    envelope_hash: str

    def __post_init__(self):
        self.binding()
        byte_tuple(self.input_record_bytes, ArtifactRecord, 16)
        hash_value(self.reservation_identity_hash)
        hash_value(self.envelope_hash)
        envelope = json_bytes(self.envelope_bytes)
        if digest(self.envelope_bytes) != self.envelope_hash or type(self.invocation_id) is not str or not self.invocation_id:
            raise ValueError("Envelope identity mismatch")
        if (envelope.get("binding") != self.binding().model_dump(mode="json")
                or envelope.get("invocation_id") != self.invocation_id
                or envelope.get("reservation_identity_hash") != self.reservation_identity_hash
                or envelope.get("input_records") != [r.model_dump(mode="json") for r in self.input_records()]):
            raise ValueError("Envelope companion joins differ")

    def binding(self):
        return model_bytes(RequestBinding, self.binding_bytes)

    def input_records(self):
        return tuple(model_bytes(ArtifactRecord, b) for b in self.input_record_bytes)


@dataclass(frozen=True, slots=True)
class ProcessingPublication:
    binding_bytes: bytes
    invocation_id: str
    receipt_hash: str
    output_hashes: tuple[str, ...]
    input_record_bytes: tuple[bytes, ...]
    assertion_bytes: tuple[bytes, ...]
    assertion_refs: tuple[str, ...]
    transcript_record_bytes: bytes | None
    proposal_receipt_ref: str | None
    marker_bytes: bytes
    marker_hash: str
    status: Literal["completed"] = "completed"
    mode: Literal["synthetic"] = "synthetic"

    def __post_init__(self):
        self.binding()
        hash_value(self.receipt_hash)
        hash_value(self.marker_hash)
        if type(self.output_hashes) is not tuple or len(self.output_hashes) != 1:
            raise ValueError("One exact saved output hash required")
        for h in self.output_hashes:
            hash_value(h)
        byte_tuple(self.input_record_bytes, ArtifactRecord, 16)
        byte_tuple(self.assertion_bytes, EvidenceAssertion, 256)
        if type(self.assertion_refs) is not tuple or len(self.assertion_refs) != len(self.assertion_bytes):
            raise ValueError("Exact assertion references required")
        for ref in self.assertion_refs:
            if type(ref) is not str or not ref.startswith("private-assertion-"):
                raise ValueError("Fixed private assertion identity required")
            hash_value(ref[len("private-assertion-"):])
        if self.proposal_receipt_ref is not None:
            if type(self.proposal_receipt_ref) is not str or not self.proposal_receipt_ref.startswith("private-proposal-"):
                raise ValueError("Fixed private proposal identity required")
            hash_value(self.proposal_receipt_ref[len("private-proposal-"):])
        if self.transcript_record_bytes is not None:
            model_bytes(ArtifactRecord, self.transcript_record_bytes)
        if sum(bool(v) for v in (self.assertion_bytes, self.transcript_record_bytes, self.proposal_receipt_ref)) > 1:
            raise ValueError("Role publication fields are exclusive")
        marker = json_bytes(self.marker_bytes)
        if (digest(self.marker_bytes) != self.marker_hash or self.status != "completed"
                or self.mode != "synthetic" or type(self.invocation_id) is not str or not self.invocation_id):
            raise ValueError("Exact completed synthetic marker required")
        expected = {"binding": self.binding().model_dump(mode="json"), "invocation_id": self.invocation_id,
            "receipt_hash": self.receipt_hash, "output_hashes": list(self.output_hashes),
            "input_records": [r.model_dump(mode="json") for r in self.input_records()],
            "assertions": [a.model_dump(mode="json") for a in self.assertions()],
            "assertion_refs": list(self.assertion_refs), "proposal_receipt_ref": self.proposal_receipt_ref,
            "transcript_record": None if self.transcript_record_bytes is None else self.transcript_record().model_dump(mode="json"),
            "status": self.status, "mode": self.mode}
        if type(marker) is not dict or set(marker) != set(expected) | {"control_hash"} or any(marker[k] != v for k, v in expected.items()):
            raise ValueError("Marker companion joins differ")
        hash_value(marker["control_hash"])

    def binding(self):
        return model_bytes(RequestBinding, self.binding_bytes)

    def input_records(self):
        return tuple(model_bytes(ArtifactRecord, b) for b in self.input_record_bytes)

    def assertions(self):
        return tuple(model_bytes(EvidenceAssertion, b) for b in self.assertion_bytes)

    def transcript_record(self):
        return None if self.transcript_record_bytes is None else model_bytes(ArtifactRecord, self.transcript_record_bytes)


def _publication_value(publication):
    """Exact field names; immutable bytes become canonical JSON values, never aliases."""
    if type(publication) is not ProcessingPublication:
        raise ValueError("Exact processing publication required")
    return {"binding_bytes": json_bytes(publication.binding_bytes),
        "invocation_id": publication.invocation_id, "receipt_hash": publication.receipt_hash,
        "output_hashes": list(publication.output_hashes),
        "input_record_bytes": [json_bytes(b) for b in publication.input_record_bytes],
        "assertion_bytes": [json_bytes(b) for b in publication.assertion_bytes],
        "assertion_refs": list(publication.assertion_refs),
        "transcript_record_bytes": None if publication.transcript_record_bytes is None else json_bytes(publication.transcript_record_bytes),
        "proposal_receipt_ref": publication.proposal_receipt_ref,
        "marker_bytes": json_bytes(publication.marker_bytes), "marker_hash": publication.marker_hash,
        "status": publication.status, "mode": publication.mode}


def _publication_from_bytes(payload):
    value = json_bytes(payload)
    if type(value) is not dict or set(value) != set(ProcessingPublication.__dataclass_fields__):
        raise ValueError("Closed exact publication fields required")
    for name, cap in (("output_hashes", 1), ("input_record_bytes", 16),
            ("assertion_bytes", 256), ("assertion_refs", 256)):
        if type(value[name]) is not list or len(value[name]) > cap:
            raise ValueError("Finite exact publication sequence required")
    publication = ProcessingPublication(binding_bytes=canonical(value["binding_bytes"]),
        invocation_id=value["invocation_id"], receipt_hash=value["receipt_hash"],
        output_hashes=tuple(value["output_hashes"]),
        input_record_bytes=tuple(canonical(r) for r in value["input_record_bytes"]),
        assertion_bytes=tuple(canonical(a) for a in value["assertion_bytes"]),
        assertion_refs=tuple(value["assertion_refs"]),
        transcript_record_bytes=None if value["transcript_record_bytes"] is None else canonical(value["transcript_record_bytes"]),
        proposal_receipt_ref=value["proposal_receipt_ref"], marker_bytes=canonical(value["marker_bytes"]),
        marker_hash=value["marker_hash"], status=value["status"], mode=value["mode"])
    if canonical(_publication_value(publication)) != payload:
        raise ValueError("Exact canonical publication roundtrip required")
    return publication


@dataclass(frozen=True, slots=True)
class PlanningEvidenceInputV2:
    checkpoint_bytes: bytes
    observation_bytes: tuple[bytes, ...]
    extraction_publication_bytes: tuple[bytes, ...]
    envelope_bytes: bytes
    envelope_hash: str

    def __post_init__(self):
        checkpoint = self.checkpoint()
        byte_tuple(self.observation_bytes, AuthorityObservation, 64)
        if (type(self.extraction_publication_bytes) is not tuple
                or not 0 < len(self.extraction_publication_bytes) <= 16):
            raise ValueError("Nonempty bounded immutable extraction tuple required")
        publications = self.extraction_publications()
        observations = self.observations()
        if any(o.object_id != checkpoint.binding.object_id for o in observations):
            raise ValueError("Observations differ from exact checkpoint object")
        if len({p.invocation_id for p in publications}) != len(publications):
            raise ValueError("Distinct exact extraction invocations required")
        count, direct = 0, {}
        for publication in publications:
            if (publication.binding() != checkpoint.binding
                    or publication.transcript_record_bytes is not None or publication.proposal_receipt_ref is not None):
                raise ValueError("Exact completed extraction publication required")
            records = publication.input_records()
            if not records or len({r.artifact_id for r in records}) != len(records):
                raise ValueError("Distinct actual publication inputs required")
            parents = {r.artifact_id: r for r in records}
            for record in records:
                if record.case_id != checkpoint.binding.case_id:
                    raise ValueError("Foreign direct record")
                if record.artifact_id in direct and direct[record.artifact_id] != record:
                    raise ValueError("Conflicting direct record")
                direct[record.artifact_id] = record
            for index, assertion in enumerate(publication.assertions()):
                record = parents.get(assertion.artifact_id)
                payload = publication.assertion_bytes[index]
                ref = "private-assertion-" + digest(canonical({"domain": "proofkey-saved-assertion-v1",
                    "receipt_hash": publication.receipt_hash, "index": index, "bytes_hash": digest(payload)}))
                if (record is None or assertion.processing_receipt_id != publication.invocation_id
                        or assertion.content_hash != record.original_hash or assertion.lineage_hash != record.lineage_hash
                        or len(assertion.claim.encode("utf-8")) > 65536 or publication.assertion_refs[index] != ref):
                    raise ValueError("Exact assertion lineage/reference required")
                count += 1
        if not 0 < count <= 256 or len(direct) > 16:
            raise ValueError("Aggregate evidence ceiling")
        hash_value(self.envelope_hash)
        value = json_bytes(self.envelope_bytes)
        pending = [(value, 0)]
        while pending:
            node, depth = pending.pop()
            if depth > 16:
                raise ValueError("Excessive envelope shape")
            if type(node) is dict:
                pending.extend((v, depth + 1) for v in node.values())
            elif type(node) is list:
                pending.extend((v, depth + 1) for v in node)
        expected = {"version": "planning-evidence-input-v2", "checkpoint": checkpoint.model_dump(mode="json"),
            "authority_observations": [o.model_dump(mode="json") for o in observations],
            "extraction_publications": [_publication_value(p) for p in publications]}
        if (type(value) is not dict or set(value) != set(expected) or value != expected
                or digest(self.envelope_bytes) != self.envelope_hash):
            raise ValueError("Exact V2 envelope/companion/hash join required")

    @classmethod
    def from_bytes(cls, payload):
        value = json_bytes(payload)
        if (type(value) is not dict or set(value) != {"version", "checkpoint", "authority_observations", "extraction_publications"}
                or value["version"] != "planning-evidence-input-v2"
                or type(value["authority_observations"]) is not list or len(value["authority_observations"]) > 64
                or type(value["extraction_publications"]) is not list or not 0 < len(value["extraction_publications"]) <= 16):
            raise ValueError("Closed bounded exact V2 envelope required")
        return cls(canonical(value["checkpoint"]), tuple(canonical(o) for o in value["authority_observations"]),
            tuple(canonical(p) for p in value["extraction_publications"]), payload, digest(payload))

    def checkpoint(self):
        return model_bytes(PhaseCheckpoint, self.checkpoint_bytes)

    def observations(self):
        return tuple(model_bytes(AuthorityObservation, b) for b in self.observation_bytes)

    def extraction_publications(self):
        return tuple(_publication_from_bytes(b) for b in self.extraction_publication_bytes)
