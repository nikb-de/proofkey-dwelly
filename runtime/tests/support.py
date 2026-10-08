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


class CommitFault:
    """Host-only transaction failure fixture, deliberately not a runtime tool."""
    def __init__(self):
        self._armed = False

    def arm(self):
        self._armed = True

    def __call__(self):
        if self._armed:
            self._armed = False
            from proofkey.journal import JournalFailure
            raise JournalFailure("Injected host commit fault")


def make_fixture_campaign(**overrides):
    """Injected-transport authorization only; no endpoint, rights or live approval."""
    from proofkey.contracts import CampaignPermit
    from hashlib import sha256
    data = dict(campaign_id="fixture-campaign-" + overrides.get("role", "extraction"), input_hashes=[sha256(b"fixture_hash").hexdigest()],
        role="extraction", provider="injected-provider", model="fixture-model", endpoint="injected://role",
        privacy_approval="synthetic-privacy", rights_approval="synthetic-rights", max_cost=4.0,
        max_usage={"tokens": 40.0}, max_invocations=4, expires_at=DEADLINE,
        approval_receipt="synthetic-campaign-not-live-approval", mode="simulated")
    data.update(overrides)
    data.pop("permit_hash", None)
    permit = CampaignPermit(permit_hash="0" * 64, **data)
    wire = permit.model_dump(mode="json")
    wire["permit_hash"] = fingerprint({key: value for key, value in wire.items() if key != "permit_hash"})
    return CampaignPermit.model_validate(wire)


def make_processor_identity(**overrides):
    """Trusted synthetic descriptor with exact fixture input; not provider output."""
    from proofkey.contracts import ProcessorIdentity
    role = overrides.get("role", "extraction")
    grant = make_fixture_campaign(role=role)
    data = dict(case_id="C1", generation="G1", role=role, campaign_id=grant.campaign_id,
        permit_hash=grant.permit_hash, input_hashes=grant.input_hashes, provider=grant.provider,
        model=grant.model, endpoint=grant.endpoint, prompt_hash=fingerprint({"prompt": "fixture"}),
        version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
    return ProcessorIdentity.model_validate({**data, **overrides})


def make_processing_receipt(**overrides):
    """Complete synthetic role result; hashes are rederived after validated overrides."""
    from proofkey.contracts import ProcessingReceipt
    from hashlib import sha256
    role = overrides.get("role", "extraction")
    identity = make_processor_identity(role=role)
    output = {"kind": "assertions", "assertions": []}
    if role == "transcription":
        output = {"kind": "transcript", "text": "Synthetic speech", "segments": []}
    elif role == "planning":
        output = {"kind": "proposal", "proposal": {"operation": "reschedule", "stage": "commit",
            "arguments": {"slot": "S1"}, "evidence_refs": []}}
    data = dict(invocation_id="fixture-invocation", role=role, provider=identity.provider,
        requested_model=identity.model, observed_model="fixture-observed-model", provider_request_id="fixture-request",
        prompt_hash=identity.prompt_hash, version=identity.version, input_hashes=identity.input_hashes,
        mode="synthetic", status="completed", latency_seconds=0.0, usage={"tokens": 1.0},
        output=output, processed_at=NOW)
    receipt = ProcessingReceipt.model_validate({**data, **overrides})
    if "output_hashes" not in overrides:
        receipt = ProcessingReceipt.model_validate({**receipt.model_dump(), "output_hashes":
            [sha256(receipt.output.model_dump_json().encode()).hexdigest()] if receipt.output else []})
    return receipt
