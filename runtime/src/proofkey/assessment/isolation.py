"""Safe actual local fixture probes; no account changes or protection attestation.

Only synthetic data created by this module is read. The same-UID filesystem
probe deliberately demonstrates that local separation alone is not enforcement.
Endpoint/credential/mount/handle denial and human custody remain unavailable.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from proofkey.contracts import IsolationProbe, IsolationReceipt
from .contracts import canonical_bytes, digest_bytes, require_hash


@dataclass(frozen=True)
class RehearsalBoundary:
    candidate_hash: str
    workload_hash: str
    public_policy: bytes

    def __post_init__(self):
        require_hash(self.candidate_hash)
        require_hash(self.workload_hash)
        digest_bytes(self.public_policy)

    @property
    def registration_hash(self):
        return digest_bytes(canonical_bytes({"candidate_hash": self.candidate_hash, "workload_hash": self.workload_hash,
                            "policy_hash": digest_bytes(self.public_policy), "mode": "local-synthetic-rehearsal"}))


@dataclass(frozen=True)
class ProbeResults:
    registration_hash: str
    runtime_uid: int
    evaluator_uid: int
    public_policy: bytes | None
    hidden_accessible: bool
    leaked_channels: tuple[str, ...]
    output_bytes: bytes
    observed_at: datetime
    limitations: tuple[str, ...]


def run_local_probes(configuration, *, presenter=None):
    if not isinstance(configuration, RehearsalBoundary):
        raise TypeError("Typed synthetic boundary required")
    if presenter is not None and not callable(presenter):
        raise TypeError("Host presentation callback required")
    canary = b"PROOFKEY_SYNTHETIC_CANARY:local-fixture-only"
    policy, hidden = None, False
    with tempfile.TemporaryDirectory(prefix="proofkey-synthetic-isolation-") as folder:
        root = Path(folder)
        (root / "public-policy").write_bytes(configuration.public_policy)
        (root / "synthetic-hidden-canary").write_bytes(canary)
        try:
            policy = (root / "public-policy").read_bytes()
            hidden = (root / "synthetic-hidden-canary").read_bytes() == canary
        except OSError:
            pass
        outputs = {} if presenter is None else presenter(policy, canary)
        if not isinstance(outputs, dict) or not set(outputs) <= {"public", "error", "debug"} or any(type(v) is not bytes for v in outputs.values()):
            raise ValueError("Bounded presentation channel bytes required")
        output_bytes = canonical_bytes({key: value.hex() for key, value in outputs.items()})
        leaked = tuple(sorted(key for key, value in outputs.items() if canary in value))
    return ProbeResults(configuration.registration_hash, os.geteuid(), os.geteuid(), policy, hidden,
        leaked, output_bytes, datetime.now(timezone.utc), ("distinct_identity_unavailable", "mount_denial_unavailable",
        "endpoint_denial_unavailable", "credential_denial_unavailable", "inherited_handle_denial_unavailable", "independent_custody_unavailable"))


def verify_isolation(configuration, probe_results, custodian):
    if not isinstance(configuration, RehearsalBoundary) or not isinstance(probe_results, ProbeResults):
        raise TypeError("Host local boundary and observed probe result required")
    if configuration.registration_hash != probe_results.registration_hash:
        raise ValueError("Isolation identity join mismatch")
    identity_hash = digest_bytes(canonical_bytes({"runtime_uid": probe_results.runtime_uid, "evaluator_uid": probe_results.evaluator_uid,
        "registration_hash": configuration.registration_hash}))
    custody_hash = digest_bytes(canonical_bytes({"custody": "unavailable", "caller_claim_supplied": custodian is not None}))
    result_hash = digest_bytes(canonical_bytes({"registration_hash": probe_results.registration_hash, "identity_hash": identity_hash,
        "public_policy_hash": None if probe_results.public_policy is None else digest_bytes(probe_results.public_policy),
        "hidden_accessible": probe_results.hidden_accessible, "leaked_channels": list(probe_results.leaked_channels),
        "presentation_hash": digest_bytes(probe_results.output_bytes), "limits": list(probe_results.limitations)}))
    failed = bool(probe_results.leaked_channels) or probe_results.public_policy != configuration.public_policy
    probes = [IsolationProbe(name=name, enforced=False, evidence_ref="local-observation:" + result_hash) for name in
        ("identity", "mounts", "endpoints", "credentials", "inherited_handles", "hidden_canary", "public_policy", "output_channels", "custody")]
    return IsolationReceipt(candidate_hash=configuration.candidate_hash, workload_hash=configuration.workload_hash,
        result_hash=result_hash, identity_hash=identity_hash, custody_hash=custody_hash, probes=probes,
        status="failed" if failed else "rehearsal", observed_at=probe_results.observed_at)
