"""Durable pre-entry debit and exact receipt joining. No live enablement or free retry."""
import hashlib
from collections.abc import Mapping
import math
from threading import Lock, get_ident
import time
from uuid import uuid4

from proofkey.contracts import CampaignPermit, InvocationRequest, ProcessingReceipt, ProcessorIdentity
from proofkey.identity import fingerprint
from proofkey.journal import JournalFailure


def output_digest(output):
    return hashlib.sha256(output.model_dump_json().encode()).hexdigest()


class InvocationService:
    def __init__(self, case_id, store, clock, campaign, processor_identity, *, worst_case_cost=None,
                 invocation_id_factory=None):
        self.case_id, self.store, self.clock = case_id, store, clock
        self.campaign = CampaignPermit.model_validate(campaign)
        self.processor_identity = ProcessorIdentity.model_validate(processor_identity)
        self.worst_case_cost = worst_case_cost
        self._id = invocation_id_factory or (lambda: "invocation-" + uuid4().hex)
        self._request = None
        self._lock = Lock()
        self._owner = None
        self._started = None

    @property
    def current_request(self):
        """Host closure only, after reservation; no reusable invocation grant."""
        if self._request is None or self._owner != get_ident():
            raise JournalFailure("No owned active invocation")
        return self._request

    def processing_context(self, catalog, auth, *, input_records=()):
        from proofkey.providers.protocols import ProcessingContext
        request = self.current_request
        lease = self.store.entry("invocation:" + request.invocation_id)
        elapsed = time.monotonic() - self._started
        if not math.isfinite(elapsed) or elapsed < 0:
            raise JournalFailure("Invalid or reversed host elapsed measurement")
        remaining = min(lease.reserved_seconds - elapsed,
                        (lease.deadline - self.clock.now()).total_seconds())
        if remaining <= 0:
            raise JournalFailure("Immutable provider lease has expired")
        return ProcessingContext(request.identity, request.invocation_id, catalog, auth, remaining,
                                 reserved_usage=request.requested_usage, input_records=input_records)

    def make_invocation_request(self, role, input_hashes, usage_ceiling):
        identity, permit = self.processor_identity, self.campaign
        if permit.mode != "simulated":
            raise PermissionError("Actual provider enablement is unavailable")
        wire = permit.model_dump(mode="json")
        if permit.permit_hash != fingerprint({k: v for k, v in wire.items() if k != "permit_hash"}):
            raise JournalFailure("Permit self-hash mismatch")
        if ((self.case_id, role, list(input_hashes)) != (identity.case_id, identity.role, identity.input_hashes)
                or (identity.campaign_id, identity.permit_hash, identity.role, identity.provider, identity.model, identity.endpoint)
                != (permit.campaign_id, permit.permit_hash, permit.role, permit.provider, permit.model, permit.endpoint)):
            raise JournalFailure("Invocation differs from trusted scope")
        if not isinstance(usage_ceiling, Mapping):
            if type(usage_ceiling) not in (int, float) or len(permit.max_usage) != 1:
                raise ValueError("Named usage ceilings required")
            usage_ceiling = {next(iter(permit.max_usage)): usage_ceiling}
        if not usage_ceiling or any(type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0
                                    for amount in usage_ceiling.values()):
            raise ValueError("Finite nonnegative usage ceiling required")
        if (type(self.worst_case_cost) not in (int, float) or not math.isfinite(self.worst_case_cost)
                or self.worst_case_cost < 0):
            raise ValueError("Explicit finite worst-case cost required")
        return InvocationRequest(identity=identity, invocation_id=self._id(),
            requested_usage=dict(usage_ceiling), worst_case_cost=self.worst_case_cost)

    def validate_receipt_identity_and_inputs(self, attempt, receipt):
        if not isinstance(receipt, ProcessingReceipt):
            raise TypeError("Typed processing receipt required")
        receipt = ProcessingReceipt.model_validate(receipt)
        identity = attempt.identity
        if ((receipt.invocation_id, receipt.role, receipt.provider, receipt.requested_model, receipt.prompt_hash,
             receipt.version, receipt.input_hashes) != (attempt.invocation_id, identity.role, identity.provider,
             identity.model, identity.prompt_hash, identity.version, identity.input_hashes)
                or any(unit not in attempt.reserved_usage or amount > attempt.reserved_usage[unit]
                       for unit, amount in receipt.usage.items())):
            raise JournalFailure("Receipt differs from immutable input/identity/usage reservation")
        if receipt.mode != "synthetic" or receipt.status not in {"completed", "failed", "outcome_unknown"}:
            raise JournalFailure("Injected entry cannot fabricate actual/replay/unavailable invocation")
        if receipt.status == "completed":
            if receipt.output is None or receipt.output.kind != {
                    "extraction": "assertions", "transcription": "transcript", "planning": "proposal"}[receipt.role]:
                raise JournalFailure("Complete output does not match declared role")
            if receipt.output_hashes != [output_digest(receipt.output)]:
                raise JournalFailure("Output bytes/hash mismatch")
        elif receipt.output is not None:
            raise JournalFailure("Noncomplete receipt has usable output")
        return receipt

    def preserve_consumed_unknown(self, attempt):
        identity = attempt.identity
        receipt = ProcessingReceipt(invocation_id=attempt.invocation_id, role=identity.role, provider=identity.provider,
            requested_model=identity.model, prompt_hash=identity.prompt_hash, version=identity.version,
            input_hashes=identity.input_hashes, mode="synthetic", status="outcome_unknown", latency_seconds=0.0,
            usage={}, processed_at=self.clock.now(), reason="Invocation interrupted or result invalid; reserved debit retained")
        self.store.record_processing(attempt.invocation_id, receipt)

    def call(self, role, input_hashes, usage_ceiling, invoke):
        if not self._lock.acquire(blocking=False):
            raise JournalFailure("Service already owns an active invocation")
        attempt = None
        try:
            request = self.make_invocation_request(role, input_hashes, usage_ceiling)
            attempt = self.store.reserve_invocation(request, self.clock.now())
            self._request = request
            self._owner = get_ident()
            lease = self.store.entry("invocation:" + attempt.invocation_id)
            started = time.monotonic()
            self._started = started
            receipt = self.validate_receipt_identity_and_inputs(attempt, invoke())
            monotonic_elapsed = time.monotonic() - started
            clock_elapsed = (self.clock.now() - attempt.reserved_at).total_seconds()
            if any(not math.isfinite(value) or value < 0 for value in (monotonic_elapsed, clock_elapsed)):
                raise JournalFailure("Invalid or reversed host elapsed measurement")
            elapsed = max(monotonic_elapsed, clock_elapsed)
            if elapsed > lease.reserved_seconds or self.clock.now() >= lease.deadline:
                self.store.finish_entry(lease.entry_id, max(elapsed, lease.reserved_seconds + 0.001))
                raise JournalFailure("Provider entry exceeded immutable lease")
            self.store.record_processing(attempt.invocation_id, receipt)
            if receipt.status == "completed":
                self.store.finish_entry(lease.entry_id, elapsed)
            saved_attempt, saved = self.store.invocation(attempt.invocation_id)
            if saved != receipt or saved_attempt.identity != self.processor_identity:
                raise JournalFailure("Receipt not durably joined to exact request")
            return saved
        except BaseException:
            if attempt is not None:
                existing = self.store.invocation(attempt.invocation_id)[1]
                if existing is None:
                    self.preserve_consumed_unknown(attempt)
            raise
        finally:
            self._request = None
            self._owner = None
            self._started = None
            self._lock.release()
