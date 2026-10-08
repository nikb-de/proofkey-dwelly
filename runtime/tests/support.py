"""Synthetic defaults only; these builders confer no production authority.

C1/O1/U1/REQ1/G1, v1 revisions, a UTC 10:00–12:00 window and the
complete goods inventory item-1:1 are deliberate public development data.
All updates are validated again, never applied via unchecked model_copy.
"""
from datetime import datetime, timedelta, timezone

from proofkey.contracts import (AuthContext, BudgetLedger, CanonicalRequest, EffectIntent, EnvironmentProfile,
                               PhaseCheckpoint, RequestBinding, RevisionVector, SavedResult,
                               VerificationResult)
from proofkey.identity import fingerprint, request_fingerprint, stable_action_id

NOW = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
DEADLINE = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)


def make_request(**overrides) -> CanonicalRequest:
    data = dict(case_id="C1", object_id="O1", principal_id="U1", request_id="REQ1",
                request_revision="v1", consent_revision="v1", kind="reschedule_window",
                consent_mode="window", arguments={"window_start": NOW.isoformat(),
                "window_end": DEADLINE.isoformat(), "inventory": {"item-1": 1}}, evidence_ids=[])
    return CanonicalRequest.model_validate({**data, **overrides})


def make_auth(**overrides) -> AuthContext:
    return AuthContext.model_validate({"caller_id": "U1", "proof_reference": "synthetic-proof", **overrides})


def make_binding(request=None, **overrides) -> RequestBinding:
    request = request or make_request()
    data = {name: getattr(request, name) for name in ("case_id", "object_id", "principal_id", "request_id",
                                                    "request_revision", "consent_revision")}
    return RequestBinding.model_validate({**data, "generation": "G1", "fingerprint": request_fingerprint(request), **overrides})


def make_intent(binding=None, **overrides) -> EffectIntent:
    case_id = overrides.pop("case_id", None)
    binding = binding or make_binding(**({"case_id": case_id} if case_id is not None else {}))
    if case_id is not None:
        binding = RequestBinding.model_validate({**binding.model_dump(), "case_id": case_id})
    operation = overrides.get("operation", "reschedule")
    stage = overrides.get("stage", "commit")
    arguments = overrides.get("arguments", {"slot": "S1"})
    action_id = stable_action_id(binding, operation, stage)
    data = dict(binding=binding, operation=operation, stage=stage, action_id=action_id,
                provider_key=action_id, arguments=arguments, argument_fingerprint=fingerprint(arguments),
                profile_version="v1", process_version="v1", policy_version="v1", consent_revision=binding.consent_revision,
                expected_revisions=RevisionVector(revisions={"delivery.status": "v1"}),
                postcondition={"slot": "S1"}, deadline=DEADLINE)
    return EffectIntent.model_validate({**data, **overrides})


def make_checkpoint(binding=None, **overrides) -> PhaseCheckpoint:
    case_id = overrides.pop("case_id", None)
    binding = binding or make_binding()
    if case_id is not None:
        binding = RequestBinding.model_validate({**binding.model_dump(), "case_id": case_id})
    data = dict(binding=binding, phase="start", next_gate="read_authority", profile_version="v1",
                process_version="v1", policy_version="v1", processing_status="pending",
                budget=BudgetLedger(case_id=binding.case_id, deadline=DEADLINE), deadline=DEADLINE)
    return PhaseCheckpoint.model_validate({**data, **overrides})


def make_result(binding=None, **overrides) -> SavedResult:
    case_id = overrides.pop("case_id", None)
    return_status = overrides.pop("return_status", None)
    binding = binding or make_binding()
    if case_id is not None:
        binding = RequestBinding.model_validate({**binding.model_dump(), "case_id": case_id})
    data = dict(binding=binding, fingerprint=binding.fingerprint, result_version="v1", as_of=NOW,
                effects={}, rationale="Synthetic offline fixture", evidence_refs=["synthetic-evidence"], policy_refs=["synthetic-policy"])
    data.update(overrides)
    if return_status is not None:
        verification = {"status": return_status}
        if return_status == "verified":
            # Complete public synthetic goods inventory, not provider authority.
            arguments = {"inventory": {"item-1": 1}}
            verification.update(object_id=binding.object_id,
                action_id=stable_action_id(binding, "create_return", "initiate"),
                fingerprint=fingerprint(arguments),
                postcondition={"return_status": "created", "inventory": arguments["inventory"]},
                evidence_refs=["synthetic-return-verification"], as_of=data["as_of"])
        data["effects"] = {**data["effects"], "create_return": VerificationResult.model_validate(verification)}
    return SavedResult.model_validate(data)


def load_test_profile(name: str = "flat-v1") -> EnvironmentProfile:
    # Task 2 owns this module; keep every Task 1 import usable before it exists.
    from proofkey.profiles import load_profile
    return load_profile(name)


class FakeClock:
    def __init__(self, start=NOW):
        if not isinstance(start, datetime) or start.utcoffset() is None:
            raise ValueError("FakeClock requires an aware datetime")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
