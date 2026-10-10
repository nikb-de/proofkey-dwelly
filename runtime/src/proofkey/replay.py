"""Completed historical results require separately scoped current disclosure."""
from datetime import timedelta
from contextlib import nullcontext
from threading import get_ident
import math

from .contracts import (AuthContext, AuthorityReadback, CanonicalRequest, CaseResult,
                        EnvironmentProfile, ReadRequest, ReadTarget)
from .identity import request_fingerprint
from .journal import JournalFailure
from .execution_consumer import ExecutionTiming


class ReplayService:
    def __init__(self, profile, bundle, store, clock):
        self.profile = EnvironmentProfile.model_validate(profile.model_dump())
        self.bundle, self.store, self.clock = bundle, store, clock
        self._owner_thread = get_ident()
        self._entry_active = False

    @staticmethod
    def _denied(request):
        return CaseResult(status="denied", correlation_id=request.case_id, reason="denied")

    def _historical_bindings(self, case_id):
        """Traverse admitted supersession history through public journal getters."""
        if not self.store.has_case(case_id):
            return ()
        binding = self.store.checkpoint(case_id).binding
        bindings, seen = [], set()
        while binding is not None:
            if binding.generation in seen:
                raise JournalFailure("Cyclic historical generation")
            seen.add(binding.generation)
            bindings.append(binding)
            generation = binding.supersedes_generation
            if generation is None:
                break
            original = self.store.original_request(case_id, generation)
            if original is None:
                raise JournalFailure("Historical original input unavailable")
            binding = self.store.find_request(case_id, original.request_id, original.request_revision,
                original.consent_revision, request_fingerprint(original))
            if binding is None or binding.generation != generation:
                raise JournalFailure("Historical supersession differs from stored input")
        return tuple(bindings)

    def _pace(self, deadline, timing):
        capability = self.profile.capabilities.get("read_authority")
        if (capability is None or capability.timeout_seconds is None
                or any(contract.status != "supported" or not contract.basis or not contract.evidence_ref
                       for contract in (capability.permission_basis, capability.readback))
                or any(self.profile.authorities.get(key) != "case" for key in ("case.binding", "case.authorization"))
                or not callable(getattr(self.clock, "wait", None))):
            raise ValueError("Disclosure authority contract unavailable")
        limits = [c.shared_limits.rate_per_second for c in self.profile.capabilities.values()
                  if c.shared_limits.account_id == capability.shared_limits.account_id]
        if not limits or any(rate is None or not math.isfinite(rate) or rate <= 0 for rate in limits):
            raise ValueError("Finite account pacing unavailable")
        now, cutoff = timing.window(deadline)
        delay = 1.0 / min(limits) + 0.000001
        if now + timedelta(seconds=delay) >= cutoff:
            raise ValueError("Disclosure deadline exhausted")
        self.clock.wait(delay)
        after, cutoff = timing.window(deadline)
        if after < now or after >= cutoff:
            raise ValueError("Invalid disclosure pacing clock")

    def _current_disclosure_allowed(self, binding, auth, timing):
        if not isinstance(auth, AuthContext):
            return False
        auth = AuthContext.model_validate(auth.model_dump())
        current = self.store.checkpoint(binding.case_id)
        self._pace(current.deadline, timing)
        anchor = timing.monotonic_anchor()
        lease = self.store.begin_disclosure_read(binding, self.clock.now())
        capability = self.profile.capabilities["read_authority"]
        now, cutoff = timing.window(min(current.deadline, lease.deadline,
            lease.started_at + timedelta(seconds=capability.timeout_seconds)))
        if timing.execution is not None and now >= cutoff:
            return False
        cutoff = timing._transport_deadline(cutoff, lease, anchor)
        read = ReadRequest(case_id=binding.case_id, object_id=binding.object_id,
            caller_id=auth.caller_id, proof_reference=auth.proof_reference, purpose="disclosure",
            deadline=cutoff,
            target=ReadTarget(kind="authority_facts", authority="case", facts=["authorization", "binding"]))
        # The provider, not the storage index or a caller flag, verifies proof and scope.
        transport = self.bundle.case.read_case
        if timing.execution is not None:
            cutoff = timing._transport_deadline(read.deadline, lease, anchor)
            read = read.model_copy(update={"deadline": cutoff})
        raw = transport(read)
        reply = AuthorityReadback.model_validate(raw.model_dump())
        now = self.clock.now()
        elapsed = timing.elapsed_since(anchor) if anchor is not None else (now - lease.started_at).total_seconds()
        if not math.isfinite(elapsed) or elapsed < 0:
            return False
        if elapsed > lease.reserved_seconds:
            self.store.finish_entry(lease.entry_id, elapsed)
            return False
        timely = (now < read.deadline and lease.started_at <= reply.as_of <= now
            and all(lease.started_at <= o.observed_at <= reply.as_of
                    and o.provider_at is not None and lease.started_at <= o.provider_at <= o.observed_at
                    for o in reply.observations))
        scoped = reply.operation == "read_case" and reply.object_id == binding.object_id
        if not timely or not scoped:
            return False
        if reply.stage == "scope_rejected":
            if not reply.observations:
                self.store.finish_entry(lease.entry_id, elapsed)
            return False
        if reply.stage != "observed" or not reply.evidence_refs:
            return False
        observations = {}
        for observation in reply.observations:
            if (observation.authority != "case" or observation.object_id != binding.object_id
                    or observation.fact in observations or not observation.evidence_ref):
                return False
            observations[observation.fact] = observation.value
        identity = observations.get("binding")
        authorization = observations.get("authorization")
        if (set(observations) != {"authorization", "binding"}
                or not isinstance(authorization, str) or authorization not in {"verified", "revoked", "denied"}
                or not isinstance(identity, dict)
                or any(identity.get(field) != getattr(binding, field)
                       for field in ("case_id", "object_id", "principal_id"))):
            return False
        # Only complete, fresh scoped authority semantics establish known completion.
        if anchor is not None:
            now, cutoff = timing.window(read.deadline)
            elapsed = timing.elapsed_since(anchor)
            if elapsed > lease.reserved_seconds:
                self.store.finish_entry(lease.entry_id, elapsed)
                return False
            if now >= cutoff:
                return False
        self.store.finish_entry(lease.entry_id, elapsed)
        return authorization == "verified"

    def lookup(self, request, auth, *, execution=None):
        if not isinstance(request, CanonicalRequest):
            raise ValueError("Canonical request required")
        if get_ident() != self._owner_thread or self._entry_active:
            return self._denied(request)
        try:
            timing = ExecutionTiming(self.clock, execution)
            self._entry_active = True
            with self.store.execution_scope(execution, self.clock) if execution is not None else nullcontext():
                return self._lookup_in_scope(request, auth, timing)
        except Exception:
            return self._denied(request)
        finally:
            self._entry_active = False

    def _lookup_in_scope(self, request, auth, timing):
        """None selects later fresh admission/recovery, never permission or new identity.

        A changed consent/revision on the same request and business intent is
        ambiguous, hence denied. A different request ID or business fingerprint
        can be a new intent only after the consumer's independent fresh gate.
        """
        if not isinstance(request, CanonicalRequest):
            raise ValueError("Canonical request required")
        request = CanonicalRequest.model_validate(request.model_dump())
        try:
            fingerprint = request_fingerprint(request)
            binding = self.store.find_request(request.case_id, request.request_id,
                request.request_revision, request.consent_revision, fingerprint)
            if binding is None:
                for known in self._historical_bindings(request.case_id):
                    if known.request_id != request.request_id:
                        continue
                    if ((known.object_id, known.principal_id) != (request.object_id, request.principal_id)
                            or known.fingerprint == fingerprint):
                        return self._denied(request)
                return None
            original = self.store.original_request(binding.case_id, binding.generation)
            if ((binding.object_id, binding.principal_id) != (request.object_id, request.principal_id)
                    or original is None):
                return self._denied(request)
            saved = self.store.saved_result(binding.case_id, binding.generation)
            if saved is None:
                current = self.store.checkpoint(binding.case_id)
                return None if current.binding == binding and original == request else self._denied(request)
            if not self._current_disclosure_allowed(binding, auth, timing):
                return self._denied(request)
            # Revalidate a detached projection; saved history and lineage remain immutable.
            return CaseResult.model_validate({**saved.model_dump(), "historical": True})
        except Exception:
            # Transport/storage uncertainty is a generic denial; active leases stay consumed.
            return self._denied(request)
