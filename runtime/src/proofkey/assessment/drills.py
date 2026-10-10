"""Measured bounded host callback rehearsal; outcome/readiness gates stay explicit."""
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from proofkey.contracts import DrillReceipt, DrillWait
from .contracts import DrillPacket, canonical_bytes, digest_bytes


class HostClock:
    """No supplied timestamps or simulated elapsed time can pass this seam."""
    def __init__(self):
        self._waits = ()
        self._waiting = False

    def sample(self):
        return datetime.now(timezone.utc), time.monotonic()

    def wait(self, case_id, kind, callback):
        if kind not in {"provider", "human", "queue"} or not callable(callback) or self._waiting:
            raise ValueError("Nonoverlapping declared host wait required")
        started, start_mono = self.sample()
        self._waiting = True
        try:
            return callback()
        finally:
            ended, end_mono = self.sample()
            self._waits += ((DrillWait(case_id=case_id, question_id="declared-" + kind,
                        started_at=started, ended_at=ended), end_mono - start_mono),)
            self._waiting = False


@dataclass(frozen=True)
class DrillPosition:
    ordinal: int
    case_id: str
    status: str
    output_bytes: bytes | None
    error: bytes | None


@dataclass(frozen=True)
class DrillResult:
    receipt: DrillReceipt
    kind: str
    positions: tuple[DrillPosition, ...]
    setup_error: bytes | None
    export_error: bytes | None
    export_bytes: bytes | None
    unmet_gates: tuple[str, ...]
    candidate_bytes: bytes
    packet_bytes: bytes


@dataclass(frozen=True, init=False)
class DrillRunner:
    """Host registration captures immutable descriptor bytes, never request flags."""
    def __init__(self, descriptor, *, setup, execute, export):
        if not isinstance(descriptor, dict) or set(descriptor) != {"source", "dependencies", "profile", "process", "policy", "prompts"}:
            raise ValueError("Closed candidate descriptor required")
        if any(not callable(callback) for callback in (setup, execute, export)):
            raise TypeError("Host callbacks required")
        object.__setattr__(self, "_candidate_bytes", canonical_bytes(descriptor))
        object.__setattr__(self, "_setup", setup)
        object.__setattr__(self, "_execute", execute)
        object.__setattr__(self, "_export", export)
        object.__setattr__(self, "_results", ())

    @property
    def candidate_hash(self):
        return digest_bytes(self._candidate_bytes)

    @property
    def results(self):
        return self._results


def _error(exc):
    return (type(exc).__name__ + ":" + str(exc)).encode("utf-8")[:1_048_576]


def run_drill(kind, packet, candidate, clock):
    if type(kind) is not str or kind not in {"pilot", "A", "B", "C", "D", "official"}:
        raise ValueError("Declared drill kind required")
    if not isinstance(packet, DrillPacket) or type(candidate) is not DrillRunner or type(clock) is not HostClock:
        raise TypeError("Frozen packet, host runner and measured clock required")
    started_at, start_mono = clock.sample()
    first_wait = len(clock._waits)
    positions, setup_error, export_error, export_bytes = [], None, None, None
    try:
        candidate._setup()
    except Exception as exc:
        setup_error = _error(exc)
    for ordinal, case_id in enumerate(packet.positions):
        output_bytes, error, status = None, None, "unfinished"
        if setup_error is not None:
            error, status = setup_error, "error"
        else:
            try:
                output = candidate._execute(case_id)
                if output is not None:
                    output_bytes, status = canonical_bytes(output), "completed"
            except Exception as exc:
                error, status = _error(exc), "error"
        positions.append(DrillPosition(ordinal, case_id, status, output_bytes, error))
    try:
        exported = candidate._export(tuple(positions))
        export_bytes = None if exported is None else canonical_bytes(exported)
    except Exception as exc:
        export_error = _error(exc)
    ended_at, end_mono = clock.sample()
    elapsed = end_mono - start_mono
    waits = clock._waits[first_wait:]
    if any(wait.case_id not in packet.positions for wait, seconds in waits):
        raise ValueError("Measured wait workload identity mismatch")
    unmet = ["outcomes_unverified", "actual_human_provider_evidence_missing", "protected_isolation_missing", "runtime_regressions_unverified"]
    if any(raw is None for raw in packet.case_bytes):
        unmet.append("workload_content_unavailable")
    if any(p.status != "completed" for p in positions):
        unmet.append("unfinished_positions")
    if setup_error is not None:
        unmet.append("setup_failed")
    if export_bytes is None or export_error is not None:
        unmet.append("export_unverified")
    workload = {"B": 7, "C": 4, "D": 12}.get(kind)
    if workload is not None and len(packet.positions) != workload:
        unmet.append("declared_timed_workload_unmet")
    if kind != "pilot":
        unmet.append("complete_declared_exercise_evidence_missing")
        if elapsed > (1800 if kind == "official" else 600):
            unmet.append("declared_deadline_exceeded")
    result_hash = digest_bytes(canonical_bytes({"domain": "offline-drill-result-v1", "kind": kind,
        "packet": packet.packet_hash, "candidate": candidate.candidate_hash,
        "positions": [{"ordinal": p.ordinal, "case_id": p.case_id, "status": p.status,
            "output_hash": None if p.output_bytes is None else digest_bytes(p.output_bytes),
            "error_hash": None if p.error is None else digest_bytes(p.error)} for p in positions],
        "setup_error": None if setup_error is None else digest_bytes(setup_error),
        "export_error": None if export_error is None else digest_bytes(export_error),
        "export_hash": None if export_bytes is None else digest_bytes(export_bytes)}))
    receipt = DrillReceipt(workload_hash=packet.packet_hash, candidate_hash=candidate.candidate_hash,
        baseline_hash=digest_bytes(packet.baseline_bytes), result_hash=result_hash,
        started_at=started_at, ended_at=ended_at, active_seconds=max(0.0, elapsed - sum(seconds for wait, seconds in waits)), wall_seconds=elapsed,
        waits=[wait for wait, seconds in waits], partial_case_ids=[p.case_id for p in positions if p.status != "completed"], mode="rehearsal")
    result = DrillResult(receipt, kind, tuple(positions), setup_error, export_error, export_bytes,
                         tuple(unmet), candidate._candidate_bytes, packet.packet_bytes)
    object.__setattr__(candidate, "_results", candidate._results + (result,))
    return receipt
