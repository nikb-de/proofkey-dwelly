"""Host-owned context and a single bounded injected transport; never attachment-selected routes."""
from dataclasses import dataclass
import math
from typing import Protocol
from collections.abc import Mapping
from types import MappingProxyType
import json

from proofkey.contracts import ArtifactRecord, AuthContext, ProcessingReceipt, ProcessorIdentity
from proofkey.evidence.catalog import EvidenceCatalog


@dataclass(frozen=True)
class ProcessingContext:
    identity: ProcessorIdentity
    invocation_id: str
    catalog: EvidenceCatalog | None
    auth: AuthContext | None
    timeout_seconds: float
    reserved_usage: Mapping[str, float] | None = None
    input_records: tuple[ArtifactRecord, ...] = ()

    def __post_init__(self):
        if not isinstance(self.identity, ProcessorIdentity) or not self.invocation_id:
            raise ValueError("Exact trusted identity and invocation required")
        if (type(self.timeout_seconds) not in (float, int) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 10):
            raise ValueError("Timeout must be positive and at most ten seconds")
        usage = dict(self.reserved_usage or {})
        if any(not isinstance(key, str) or not key or type(val) not in (int, float)
               or not math.isfinite(val) or val < 0 for key, val in usage.items()):
            raise ValueError("Finite named reserved usage required")
        object.__setattr__(self, "reserved_usage", MappingProxyType(usage))
        records = tuple(self.input_records)
        if len(records) > 16 or any(not isinstance(record, ArtifactRecord) for record in records):
            raise ValueError("Finite typed registered inputs required")
        object.__setattr__(self, "input_records", records)


@dataclass(frozen=True)
class TransportRequest:
    endpoint: str
    body: bytes
    content_type: str
    timeout_seconds: float
    max_response_bytes: int
    # No transport may retry, redirect, select models or repair accounts.
    attempts: int = 1
    follow_redirects: bool = False


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    body: bytes
    request_id: str | None = None


class InjectedTransport(Protocol):
    def __call__(self, request: TransportRequest) -> TransportResponse: ...


class Extractor(Protocol):
    def extract(self, records: list[ArtifactRecord], context: ProcessingContext) -> ProcessingReceipt: ...


class Transcriber(Protocol):
    def transcribe(self, record: ArtifactRecord, context: ProcessingContext) -> ProcessingReceipt: ...


class Planner(Protocol):
    def propose(self, checkpoint, observations) -> ProcessingReceipt: ...


def finite_limits(max_request_bytes, max_response_bytes):
    for amount in (max_request_bytes, max_response_bytes):
        if type(amount) is not int or not 0 < amount <= 8 * 1024 * 1024:
            raise ValueError("Positive bounded request/response byte ceilings required")


def strict_json(response, max_bytes, *, allow_negative_infinity=False):
    if (not isinstance(response, TransportResponse) or type(response.status_code) is not int
            or response.status_code != 200 or not isinstance(response.body, bytes) or len(response.body) > max_bytes):
        raise ValueError("Transport rejected, unavailable or outside response byte ceiling")
    def constant(value):
        if allow_negative_infinity and value == "-Infinity":
            return float("-inf")
        raise ValueError("Nonfinite JSON")
    def pairs(values):
        obj = {}
        for key, value in values:
            if key in obj:
                raise ValueError("Duplicate JSON field")
            obj[key] = value
        return obj
    try:
        result = json.loads(response.body, parse_constant=constant, object_pairs_hook=pairs)
    except (UnicodeError, ValueError) as error:
        raise ValueError("Malformed provider response") from error
    if not isinstance(result, dict):
        raise ValueError("Provider response must be an object")
    pending = [(result, ())]
    while pending:
        value, path = pending.pop()
        if isinstance(value, float) and not math.isfinite(value):
            # JSON exponent overflow bypasses parse_constant. The one vendor
            # exception is scoped to words[index].logprob, never an envelope,
            # another key or nested lookalike field.
            if not (allow_negative_infinity and value == float("-inf") and len(path) == 3
                    and path[0] == "words" and type(path[1]) is int and path[2] == "logprob"):
                raise ValueError("Nonfinite parsed provider number")
        elif isinstance(value, dict):
            pending.extend((item, (*path, key)) for key, item in value.items())
        elif isinstance(value, list):
            pending.extend((item, (*path, index)) for index, item in enumerate(value))
    return result


def exact_context(context, role, provider, endpoint):
    if (not isinstance(context, ProcessingContext) or context.identity.role != role
            or context.identity.provider != provider or context.identity.endpoint != endpoint):
        raise ValueError("Role or route differs from fixed injected client")
    if not isinstance(context.catalog, EvidenceCatalog) or not isinstance(context.auth, AuthContext):
        raise ValueError("Trusted catalog and current source authorization required")


def read_records(records, context, max_bytes):
    from proofkey.evidence.intake import inspect_content, IntakeLimits
    if not records or len(records) > 16:
        raise ValueError("Finite nonempty registered record list required")
    if [record.original_hash for record in records] != context.identity.input_hashes:
        raise ValueError("Record hashes differ from reserved exact input sequence")
    decoded, total = [], 0
    for record in records:
        trusted = context.catalog.resolve_record(record, context.auth, purpose="provider-processing")
        if trusted.case_id != context.identity.case_id:
            raise ValueError("Record is outside exact case")
        payload = context.catalog.read_original(record.artifact_id, context.auth,
            purpose="provider-processing", max_bytes=max_bytes)
        total += len(payload)
        if total > max_bytes:
            raise ValueError("Aggregate request byte ceiling exceeded")
        intake = inspect_content(record, IntakeLimits(max_bytes=max_bytes), catalog=context.catalog, auth=context.auth)
        if intake.status != "completed":
            raise ValueError("Content route is unavailable or malformed")
        decoded.append((trusted, payload, intake))
    return decoded
