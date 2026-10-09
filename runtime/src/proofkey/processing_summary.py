"""Detached processing status/debt, never content, permission or spend evidence."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Literal
from pydantic import TypeAdapter
from .contracts import Identifier, RequestBinding
from .evidence.processing_contracts import model_bytes


def _identifier(value):
    if type(value) is not str:
        raise ValueError("Exact identifier required")
    TypeAdapter(Identifier).validate_python(value, strict=True)


def _enum(value, choices):
    if type(value) is not str or value not in choices:
        raise ValueError("Declared status required")


def _float(value):
    if type(value) is not float or not math.isfinite(value) or value < 0:
        raise ValueError("Exact finite nonnegative accounting required")


@dataclass(frozen=True, slots=True)
class ProcessingAttemptSummaryV1:
    invocation_id: str
    role: Literal['extraction', 'transcription', 'planning']
    reservation_status: Literal['consumed', 'completed', 'failed', 'outcome_unknown']
    receipt_status: Literal['completed', 'failed', 'outcome_unknown', 'unavailable'] | None
    mode: Literal['intake_only', 'deterministic', 'recorded_replay', 'replay', 'synthetic', 'actual', 'unavailable'] | None
    reserved_usage: tuple[tuple[str, float], ...]
    worst_case_cost: float
    case_debit: int
    role_debit: int
    campaign_debit: int

    def __post_init__(self):
        _identifier(self.invocation_id)
        _enum(self.role, {'extraction', 'transcription', 'planning'})
        _enum(self.reservation_status, {'consumed', 'completed', 'failed', 'outcome_unknown'})
        if self.receipt_status is None:
            if self.mode is not None or self.reservation_status != 'consumed':
                raise ValueError("No receipt retains only consumed debt")
        else:
            _enum(self.receipt_status, {'completed', 'failed', 'outcome_unknown', 'unavailable'})
            _enum(self.mode, {'intake_only', 'deterministic', 'recorded_replay', 'replay',
                'synthetic', 'actual', 'unavailable'})
            state = 'failed' if self.receipt_status == 'unavailable' else self.receipt_status
            if state != self.reservation_status:
                raise ValueError("Terminal reservation/receipt mismatch")
        if type(self.reserved_usage) is not tuple:
            raise ValueError("Exact immutable usage required")
        names = []
        for pair in self.reserved_usage:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("Exact immutable usage pair required")
            name, amount = pair
            _identifier(name)
            _float(amount)
            names.append(name)
        if names != sorted(set(names)):
            raise ValueError("Distinct sorted usage units required")
        _float(self.worst_case_cost)
        for value in (self.case_debit, self.role_debit, self.campaign_debit):
            if type(value) is not int or value != 1:
                raise ValueError("Original unit debt required")


@dataclass(frozen=True, slots=True)
class ProcessingEntryNoteV1:
    kind: Literal['unavailable', 'recorded_replay']
    reason: Literal['input_unavailable', 'permit_unavailable', 'processing_interrupted',
        'output_rejected', 'publication_unavailable'] | None

    def __post_init__(self):
        _enum(self.kind, {'unavailable', 'recorded_replay'})
        if self.kind == 'recorded_replay':
            if self.reason is not None:
                raise ValueError("Replay note carries no content or reason")
        else:
            _enum(self.reason, {'input_unavailable', 'permit_unavailable', 'processing_interrupted',
                'output_rejected', 'publication_unavailable'})


@dataclass(frozen=True, slots=True)
class ProcessingSummaryV1:
    binding_bytes: bytes
    as_of: datetime
    attempts: tuple[ProcessingAttemptSummaryV1, ...]
    entry_local: tuple[ProcessingEntryNoteV1, ...]

    def __post_init__(self):
        if type(self.binding_bytes) is not bytes or not 0 < len(self.binding_bytes) <= 65536:
            raise ValueError("Bounded canonical complete binding bytes required")
        model_bytes(RequestBinding, self.binding_bytes)
        if type(self.as_of) is not datetime or self.as_of.utcoffset() != timedelta(0):
            raise ValueError("Aware UTC observation required")
        object.__setattr__(self, 'as_of', self.as_of.replace(tzinfo=timezone.utc))
        if type(self.attempts) is not tuple or type(self.entry_local) is not tuple or len(self.entry_local) > 1:
            raise ValueError("Exact immutable inventory and one local note required")
        for attempt in self.attempts:
            if type(attempt) is not ProcessingAttemptSummaryV1:
                raise ValueError("Exact closed attempt projection required")
            attempt.__post_init__()
        for note in self.entry_local:
            if type(note) is not ProcessingEntryNoteV1:
                raise ValueError("Exact closed local note required")
            note.__post_init__()
