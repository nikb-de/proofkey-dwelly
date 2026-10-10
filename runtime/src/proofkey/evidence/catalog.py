"""Trusted service catalog; construction and register scope are not request-body API.

The resolver receives (AuthContext, ArtifactRecord, immutable scope, purpose).
Only the literal True authorizes access. Roots, scope and derivative policies
are configured by the hosting service, never by narrative/model instructions.
"""
import hashlib
import json
import os
import stat
import uuid
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

from proofkey.contracts import ArtifactRecord, AuthContext, EvidenceAssertion, UnknownLocator, Locator
from pydantic import TypeAdapter
from proofkey.identity import fingerprint
from proofkey.evidence.processing_contracts import (InputPublication, ProcessingPublication,
    PlanningEvidenceInputV2, ProcessingPublicationError, SavedOriginalScope,
    _publication_value, canonical, digest, json_bytes, model_bytes)
from proofkey.contracts import (AuthorityObservation, CanonicalRequest, InvocationReservation,
    PhaseCheckpoint, ProcessingReceipt, RequestBinding)
from proofkey.identity import request_fingerprint


class EvidenceAccessDenied(PermissionError):
    pass


class EvidencePathError(ValueError):
    pass


def _publication_operation(operation):
    """Keep new public errors closed; never swallow process-exit/BaseException."""
    @wraps(operation)
    def checked(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except ProcessingPublicationError:
            raise
        except EvidenceAccessDenied:
            raise ProcessingPublicationError("scope_denied") from None
        except (EvidencePathError, OSError):
            raise ProcessingPublicationError("partial_publication") from None
        except Exception:
            raise ProcessingPublicationError("output_invalid") from None
    return checked


class UTCClock:
    def now(self):
        return datetime.now(timezone.utc)


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _safe_path(path):
    raw = os.fspath(path)
    if "://" in raw or "\x00" in raw:
        raise EvidencePathError("Only permitted local paths are accepted")
    if ".." in Path(raw).parts:
        raise EvidencePathError("Parent traversal is forbidden")
    path = Path(os.path.abspath(raw))
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise EvidencePathError("Symlink paths are forbidden")
    return path


def _open_parent(path):
    """Walk directories with no-follow descriptors, including ancestor races."""
    path = _safe_path(path)
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, path.name
    except BaseException:
        os.close(fd)
        raise


def _bounded_read(path, limit, *, private=False):
    directory = None
    try:
        directory, name = _open_parent(path)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise EvidencePathError("Not a permitted finite regular file")
            if private and info.st_mode & 0o077:
                raise EvidencePathError("Catalog storage permissions are not private")
            payload = stream.read(limit + 1)
    except OSError as exc:
        raise EvidencePathError("Local bytes unavailable") from exc
    finally:
        if directory is not None:
            os.close(directory)
    if len(payload) > limit:
        raise EvidencePathError("Byte limit exceeded")
    return payload


def _mime(payload, suffix):
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith(b"%PDF-"):
        return "application/pdf"
    if payload[:4] == b"RIFF" and payload[8:12] == b"WAVE":
        return "audio/wav"
    if payload.startswith(b"ID3") or payload[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    return {".txt": "text/plain", ".json": "application/json", ".transcript": "text/x-supplied-transcript",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".pdf": "application/pdf", ".wav": "audio/wav", ".mp3": "audio/mpeg"}.get(suffix.lower(), "application/octet-stream")


class EvidenceCatalog:
    def __init__(self, root, clock=None, *, allowed_input_roots, access_resolver,
                 max_bytes=8 * 1024 * 1024, derivative_policies=None, processing_bindings=None):
        if type(max_bytes) is not int or not 0 < max_bytes <= 8 * 1024 * 1024:
            raise ValueError("Catalog byte ceiling must be finite and at most 8 MiB")
        if not callable(access_resolver):
            raise ValueError("A trusted proof resolver is required")
        self.root = _safe_path(root)
        self.clock = clock or UTCClock()
        self.max_bytes = max_bytes
        self.allowed_input_roots = tuple(_safe_path(item) for item in allowed_input_roots)
        if not self.allowed_input_roots:
            raise ValueError("Explicit permitted input roots required")
        self.access_resolver = access_resolver
        from proofkey.evidence.processing_contracts import ProcessingCatalogBindings
        if processing_bindings is not None and type(processing_bindings) is not ProcessingCatalogBindings:
            raise TypeError("Exact processing catalog bindings required")
        self._processing_bindings = processing_bindings
        self.derivative_policies = _freeze(json.loads(json.dumps(derivative_policies or {}, allow_nan=False)))
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.stat().st_mode & 0o077:
            raise EvidencePathError("Catalog root must have private permissions")
        for name in ("objects", "records", "assertions", "receipts"):
            directory = _safe_path(self.root / name)
            directory.mkdir(exist_ok=True, mode=0o700)
            if directory.stat().st_mode & 0o077:
                raise EvidencePathError("Catalog directories must have private permissions")

    def read_permitted_local_bytes(self, path):
        path = _safe_path(path)
        if not any(path.is_relative_to(root) for root in self.allowed_input_roots):
            raise EvidencePathError("Input path is outside trusted roots")
        return _bounded_read(path, self.max_bytes)

    def _store(self, path, payload):
        if len(payload) > self.max_bytes:
            raise EvidencePathError("Catalog storage byte ceiling exceeded")
        path = _safe_path(path)
        directory = None
        try:
            directory, name = _open_parent(path)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        except FileExistsError:
            if _bounded_read(path, self.max_bytes, private=True) != payload:
                raise EvidencePathError("Stored content collision")
            return
        except OSError as exc:
            raise EvidencePathError("Private catalog storage unavailable") from exc
        finally:
            if directory is not None:
                os.close(directory)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    def _persist(self, payload, case_id, source, scope, mime, parents=(), policy=None):
        scope = json.loads(json.dumps(scope, allow_nan=False))
        if not isinstance(scope, dict) or not scope.get("allowed_actors") or not all(
                isinstance(actor, str) and actor for actor in scope["allowed_actors"]):
            raise ValueError("Trusted explicit source scope required")
        digest = hashlib.sha256(payload).hexdigest()
        identifier = "artifact-" + uuid.uuid4().hex
        record = ArtifactRecord(artifact_id=identifier, original_hash=digest, mime_type=mime,
            source=source, case_id=case_id, access="restricted", created_at=self.clock.now(),
            lineage_hash=fingerprint({"bytes": digest, "parents": list(parents), "scope": scope,
                                      "case": case_id, "source": source, "policy": policy}),
            parent_hashes=list(parents), source_reference="private-catalog:" + identifier)
        envelope = {"record": record.model_dump(mode="json"), "scope": scope, "policy": policy}
        encoded = json.dumps(envelope, sort_keys=True, allow_nan=False).encode()
        if len(encoded) > self.max_bytes:
            raise EvidencePathError("Catalog metadata byte ceiling exceeded")
        self._store(self.root / "objects" / digest, payload)
        self._store(self.root / "records" / (identifier + ".json"), encoded)
        return record

    def register(self, path, case_id, source, scope):
        payload = self.read_permitted_local_bytes(path)
        return self._persist(payload, case_id, source, scope, _mime(payload, Path(path).suffix))

    @_publication_operation
    def register_saved_narrative(self, binding: RequestBinding, auth: AuthContext) -> ArtifactRecord:
        original, scope = self._processing_scope(binding, auth, "provider_processing")
        if not original.narrative:
            raise ProcessingPublicationError("input_unavailable")
        payload = original.narrative.encode("utf-8")
        return self._processing_record(payload, binding, scope, auth,
            "saved-request-narrative", "text/plain", (),
            {"kind": "saved_narrative", "original_request_hash": scope.original_request_hash})

    @_publication_operation
    def register_planning_snapshot(self, checkpoint: PhaseCheckpoint,
            observations: tuple[AuthorityObservation, ...], auth: AuthContext) -> ArtifactRecord:
        if type(checkpoint) is not PhaseCheckpoint or type(observations) is not tuple:
            raise ProcessingPublicationError("identity_mismatch")
        original, scope = self._processing_scope(checkpoint.binding, auth, "provider_processing")
        from proofkey.contracts import EnvironmentProfile
        from proofkey.profiles import validate_profile
        from proofkey.process import validate_process
        try:
            lookup = self._processing_bindings.profile_lookup
            if lookup is None:
                raise ValueError("Registered local profile unavailable")
            profile = lookup(checkpoint.binding, original)
            if type(profile) is not EnvironmentProfile:
                raise ValueError("Exact registered profile required")
            profile = validate_profile(profile)
            spec = profile.processes[original.kind]
            validate_process(spec)
            if profile.version != checkpoint.profile_version or spec.version != checkpoint.process_version:
                raise ValueError("Registered profile/process version mismatch")
        except Exception as exc:
            raise ProcessingPublicationError("input_unavailable") from exc
        try:
            current = self._processing_bindings.checkpoint_lookup(checkpoint.binding)
            if type(current) is not PhaseCheckpoint or current != checkpoint:
                raise ValueError("Not the exact current pre-debit checkpoint")
            operations = {"reschedule", "register_goods_refusal", "register_service_refusal", "create_return"}
            if (checkpoint.stop.requested or checkpoint.phase in {"stop", "stopped", spec.completion.phase}
                    or checkpoint.next_gate not in operations or len([edge for edge in spec.edges
                        if edge.origin == checkpoint.phase and edge.operation == checkpoint.next_gate]) != 1):
                raise ValueError("No structurally selected business operation")
            if (len(observations) > 64 or any(type(o) is not AuthorityObservation
                    or o.object_id != checkpoint.binding.object_id for o in observations)):
                raise ValueError("Finite scoped typed observations required")
            payload = canonical({"checkpoint": checkpoint.model_dump(mode="json"),
                "observations": [o.model_dump(mode="json") for o in observations]})
        except Exception as exc:
            raise ProcessingPublicationError("identity_mismatch") from exc
        record = self._processing_record(payload, checkpoint.binding, scope, auth,
            "saved-planning-snapshot-v1", "application/json", (),
            {"kind": "planning_snapshot_v1", "checkpoint_hash": fingerprint(checkpoint.model_dump(mode="json"))})
        current = self._processing_bindings.checkpoint_lookup(checkpoint.binding)
        if type(current) is not PhaseCheckpoint or current != checkpoint:
            raise ProcessingPublicationError("identity_mismatch")
        self._processing_current_scope(checkpoint.binding, scope, auth)
        return record

    @_publication_operation
    def register_planning_evidence_snapshot(self, checkpoint: PhaseCheckpoint,
            observations: tuple[AuthorityObservation, ...], extraction_invocation_ids: tuple[str, ...],
            auth: AuthContext) -> ArtifactRecord:
        if (type(checkpoint) is not PhaseCheckpoint or type(observations) is not tuple
                or type(extraction_invocation_ids) is not tuple
                or not 0 < len(extraction_invocation_ids) <= 16
                or any(type(i) is not str or not i for i in extraction_invocation_ids)
                or len(set(extraction_invocation_ids)) != len(extraction_invocation_ids)):
            raise ProcessingPublicationError("identity_mismatch")
        # Detach exact validated snapshots before any actual lookup/I/O can mutate aliases.
        checkpoint = model_bytes(PhaseCheckpoint, canonical(checkpoint.model_dump(mode="json")))
        if len(observations) > 64 or any(type(o) is not AuthorityObservation for o in observations):
            raise ProcessingPublicationError("identity_mismatch")
        observations = tuple(model_bytes(AuthorityObservation, canonical(o.model_dump(mode="json")))
                             for o in observations)
        binding = checkpoint.binding
        original, scope = self._processing_scope(binding, auth, "provider_processing")
        self._planning_evidence_checkpoint(checkpoint, observations, original)
        publications = self._planning_evidence_publications(checkpoint, extraction_invocation_ids, auth)
        assertion_count = sum(len(p.assertion_bytes) for p in publications)
        if assertion_count == 0:
            raise ProcessingPublicationError("input_unavailable")
        if assertion_count > self._processing_bindings.max_output_items:
            raise ProcessingPublicationError("output_invalid")
        identifiers = tuple(dict.fromkeys(r.artifact_id for p in publications for r in p.input_records()))
        records, envelopes = self._planning_evidence_inputs(identifiers, binding, scope, auth)
        payload = canonical({"version": "planning-evidence-input-v2",
            "checkpoint": checkpoint.model_dump(mode="json"),
            "authority_observations": [o.model_dump(mode="json") for o in observations],
            "extraction_publications": [_publication_value(p) for p in publications]})
        self._processing_limit(payload)
        companion = PlanningEvidenceInputV2.from_bytes(payload)
        identity = {"kind": "planning_evidence_v2", "envelope_hash": companion.envelope_hash,
            "checkpoint_hash": digest(companion.checkpoint_bytes),
            "extraction_invocation_ids": list(extraction_invocation_ids),
            "extraction_marker_hashes": [p.marker_hash for p in publications]}
        record = self._processing_record(payload, binding, scope, auth,
            "saved-planning-evidence-v2", "application/json", records, identity)
        # Every check here follows the actual final envelope/control/record I/O.
        if self.read_original(record.artifact_id, auth, purpose="provider_processing") != payload:
            raise ProcessingPublicationError("partial_publication")
        if self._planning_evidence_publications(checkpoint, extraction_invocation_ids, auth) != publications:
            raise ProcessingPublicationError("identity_mismatch")
        actual, actual_envelopes = self._planning_evidence_inputs(identifiers, binding, scope, auth)
        if actual != records or actual_envelopes != envelopes:
            raise ProcessingPublicationError("identity_mismatch")
        self._processing_current_scope(binding, scope, auth)
        current = self._processing_bindings.checkpoint_lookup(binding)
        if type(current) is not PhaseCheckpoint or current != checkpoint:
            raise ProcessingPublicationError("identity_mismatch")
        self._processing_current_scope(binding, scope, auth)
        if self.clock.now() >= checkpoint.deadline:
            raise ProcessingPublicationError("scope_denied")
        return record

    def _planning_evidence_checkpoint(self, checkpoint, observations, original):
        from proofkey.contracts import EnvironmentProfile
        from proofkey.profiles import validate_profile
        from proofkey.process import validate_process
        try:
            lookup = self._processing_bindings.profile_lookup
            if lookup is None:
                raise ValueError("Registered local profile unavailable")
            profile = lookup(checkpoint.binding, original)
            if type(profile) is not EnvironmentProfile:
                raise ValueError("Exact registered profile required")
            profile = validate_profile(profile)
            spec = profile.processes[original.kind]
            validate_process(spec)
            if profile.version != checkpoint.profile_version or spec.version != checkpoint.process_version:
                raise ValueError("Registered version mismatch")
        except Exception as exc:
            raise ProcessingPublicationError("input_unavailable") from exc
        current = self._processing_bindings.checkpoint_lookup(checkpoint.binding)
        if (type(current) is not PhaseCheckpoint or current != checkpoint or checkpoint.stop.requested
                or checkpoint.phase in {"stop", "stopped", spec.completion.phase}
                or checkpoint.next_gate not in {"reschedule", "register_goods_refusal", "register_service_refusal", "create_return"}
                or len([e for e in spec.edges if e.origin == checkpoint.phase
                        and e.operation == checkpoint.next_gate]) != 1
                or any(o.object_id != checkpoint.binding.object_id for o in observations)):
            raise ProcessingPublicationError("identity_mismatch")
        if self.clock.now() >= checkpoint.deadline:
            raise ProcessingPublicationError("scope_denied")

    def _planning_evidence_publications(self, checkpoint, identifiers, auth):
        publications = []
        for identifier in identifiers:
            attempt, _ = self._processing_attempt(checkpoint.binding, identifier)
            if (attempt.identity.role != "extraction"
                    or attempt.identity.profile_version != checkpoint.profile_version
                    or attempt.identity.process_version != checkpoint.process_version):
                raise ProcessingPublicationError("identity_mismatch")
            publication = self.publish_processing_output(checkpoint.binding, identifier, auth)
            publications.append(publication)
        return tuple(publications)

    def _planning_evidence_inputs(self, identifiers, binding, scope, auth):
        if not 0 < len(identifiers) <= self._processing_bindings.max_inputs:
            raise ProcessingPublicationError("output_invalid")
        records, envelopes = self._processing_inputs(identifiers, binding, auth, scope=scope)
        # Bound the distinct ancestry of the full envelope, not each direct input alone.
        seen = set()
        for record in records:
            if self._get(record.artifact_id, auth, "provider_processing", set(), seen, 0,
                         processing_scope=scope) != record:
                raise ProcessingPublicationError("identity_mismatch")
        return records, envelopes

    @_publication_operation
    def seal_invocation_inputs(self, binding: RequestBinding, invocation_id: str,
            artifact_ids: tuple[str, ...], auth: AuthContext) -> InputPublication:
        _, scope = self._processing_scope(binding, auth, "provider_processing")
        attempt, receipt = self._processing_attempt(binding, invocation_id)
        if receipt is not None or attempt.status != "consumed":
            raise ProcessingPublicationError("not_reserved")
        if (type(artifact_ids) is not tuple or not 0 < len(artifact_ids) <= self._processing_bindings.max_inputs
                or any(type(a) is not str for a in artifact_ids) or len(set(artifact_ids)) != len(artifact_ids)):
            raise ProcessingPublicationError("identity_mismatch")
        records, envelopes = self._processing_inputs(artifact_ids, binding, auth, scope=scope)
        if [r.original_hash for r in records] != attempt.identity.input_hashes:
            raise ProcessingPublicationError("identity_mismatch")
        envelope = {"binding": binding.model_dump(mode="json"),
            "invocation_id": invocation_id, "reservation": attempt.model_dump(mode="json"),
            "reservation_identity_hash": fingerprint(attempt.identity.model_dump(mode="json")),
            "input_records": [r.model_dump(mode="json") for r in records],
            "record_envelopes": envelopes}
        encoded = canonical(envelope)
        self._processing_write(self._processing_path("inputs", binding, invocation_id), encoded)
        self._processing_final_inputs(binding, invocation_id, auth, scope, records, envelopes, (attempt, None))
        return InputPublication(canonical(binding.model_dump(mode="json")), invocation_id,
            envelope["reservation_identity_hash"], tuple(canonical(r.model_dump(mode="json")) for r in records),
            encoded, digest(encoded))

    def _processing_path(self, kind, binding, invocation_id):
        key = digest(canonical({"domain": "proofkey-processing-" + kind + "-v1",
            "binding": binding.model_dump(mode="json"), "invocation_id": invocation_id}))
        return self.root / "receipts" / (kind + "-" + key + ".json")

    def _processing_attempt(self, binding, invocation_id):
        try:
            pair = self._processing_bindings.invocation_lookup(invocation_id)
            if type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not InvocationReservation:
                raise ValueError("Exact durable invocation required")
            attempt = InvocationReservation.model_validate(pair[0].model_dump(mode="json"))
            receipt = pair[1]
            if receipt is not None:
                if type(receipt) is not ProcessingReceipt:
                    raise ValueError("Exact durable receipt required")
                receipt = ProcessingReceipt.model_validate(receipt.model_dump(mode="json"))
            if (attempt.invocation_id != invocation_id
                    or (attempt.identity.case_id, attempt.identity.generation) != (binding.case_id, binding.generation)
                    or (attempt.case_debit, attempt.role_debit, attempt.campaign_debit) != (1, 1, 1)):
                raise ValueError("Invocation differs from original/debits")
            return attempt, receipt
        except Exception as exc:
            raise ProcessingPublicationError("identity_mismatch") from exc

    def _processing_inputs(self, artifact_ids, binding, auth, *, scope):
        records, envelopes, size = [], [], 0
        try:
            for identifier in artifact_ids:
                record = self._get(identifier, auth, "provider_processing", set(), set(), 0,
                                   processing_scope=scope)
                payload = self.read_original(identifier, auth, purpose="provider_processing")
                _, envelope = self._load(identifier)
                if (record.case_id != binding.case_id
                        or (record.parent_hashes and "processing" not in envelope)):
                    raise ValueError("Unresolved original ancestry")
                self._processing_limit(payload)
                size += len(payload)
                if size > min(self.max_bytes, self._processing_bindings.max_publication_bytes):
                    raise ValueError("Aggregate original bytes ceiling")
                records.append(record)
                envelopes.append(envelope)
        except EvidenceAccessDenied as exc:
            raise ProcessingPublicationError("scope_denied") from exc
        except Exception as exc:
            raise ProcessingPublicationError("input_unavailable") from exc
        return tuple(records), envelopes

    def _processing_current_scope(self, binding, expected, auth):
        _, current = self._processing_scope(binding, auth, "provider_processing")
        if current != expected:
            raise ProcessingPublicationError("identity_mismatch")
        return current

    def _processing_final_inputs(self, binding, invocation_id, auth, scope, records, envelopes, pair):
        current = self._processing_current_scope(binding, scope, auth)
        actual, actual_envelopes = self._processing_inputs(tuple(r.artifact_id for r in records), binding, auth,
                                                         scope=current)
        if (actual != records or actual_envelopes != envelopes
                or self._processing_attempt(binding, invocation_id) != pair):
            raise ProcessingPublicationError("identity_mismatch")
        # Input reads/lookup can themselves take time; never reuse the pre-I/O window.
        self._processing_current_scope(binding, scope, auth)

    @_publication_operation
    def publish_processing_output(self, binding: RequestBinding, invocation_id: str,
            auth: AuthContext) -> ProcessingPublication:
        _, scope = self._processing_scope(binding, auth, "provider_processing")
        attempt, receipt = self._processing_attempt(binding, invocation_id)
        if receipt is None or attempt.status != "completed" or receipt.status != "completed" or receipt.mode != "synthetic":
            raise ProcessingPublicationError("not_complete")
        identity = attempt.identity
        if ((receipt.invocation_id, receipt.role, receipt.provider, receipt.requested_model,
                receipt.prompt_hash, receipt.version, receipt.input_hashes) !=
                (attempt.invocation_id, identity.role, identity.provider, identity.model,
                 identity.prompt_hash, identity.version, identity.input_hashes)
                or any(unit not in attempt.reserved_usage or amount > attempt.reserved_usage[unit]
                       for unit, amount in receipt.usage.items())):
            raise ProcessingPublicationError("identity_mismatch")
        output = receipt.output
        if (output is None or output.kind != {"extraction": "assertions", "transcription": "transcript",
                "planning": "proposal"}[identity.role]
                or receipt.output_hashes != [digest(output.model_dump_json().encode("utf-8"))]):
            raise ProcessingPublicationError("output_invalid")
        seal_path = self._processing_path("inputs", binding, invocation_id)
        try:
            seal_bytes = _bounded_read(seal_path, self.max_bytes, private=True)
            seal = json_bytes(seal_bytes)
            if type(seal) is not dict or set(seal) != {"binding", "invocation_id", "reservation",
                    "reservation_identity_hash", "input_records", "record_envelopes"}:
                raise ValueError("Closed sealed envelope required")
            original_attempt = InvocationReservation.model_validate(seal["reservation"])
            if (seal["binding"] != binding.model_dump(mode="json") or seal["invocation_id"] != invocation_id
                    or original_attempt.status != "consumed"
                    or original_attempt.model_copy(update={"status": attempt.status}) != attempt
                    or seal["reservation_identity_hash"] != fingerprint(identity.model_dump(mode="json"))):
                raise ValueError("Sealed reservation mismatch")
            sealed_records = tuple(ArtifactRecord.model_validate(r) for r in seal["input_records"])
            if (not 0 < len(sealed_records) <= self._processing_bindings.max_inputs
                    or len({r.artifact_id for r in sealed_records}) != len(sealed_records)):
                raise ValueError("Invalid sealed record sequence")
            records, envelopes = self._processing_inputs(tuple(r.artifact_id for r in sealed_records), binding, auth,
                                                        scope=scope)
            if (records != sealed_records or envelopes != seal["record_envelopes"]
                    or [r.original_hash for r in records] != identity.input_hashes):
                raise ValueError("Sealed ACL/bytes/lineage changed")
        except ProcessingPublicationError:
            raise
        except Exception as exc:
            raise ProcessingPublicationError("identity_mismatch") from exc
        self._processing_limit(canonical(output.model_dump(mode="json")))
        assertions, transcript = self._validate_processing_output(receipt, records, auth)
        planning_evidence = None
        if identity.role == "planning" and records[0].source == "saved-planning-evidence-v2":
            planning_evidence = self._saved_planning_evidence(binding, identity, records[0], scope, auth)
        receipt_hash = fingerprint(receipt.model_dump(mode="json"))
        fixed = {"binding": binding.model_dump(mode="json"), "invocation_id": invocation_id,
            "receipt": receipt.model_dump(mode="json"), "receipt_hash": receipt_hash,
            "input_envelope_hash": digest(seal_bytes), "scope": scope.scope()}
        control_path = self._processing_path("output-control", binding, invocation_id)
        if control_path.exists():
            try:
                control = json_bytes(_bounded_read(control_path, self.max_bytes, private=True))
                if (set(control) != {"fixed", "created_at"} or control["fixed"] != fixed
                        or datetime.fromisoformat(control["created_at"]).utcoffset() is None):
                    raise ValueError("Conflicting publication control")
            except Exception as exc:
                raise ProcessingPublicationError("publication_conflict") from exc
        else:
            control = {"fixed": fixed, "created_at": self.clock.now().isoformat()}
            self._processing_write(control_path, canonical(control))
        assertion_bytes = tuple(canonical(a.model_dump(mode="json")) for a in assertions)
        assertion_refs, written = [], []
        for index, payload in enumerate(assertion_bytes):
            ref = "private-assertion-" + digest(canonical({"domain": "proofkey-saved-assertion-v1",
                "receipt_hash": receipt_hash, "index": index, "bytes_hash": digest(payload)}))
            path = self.root / "receipts" / (ref + ".json")
            self._processing_write(path, payload)
            assertion_refs.append(ref)
            written.append((path, payload))
        transcript_record = None
        proposal_ref = None
        if transcript is not None:
            transcript_record = self._processing_record(transcript.text.encode("utf-8"), binding, scope, auth,
                "saved-synthetic-transcription", "text/x-supplied-transcript", records,
                {"kind": "transcription", "invocation_id": invocation_id, "receipt_hash": receipt_hash,
                 "output_digest": receipt.output_hashes[0], "mode": "synthetic",
                 "segments": [s.model_dump(mode="json") for s in transcript.segments],
                 "timing": "unknown" if not transcript.segments else "saved_locators"})
        elif identity.role == "planning":
            proposal_ref = "private-proposal-" + digest(canonical({"domain": "proofkey-saved-proposal-v1",
                "receipt_hash": receipt_hash, "input_envelope_hash": digest(seal_bytes)}))
            payload = canonical({"receipt": receipt.model_dump(mode="json"), "input_envelope_hash": digest(seal_bytes)})
            path = self.root / "receipts" / (proposal_ref + ".json")
            self._processing_write(path, payload)
            written.append((path, payload))
        # Read back every actual output and reauthorize every original/parent immediately before marker.
        for path, payload in written:
            if _bounded_read(path, self.max_bytes, private=True) != payload:
                raise ProcessingPublicationError("partial_publication")
        again_records, again_envelopes = self._processing_inputs(tuple(r.artifact_id for r in records), binding, auth,
                                                               scope=scope)
        _, current_scope = self._processing_scope(binding, auth, "provider_processing")
        if (again_records != records or again_envelopes != envelopes or current_scope != scope
                or self._processing_attempt(binding, invocation_id) != (attempt, receipt)):
            raise ProcessingPublicationError("identity_mismatch")
        if transcript_record is not None:
            if self.read_original(transcript_record.artifact_id, auth, purpose="provider_processing") != transcript.text.encode("utf-8"):
                raise ProcessingPublicationError("partial_publication")
        marker = {"binding": binding.model_dump(mode="json"), "invocation_id": invocation_id,
            "receipt_hash": receipt_hash, "output_hashes": receipt.output_hashes,
            "input_records": [r.model_dump(mode="json") for r in records],
            "assertions": [a.model_dump(mode="json") for a in assertions], "assertion_refs": assertion_refs,
            "transcript_record": None if transcript_record is None else transcript_record.model_dump(mode="json"),
            "proposal_receipt_ref": proposal_ref, "control_hash": digest(canonical(control)),
            "status": "completed", "mode": "synthetic"}
        marker_bytes = canonical(marker)
        self._processing_write(self._processing_path("output-marker", binding, invocation_id), marker_bytes)
        if transcript_record is not None:
            if self.read_original(transcript_record.artifact_id, auth, purpose="provider_processing") != transcript.text.encode("utf-8"):
                raise ProcessingPublicationError("partial_publication")
        if planning_evidence is not None:
            if self._saved_planning_evidence(binding, identity, records[0], scope, auth) != planning_evidence:
                raise ProcessingPublicationError("identity_mismatch")
        self._processing_final_inputs(binding, invocation_id, auth, scope, records, envelopes, (attempt, receipt))
        return ProcessingPublication(canonical(binding.model_dump(mode="json")), invocation_id, receipt_hash,
            tuple(receipt.output_hashes), tuple(canonical(r.model_dump(mode="json")) for r in records),
            assertion_bytes, tuple(assertion_refs),
            None if transcript_record is None else canonical(transcript_record.model_dump(mode="json")),
            proposal_ref, marker_bytes, digest(marker_bytes))

    def _validate_processing_output(self, receipt, records, auth):
        # Closed catalog-owner format seam: no intake/provider receipt or debit is created.
        from proofkey.evidence.intake import DecoderUnavailable, IntakeLimits, _decode
        limits = self._processing_bindings
        decoded = {}
        try:
            for record in records:
                actual = self.resolve_record(record, auth, purpose="inspect")
                decode_limits = IntakeLimits(max_bytes=min(self.max_bytes, limits.max_publication_bytes))
                payload = self.read_original(actual.artifact_id, auth, purpose="inspect",
                                             max_bytes=decode_limits.max_bytes)
                _, coordinates, _ = _decode(payload, actual.mime_type, decode_limits)
                decoded[record.artifact_id] = coordinates
            if receipt.role == "extraction":
                assertions = tuple(receipt.output.assertions)
                if len(assertions) > limits.max_output_items:
                    raise ValueError("Assertion ceiling")
                parents = {r.artifact_id: r for r in records}
                for assertion in assertions:
                    record = parents.get(assertion.artifact_id)
                    if (record is None or assertion.processing_receipt_id != receipt.invocation_id
                            or assertion.content_hash != record.original_hash or assertion.lineage_hash != record.lineage_hash
                            or len(assertion.claim.encode("utf-8")) > limits.max_claim_bytes):
                        raise ValueError("Assertion saved-input lineage mismatch")
                    if assertion.locator.kind != "unknown":
                        _validate_locator(assertion.locator, decoded[record.artifact_id])
                return assertions, None
            if receipt.role == "transcription":
                transcript = receipt.output
                if (len(records) != 1 or not records[0].mime_type.startswith("audio/")
                        or len(transcript.segments) > limits.max_output_items):
                    raise ValueError("One finite original audio required")
                self._processing_limit(transcript.text.encode("utf-8"))
                for segment in transcript.segments:
                    if len(segment.text.encode("utf-8")) > limits.max_claim_bytes:
                        raise ValueError("Segment ceiling")
                    if segment.locator.kind != "unknown":
                        if segment.locator.kind != "audio_time":
                            raise ValueError("Original audio coordinates required")
                        _validate_locator(segment.locator, decoded[records[0].artifact_id])
                return (), transcript
            if (len(records) == 1 and records[0].source == "saved-planning-evidence-v2"
                    and records[0].mime_type == "application/json"):
                # The public publisher joins this separate format to its saved durable lineage.
                return (), None
            if len(records) != 1 or records[0].source != "saved-planning-snapshot-v1":
                raise ValueError("Exact pre-debit planning input required")
            _, envelope = self._load(records[0].artifact_id)
            if envelope["processing"]["identity"]["kind"] != "planning_snapshot_v1":
                raise ValueError("Exact planning lineage required")
            snapshot = json_bytes(self.read_original(records[0].artifact_id, auth, purpose="provider_processing"))
            checkpoint = PhaseCheckpoint.model_validate(snapshot["checkpoint"])
            identity = self._processing_bindings.invocation_lookup(receipt.invocation_id)[0].identity
            if (checkpoint.binding.case_id, checkpoint.binding.generation, checkpoint.profile_version,
                    checkpoint.process_version) != (identity.case_id, identity.generation,
                                                    identity.profile_version, identity.process_version):
                raise ValueError("Planning snapshot versions differ from saved reservation")
            return (), None
        except ProcessingPublicationError:
            raise
        except DecoderUnavailable:
            raise ProcessingPublicationError("input_unavailable") from None
        except Exception as exc:
            raise ProcessingPublicationError("output_invalid") from exc

    def _saved_planning_evidence(self, binding, identity, record, scope, auth):
        """Reauthorize exact historical V2 input; never require the post-debit checkpoint."""
        payload = self._processing_limit(self.read_original(record.artifact_id, auth,
                                                           purpose="provider_processing"))
        companion = PlanningEvidenceInputV2.from_bytes(payload)
        checkpoint = companion.checkpoint()
        _, envelope = self._load(record.artifact_id)
        metadata = envelope["processing"]
        publications = companion.extraction_publications()
        identifiers = tuple(p.invocation_id for p in publications)
        expected_identity = {"kind": "planning_evidence_v2", "envelope_hash": companion.envelope_hash,
            "checkpoint_hash": digest(companion.checkpoint_bytes),
            "extraction_invocation_ids": list(identifiers),
            "extraction_marker_hashes": [p.marker_hash for p in publications]}
        parents = tuple({r.artifact_id: r for p in publications for r in p.input_records()}.values())
        if (record.source != "saved-planning-evidence-v2" or record.mime_type != "application/json"
                or record.original_hash != companion.envelope_hash
                or identity.input_hashes != [companion.envelope_hash]
                or checkpoint.binding != binding or metadata["binding"] != binding.model_dump(mode="json")
                or (checkpoint.binding.case_id, checkpoint.binding.generation, checkpoint.profile_version,
                    checkpoint.process_version) != (identity.case_id, identity.generation,
                                                    identity.profile_version, identity.process_version)
                or metadata["identity"] != expected_identity
                or metadata["parents"] != [p.model_dump(mode="json") for p in parents]):
            raise ProcessingPublicationError("identity_mismatch")
        if sum(len(p.assertion_bytes) for p in publications) > self._processing_bindings.max_output_items:
            raise ProcessingPublicationError("output_invalid")
        actual, _ = self._planning_evidence_inputs(tuple(p.artifact_id for p in parents), binding, scope, auth)
        if actual != parents or self._planning_evidence_publications(checkpoint, identifiers, auth) != publications:
            raise ProcessingPublicationError("identity_mismatch")
        return companion

    def _processing_scope(self, binding, auth, purpose):
        bindings = self._processing_bindings
        if bindings is None:
            raise ProcessingPublicationError("input_unavailable")
        if type(binding) is not RequestBinding or type(auth) is not AuthContext:
            raise ProcessingPublicationError("scope_denied")
        try:
            binding = RequestBinding.model_validate(binding.model_dump(mode="json"))
            original = bindings.original_lookup(binding)
            if type(original) is not CanonicalRequest:
                raise ValueError("No complete typed saved original")
            original = CanonicalRequest.model_validate(original.model_dump(mode="json"))
            fields = ("case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision")
            if (any(getattr(binding, n) != getattr(original, n) for n in fields)
                    or binding.fingerprint != request_fingerprint(original)):
                raise ValueError("Original business binding mismatch")
            scope = bindings.original_scope(binding, original, auth, purpose)
            if type(scope) is not SavedOriginalScope:
                raise ValueError("No current registered scope")
            scope = SavedOriginalScope(**{n: getattr(scope, n) for n in scope.__dataclass_fields__})
            if (scope.binding() != binding or scope.original_request_hash != fingerprint(original.model_dump(mode="json"))
                    or self.clock.now() >= scope.expires_at):
                raise ValueError("Saved original scope mismatch or expiry")
            return original, scope
        except Exception as exc:
            raise ProcessingPublicationError("scope_denied") from exc

    def _processing_limit(self, payload):
        if (type(payload) is not bytes or len(payload) > min(self.max_bytes,
                self._processing_bindings.max_publication_bytes)):
            raise ProcessingPublicationError("output_invalid")
        return payload

    def _processing_write(self, path, payload):
        self._processing_limit(payload)
        try:
            self._store(path, payload)
            if _bounded_read(path, self.max_bytes, private=True) != payload:
                raise EvidencePathError("Readback mismatch")
        except EvidencePathError as exc:
            # Never repair, overwrite or treat a partial/conflicting object as completed.
            raise ProcessingPublicationError("publication_conflict") from exc
        except OSError as exc:
            raise ProcessingPublicationError("partial_publication") from exc

    def _processing_record(self, payload, binding, scope, auth, source, mime, parents, identity):
        self._processing_limit(payload)
        metadata = {"binding": binding.model_dump(mode="json"),
            "original_request_hash": scope.original_request_hash,
            "parents": [p.model_dump(mode="json") for p in parents], "identity": identity}
        fixed = {"payload_hash": digest(payload), "processing": metadata,
                 "scope": scope.scope(), "source": source, "mime": mime}
        key = digest(canonical({"domain": "proofkey-processing-record-v1", "identity": fixed}))
        identifier = "artifact-" + key[:32]
        control_path = self.root / "receipts" / ("record-" + key + ".json")
        if control_path.exists():
            try:
                control = json_bytes(_bounded_read(control_path, self.max_bytes, private=True))
                if set(control) != {"fixed", "created_at"} or control["fixed"] != fixed:
                    raise ValueError("Conflicting record control")
                created_at = datetime.fromisoformat(control["created_at"])
                if created_at.utcoffset() is None:
                    raise ValueError("Aware initial timestamp required")
            except (ValueError, KeyError, TypeError) as exc:
                raise ProcessingPublicationError("publication_conflict") from exc
        else:
            created_at = self.clock.now()
        parent_hashes = [p.original_hash for p in parents]
        lineage = fingerprint({"bytes": digest(payload), "parents": parent_hashes,
            "scope": scope.scope(), "case": binding.case_id, "source": source, "policy": scope.policy_id})
        record = ArtifactRecord(artifact_id=identifier, original_hash=digest(payload), mime_type=mime,
            source=source, case_id=binding.case_id, access="restricted", created_at=created_at,
            lineage_hash=lineage, parent_hashes=parent_hashes, source_reference="private-catalog:" + identifier)
        self._authorize(record, {"scope": scope.scope(), "policy": scope.policy_id}, auth, "provider_processing")
        for parent in parents:
            if self.get(parent.artifact_id, auth, purpose="provider_processing") != parent:
                raise ProcessingPublicationError("identity_mismatch")
        self._processing_write(control_path, canonical({"fixed": fixed, "created_at": created_at.isoformat()}))
        envelope = {"record": record.model_dump(mode="json"), "scope": scope.scope(),
                    "policy": scope.policy_id, "processing": metadata}
        self._processing_write(self.root / "objects" / record.original_hash, payload)
        self._processing_write(self.root / "records" / (identifier + ".json"), canonical(envelope))
        if self.get(identifier, auth, purpose="provider_processing") != record:
            raise ProcessingPublicationError("publication_conflict")
        self._processing_current_scope(binding, scope, auth)
        return record

    def _authorize(self, record, envelope, auth, purpose):
        try:
            permitted = self.access_resolver(auth, record, _freeze(envelope["scope"]), purpose)
        except Exception as exc:
            raise EvidenceAccessDenied("Evidence unavailable or denied") from exc
        if permitted is not True:
            raise EvidenceAccessDenied("Evidence unavailable or denied")

    def _load(self, artifact_id):
        if not isinstance(artifact_id, str) or not artifact_id.startswith("artifact-") or len(artifact_id) != 41 or any(
                ch not in "0123456789abcdef" for ch in artifact_id[9:]):
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        try:
            envelope = json.loads(_bounded_read(self.root / "records" / (artifact_id + ".json"), self.max_bytes, private=True))
            record = ArtifactRecord.model_validate(envelope["record"])
            if record.artifact_id != artifact_id:
                raise ValueError("Mismatched stored identity")
            return record, envelope
        except (ValueError, KeyError, TypeError) as exc:
            raise EvidenceAccessDenied("Evidence unavailable or denied") from exc

    def get(self, artifact_id, auth=None, *, purpose="read"):
        return self._get(artifact_id, auth, purpose, set(), set(), 0)

    def _get(self, artifact_id, auth, purpose, active, seen, depth, *, processing_scope=None):
        if not isinstance(auth, AuthContext):
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        limits = self._processing_bindings
        if artifact_id in active or (limits is not None and (
                depth > limits.max_ancestry_depth or len(seen | {artifact_id}) > limits.max_ancestry_records)):
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        active.add(artifact_id)
        seen.add(artifact_id)
        record, envelope = self._load(artifact_id)
        expected = fingerprint({"bytes": record.original_hash, "parents": list(record.parent_hashes),
            "scope": envelope["scope"], "case": record.case_id, "source": record.source, "policy": envelope["policy"]})
        if expected != record.lineage_hash:
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        self._authorize(record, envelope, auth, purpose)
        scopes = ()
        if processing_scope is not None:
            scopes = (processing_scope,) if type(processing_scope) is SavedOriginalScope else processing_scope
        for inherited in scopes:
            # Independent intersection on the actual record, never a fabricated grant.
            self._authorize(record, {"scope": inherited.scope(), "policy": inherited.policy_id},
                            auth, purpose)
        if limits is not None and record.source in {"saved-request-narrative", "saved-planning-snapshot-v1", "saved-synthetic-transcription", "saved-planning-evidence-v2"} and "processing" not in envelope:
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        if "processing" in envelope:
            try:
                metadata = envelope["processing"]
                fixed = {"payload_hash": record.original_hash, "processing": metadata,
                    "scope": envelope["scope"], "source": record.source, "mime": record.mime_type}
                key = digest(canonical({"domain": "proofkey-processing-record-v1", "identity": fixed}))
                control = json_bytes(_bounded_read(self.root / "receipts" / ("record-" + key + ".json"),
                    self.max_bytes, private=True))
                if (set(control) != {"fixed", "created_at"} or record.artifact_id != "artifact-" + key[:32] or control["fixed"] != fixed
                        or record.created_at != datetime.fromisoformat(control["created_at"])):
                    raise ValueError("Immutable record control mismatch")
                binding = RequestBinding.model_validate(metadata["binding"])
                _, scope = self._processing_scope(binding, auth, purpose)
                if record.source == "saved-planning-evidence-v2":
                    # Add this V2 policy without losing any outer current-policy intersection.
                    # Each ancestry level can add at most one scope; existing depth/count caps bind it.
                    if scope not in scopes:
                        scopes = (*scopes, scope)
                raw_parents = metadata["parents"]
                if type(raw_parents) is not list or len(raw_parents) > limits.max_inputs:
                    raise ValueError("Finite exact parent inventory required")
                parents = tuple(ArtifactRecord.model_validate(p) for p in raw_parents)
                if (record.case_id != binding.case_id or scope.scope() != envelope["scope"]
                        or scope.policy_id != envelope["policy"]
                        or scope.original_request_hash != metadata["original_request_hash"]
                        or record.parent_hashes != [p.original_hash for p in parents]):
                    raise ValueError("Processing scope/parent mismatch")
                for parent in parents:
                    current = self._get(parent.artifact_id, auth, purpose, active, seen, depth + 1,
                                        processing_scope=scopes)
                    if current != parent or current.case_id != record.case_id:
                        raise ValueError("Parent identity mismatch")
                    payload = _bounded_read(self.root / "objects" / current.original_hash, self.max_bytes, private=True)
                    if digest(payload) != current.original_hash:
                        raise ValueError("Parent bytes mismatch")
            except Exception as exc:
                raise EvidenceAccessDenied("Evidence unavailable or denied") from exc
        active.remove(artifact_id)
        return record

    def resolve_record(self, record, auth=None, *, purpose="inspect"):
        if not isinstance(record, ArtifactRecord):
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        trusted = self.get(record.artifact_id, auth, purpose=purpose)
        if trusted != record:
            raise EvidenceAccessDenied("Evidence unavailable or denied")
        return trusted

    def read_original(self, artifact_id, auth=None, *, purpose="read", max_bytes=None):
        record = self.get(artifact_id, auth, purpose=purpose)
        payload = _bounded_read(self.root / "objects" / record.original_hash,
                               min(self.max_bytes, max_bytes if max_bytes is not None else self.max_bytes), private=True)
        if hashlib.sha256(payload).hexdigest() != record.original_hash:
            raise EvidencePathError("Stored bytes failed integrity check")
        return payload

    def assertion(self, artifact_id, content, locator=None, *, auth=None):
        record = self.get(artifact_id, auth, purpose="assertion")
        from proofkey.evidence.intake import inspect_content, IntakeLimits
        receipt = inspect_content(record, IntakeLimits(max_bytes=self.max_bytes), catalog=self, auth=auth)
        locator = TypeAdapter(Locator).validate_python(locator or UnknownLocator(reason="source_coordinates_not_supplied"))
        if locator.kind != "unknown":
            if receipt.status != "completed":
                raise ValueError("Coordinates require a successfully decoded original")
            _validate_locator(locator, receipt.available_coordinates)
        assertion = EvidenceAssertion(artifact_id=artifact_id, claim=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(), lineage_hash=record.lineage_hash,
            locator=locator, uncertainty="unverified", processing_receipt_id=receipt.invocation_id)
        self._store(self.root / "assertions" / (artifact_id + "-" + uuid.uuid4().hex + ".json"),
                    assertion.model_dump_json().encode())
        return assertion

    def assertions(self, artifact_id, auth=None):
        self.get(artifact_id, auth, purpose="assertion")
        return [EvidenceAssertion.model_validate_json(_bounded_read(path, self.max_bytes, private=True))
                for path in sorted((self.root / "assertions").glob(artifact_id + "-*.json"))]


def _validate_locator(locator, coordinates):
    matching = [item for item in coordinates if item.kind == locator.kind]
    if locator.kind == "text_span" and matching and locator.end <= matching[0].end:
        return
    if locator.kind == "audio_time" and matching and locator.end_seconds <= matching[0].end_seconds:
        return
    if locator.kind == "page_region":
        pages = [item for item in matching if item.page == locator.page]
        if pages:
            if locator.region is None:
                return
            region, bounds = locator.region, pages[0].region
            if bounds is not None:
                width, height = (1, 1) if region.units == "normalized" else (bounds.width, bounds.height)
                if region.x + region.width <= width and region.y + region.height <= height:
                    return
    raise ValueError("Coordinates exceed or are unavailable in the decoded source")
