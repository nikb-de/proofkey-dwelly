"""Durable bootstrap-read accounting for unverified customer selectors.

These records are correlation bookkeeping, never authenticated case history.
Only the trusted host, after designated-identity verification, may admit a
binding. Different attempts/proofs/requests do not reset a claimed-case cap.
"""
from datetime import datetime, timedelta
import math
from typing import Literal
from uuid import uuid4

from pydantic import model_validator

from .budget import BudgetExceeded, debit, tool_timeout
from .contracts import (AuthContext, CanonicalRequest, Hash, Identifier, NonnegativeFloat,
                        NonnegativeInt, PhaseCheckpoint, PositiveFloat, RequestBinding,
                        Revision, Timestamp, WireModel)
from .identity import fingerprint, request_fingerprint
from .journal import JournalFailure, _read, _typed


class AdmissionAccount(WireModel):
    claimed_case_id: Identifier
    deadline: Timestamp
    tool_calls: NonnegativeInt = 0
    active_seconds: NonnegativeFloat = 0.0
    pending_tool_calls: NonnegativeInt = 0
    pending_active_seconds: NonnegativeFloat = 0.0
    imported: bool = False
    exhausted: bool = False

    @model_validator(mode="after")
    def finite_account(self):
        if self.tool_calls > 24 or self.active_seconds > 120.0:
            raise ValueError("Correlation accounting exceeds finite ceilings")
        if self.pending_tool_calls > self.tool_calls or self.pending_active_seconds > self.active_seconds:
            raise ValueError("Pending debt exceeds aggregate accounting")
        if self.imported and (self.pending_tool_calls or self.pending_active_seconds):
            raise ValueError("Imported account cannot retain unbound debt")
        if self.exhausted and self.active_seconds != 120.0:
            raise ValueError("Overrun must exhaust correlation active capacity")
        return self


class AdmissionAttempt(WireModel):
    attempt_id: Identifier
    claimed_case_id: Identifier
    claimed_object_id: Identifier
    claimed_principal_id: Identifier
    request_id: Identifier
    request_revision: Revision
    consent_revision: Revision
    claimed_caller_id: Identifier
    proof_digest: Hash
    business_fingerprint: Hash
    request_hash: Hash
    dedup_hash: Hash
    created_at: Timestamp
    deadline: Timestamp
    state: Literal["unbound", "transferred"] = "unbound"


class AdmissionLease(WireModel):
    entry_id: Identifier
    attempt_id: Identifier
    claimed_case_id: Identifier
    charge: Literal["unbound", "case"]
    charge_generation: Identifier | None = None
    reserved_seconds: PositiveFloat
    started_at: Timestamp
    deadline: Timestamp
    state: Literal["active", "settled", "overrun"] = "active"
    elapsed_seconds: NonnegativeFloat | None = None

    @model_validator(mode="after")
    def bounded_entry(self):
        if (self.reserved_seconds > 10.0 or self.deadline <= self.started_at
                or self.deadline > self.started_at + timedelta(seconds=self.reserved_seconds)):
            raise ValueError("Bootstrap read requires its bounded deadline")
        if (self.charge == "case") != (self.charge_generation is not None):
            raise ValueError("Case debit must retain its original accounting generation")
        if self.state == "active" and self.elapsed_seconds is not None:
            raise ValueError("Unfinished entry has no measured completion")
        if self.state != "active" and self.elapsed_seconds is None:
            raise ValueError("Finished entry needs measured elapsed time")
        if self.state == "settled" and self.elapsed_seconds > self.reserved_seconds:
            raise ValueError("Overrun cannot refund capacity")
        if self.state == "overrun" and self.elapsed_seconds <= self.reserved_seconds:
            raise ValueError("Overrun must retain observed violation")
        return self


class AdmissionAudit(WireModel):
    kind: Literal["correlation_account"] = "correlation_account"
    account_hash: Hash
    entry_id: Identifier | None = None


def _aware(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise JournalFailure("Admission accounting requires an aware host time")


def _material(auth, request):
    proof_digest = fingerprint({"proof_reference": auth.proof_reference})
    claim = {name: getattr(request, name) for name in (
        "case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision")}
    business = request_fingerprint(request)
    return dict(claimed_case_id=request.case_id, claimed_object_id=request.object_id,
        claimed_principal_id=request.principal_id, request_id=request.request_id,
        request_revision=request.request_revision, consent_revision=request.consent_revision,
        claimed_caller_id=auth.caller_id, proof_digest=proof_digest, business_fingerprint=business,
        request_hash=fingerprint(request.model_dump(mode="json")),
        dedup_hash=fingerprint({"caller_id": auth.caller_id, "proof_digest": proof_digest,
                               "claim": claim, "business_fingerprint": business}))


class AdmissionLedger:
    """Internal CaseStore collaborator; connection and transactions stay shared."""
    def __init__(self, store):
        self.store = store

    def _current(self, claimed_case_id):
        row = self.store._db.execute("SELECT checkpoint_json FROM cases WHERE case_id=?", (claimed_case_id,)).fetchone()
        if row is None or row[0] is None:
            return None
        current = self.store.checkpoint(claimed_case_id)
        if self.store.original_request(claimed_case_id, current.binding.generation) is None:
            return None
        return current

    def account(self, claimed_case_id):
        self.store._schema()
        row = self.store._db.execute("SELECT account_json FROM admission_accounts WHERE claimed_case_id=?", (claimed_case_id,)).fetchone()
        if row is None:
            raise JournalFailure("Unknown correlation account")
        account = _read(AdmissionAccount, row[0])
        if account.claimed_case_id != claimed_case_id:
            raise JournalFailure("Correlation selector index mismatch")
        audit = self.store._db.execute("SELECT event_json FROM admission_audit WHERE claimed_case_id=? ORDER BY sequence DESC LIMIT 1", (claimed_case_id,)).fetchone()
        if audit is None or _read(AdmissionAudit, audit[0]).account_hash != fingerprint(account.model_dump(mode="json")):
            raise JournalFailure("Correlation account differs from committed audit")
        return account

    def _write_account(self, account, entry_id=None):
        self.store._db.execute("UPDATE admission_accounts SET account_json=?,revision=revision+1 WHERE claimed_case_id=?",
            (account.model_dump_json(), account.claimed_case_id))
        audit = AdmissionAudit(account_hash=fingerprint(account.model_dump(mode="json")), entry_id=entry_id)
        self.store._db.execute("INSERT INTO admission_audit(claimed_case_id,event_json) VALUES(?,?)",
            (account.claimed_case_id, audit.model_dump_json()))

    def attempt(self, attempt_id):
        self.store._schema()
        row = self.store._db.execute("SELECT * FROM admission_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if row is None:
            raise JournalFailure("Unknown immutable admission attempt")
        attempt = _read(AdmissionAttempt, row["attempt_json"])
        if (attempt.attempt_id, attempt.claimed_case_id, attempt.dedup_hash, attempt.state) != (
            row["attempt_id"], row["claimed_case_id"], row["dedup_hash"], row["state"]):
            raise JournalFailure("Admission attempt index mismatch")
        claim = {"case_id": attempt.claimed_case_id, "object_id": attempt.claimed_object_id,
            "principal_id": attempt.claimed_principal_id, "request_id": attempt.request_id,
            "request_revision": attempt.request_revision, "consent_revision": attempt.consent_revision}
        expected = fingerprint({"caller_id": attempt.claimed_caller_id, "proof_digest": attempt.proof_digest,
            "claim": claim, "business_fingerprint": attempt.business_fingerprint})
        if attempt.dedup_hash != expected:
            raise JournalFailure("Admission attempt differs from immutable dedup identity")
        self.account(attempt.claimed_case_id)
        return attempt

    def start(self, attempt_id, auth, request, now, deadline):
        auth, request = _typed(AuthContext, auth), _typed(CanonicalRequest, request)
        _aware(now)
        _aware(deadline)
        if deadline <= now:
            raise BudgetExceeded("Admission allowance exhausted")
        material = _material(auth, request)
        with self.store._transaction():
            row = self.store._db.execute("SELECT 1 FROM admission_accounts WHERE claimed_case_id=?", (request.case_id,)).fetchone()
            current = self._current(request.case_id)
            if row is None:
                if current is not None:
                    deadline = min(deadline, current.budget.deadline)
                account = AdmissionAccount(claimed_case_id=request.case_id, deadline=deadline, imported=current is not None)
                self.store._db.execute("INSERT INTO admission_accounts VALUES(?,?,0)", (request.case_id, account.model_dump_json()))
                self._write_account(account)
            else:
                account = self.account(request.case_id)
                deadline = min(deadline, account.deadline)
                if current is not None:
                    deadline = min(deadline, current.budget.deadline)
                if deadline < account.deadline:
                    account = AdmissionAccount.model_validate({**account.model_dump(), "deadline": deadline})
                    self._write_account(account)
            if deadline <= now:
                raise BudgetExceeded("Admission allowance exhausted")
            existing = self.store._db.execute("SELECT attempt_id FROM admission_attempts WHERE attempt_id=? OR dedup_hash=?",
                (attempt_id, material["dedup_hash"])).fetchall()
            if existing:
                if len(existing) != 1:
                    raise JournalFailure("Admission input conflicts with immutable attempt")
                saved = self.attempt(existing[0][0])
                if any(getattr(saved, key) != value for key, value in material.items()):
                    raise JournalFailure("Admission input conflicts with immutable attempt")
                return saved
            attempt = AdmissionAttempt(attempt_id=attempt_id, created_at=now, deadline=deadline, **material)
            self.store._db.execute("INSERT INTO admission_attempts VALUES(?,?,?,?,?)", (attempt.attempt_id,
                attempt.claimed_case_id, attempt.dedup_hash, attempt.model_dump_json(), attempt.state))
            return attempt

    def begin(self, attempt_id, now):
        """Initial designated-identity read only; no authenticated permission grant."""
        _aware(now)
        try:
            with self.store._transaction():
                attempt = self.attempt(attempt_id)
                if attempt.state != "unbound":
                    raise JournalFailure("Admission attempt already transferred")
                account = self.account(attempt.claimed_case_id)
                deadline = min(account.deadline, attempt.deadline)
                if account.exhausted or account.tool_calls >= 24 or account.active_seconds >= 120.0 or now >= deadline:
                    raise BudgetExceeded("Admission allowance exhausted")
                seconds = min(10.0, 120.0 - account.active_seconds, (deadline - now).total_seconds())
                current = self._current(attempt.claimed_case_id)
                charge = "unbound" if current is None else "case"
                generation = None if current is None else current.binding.generation
                if current is not None:
                    seconds = min(seconds, tool_timeout(current.budget, now))
                    budget = debit(current.budget, "tool_calls", 1, now)
                    budget = debit(budget, "active_seconds", seconds, now)
                    self.store._write_checkpoint(PhaseCheckpoint.model_validate({**current.model_dump(), "budget": budget}))
                data = account.model_dump()
                data["tool_calls"] += 1
                data["active_seconds"] += seconds
                if charge == "unbound":
                    if account.imported:
                        raise JournalFailure("Imported correlation account lost authenticated history")
                    data["pending_tool_calls"] += 1
                    data["pending_active_seconds"] += seconds
                lease = AdmissionLease(entry_id="admission:" + uuid4().hex, attempt_id=attempt.attempt_id,
                    claimed_case_id=attempt.claimed_case_id, charge=charge, charge_generation=generation,
                    reserved_seconds=seconds, started_at=now, deadline=min(deadline, now + timedelta(seconds=seconds)))
                self.store._db.execute("INSERT INTO admission_entries VALUES(?,?,?,?,?,?)", (lease.entry_id,
                    lease.attempt_id, lease.claimed_case_id, lease.charge_generation, lease.model_dump_json(), lease.state))
                self._write_account(AdmissionAccount.model_validate(data), lease.entry_id)
                return lease
        except BudgetExceeded as error:
            raise BudgetExceeded("Admission allowance exhausted") from error
        except JournalFailure as error:
            raise JournalFailure("Admission read unavailable") from error

    def entry(self, entry_id):
        self.store._schema()
        row = self.store._db.execute("SELECT * FROM admission_entries WHERE entry_id=?", (entry_id,)).fetchone()
        if row is None:
            raise JournalFailure("Unknown admission entry")
        lease = _read(AdmissionLease, row["lease_json"])
        attempt = self.attempt(lease.attempt_id)
        if (lease.entry_id, lease.attempt_id, lease.claimed_case_id, lease.charge_generation, lease.state) != (
            row["entry_id"], row["attempt_id"], row["claimed_case_id"], row["charge_generation"], row["state"]):
            raise JournalFailure("Admission entry index mismatch")
        if attempt.claimed_case_id != lease.claimed_case_id:
            raise JournalFailure("Admission entry belongs to another correlation account")
        if lease.charge == "case":
            self.store._binding(lease.claimed_case_id, lease.charge_generation)
        return lease

    def finish(self, entry_id, elapsed_seconds):
        """Trusted measured completion before transfer only; unknowns keep full debt."""
        if type(elapsed_seconds) not in (int, float) or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise JournalFailure("Admission completion requires finite nonnegative elapsed time")
        overrun = False
        with self.store._transaction():
            lease = self.entry(entry_id)
            attempt = self.attempt(lease.attempt_id)
            account = self.account(lease.claimed_case_id)
            if lease.state != "active" or attempt.state == "transferred" or (lease.charge == "unbound" and account.imported):
                raise JournalFailure("Admission completion already settled or transferred")
            if account.exhausted or self.store._db.execute("SELECT 1 FROM entries WHERE case_id=? AND state='overrun'", (lease.claimed_case_id,)).fetchone():
                raise BudgetExceeded("Admission allowance exhausted")
            current = self._current(lease.claimed_case_id) if lease.charge == "case" else None
            if lease.charge == "case" and current is None:
                raise JournalFailure("Admission case accounting is unavailable")
            data = account.model_dump()
            if elapsed_seconds > lease.reserved_seconds:
                overrun = True
                state = "overrun"
                data["active_seconds"] = 120.0
                data["exhausted"] = True
                if lease.charge == "unbound":
                    data["pending_active_seconds"] = 120.0
                if current is not None:
                    checkpoint_data = current.model_dump()
                    checkpoint_data["budget"]["active_seconds"] = current.budget.max_active_seconds
            else:
                state = "settled"
                refund = lease.reserved_seconds - elapsed_seconds
                data["active_seconds"] -= refund
                if lease.charge == "unbound":
                    data["pending_active_seconds"] -= refund
                if current is not None:
                    checkpoint_data = current.model_dump()
                    checkpoint_data["budget"]["active_seconds"] -= refund
            finished = AdmissionLease.model_validate({**lease.model_dump(), "state": state, "elapsed_seconds": elapsed_seconds})
            self.store._db.execute("UPDATE admission_entries SET lease_json=?,state=? WHERE entry_id=?", (finished.model_dump_json(), state, entry_id))
            if current is not None:
                self.store._write_checkpoint(PhaseCheckpoint.model_validate(checkpoint_data))
            self._write_account(AdmissionAccount.model_validate(data), lease.entry_id)
        if overrun:
            raise BudgetExceeded("Admission allowance exhausted")

    def import_pending(self, case_id):
        """Called only inside authentic trusted-host admission's transaction."""
        if self.store._db.execute("SELECT 1 FROM admission_accounts WHERE claimed_case_id=?", (case_id,)).fetchone() is None:
            return
        account = self.account(case_id)
        current = self.store.checkpoint(case_id)
        data = current.model_dump()
        data["budget"]["tool_calls"] += account.pending_tool_calls
        data["budget"]["active_seconds"] += account.pending_active_seconds
        if (data["budget"]["tool_calls"] > current.budget.max_tool_calls
                or data["budget"]["active_seconds"] > current.budget.max_active_seconds):
            raise BudgetExceeded("Admission allowance exhausted")
        data["budget"]["deadline"] = min(current.budget.deadline, account.deadline)
        data["deadline"] = min(current.deadline, data["budget"]["deadline"])
        self.store._write_checkpoint(PhaseCheckpoint.model_validate(data))
        account_data = account.model_dump()
        account_data.update(imported=True, pending_tool_calls=0, pending_active_seconds=0.0)
        self._write_account(AdmissionAccount.model_validate(account_data))

    def admit(self, attempt_id, binding, request, checkpoint):
        return self._admit(attempt_id, binding, request, checkpoint)

    def admit_refusal(self, attempt_id, binding, request, checkpoint, expected_previous_binding):
        return self._admit(attempt_id, binding, request, checkpoint, expected_previous_binding)

    def _admit(self, attempt_id, binding, request, checkpoint, expected_previous_binding=None):
        binding, request = _typed(RequestBinding, binding), _typed(CanonicalRequest, request)
        with self.store._transaction():
            attempt = self.attempt(attempt_id)
            if attempt.state != "unbound":
                raise JournalFailure("Admission attempt already transferred")
            if (attempt.request_hash != fingerprint(request.model_dump(mode="json"))
                    or attempt.claimed_case_id != binding.case_id or attempt.business_fingerprint != binding.fingerprint):
                raise JournalFailure("Admission original input conflicts with immutable attempt")
            self.store._request_identity(binding, request)
            if expected_previous_binding is None:
                self.store.admit(binding, request, checkpoint)
            else:
                self.store._admit_refusal(binding, request, checkpoint, expected_previous_binding)
            transferred = AdmissionAttempt.model_validate({**attempt.model_dump(), "state": "transferred"})
            self.store._db.execute("UPDATE admission_attempts SET attempt_json=?,state='transferred' WHERE attempt_id=?",
                (transferred.model_dump_json(), attempt_id))

    def require_imported(self, case_id):
        if self.store._db.execute("SELECT 1 FROM admission_accounts WHERE claimed_case_id=?", (case_id,)).fetchone():
            if not self.account(case_id).imported:
                raise JournalFailure("Admission accounting must be transferred before external entry")

    def exhausted(self, case_id):
        if self.store._db.execute("SELECT 1 FROM admission_accounts WHERE claimed_case_id=?", (case_id,)).fetchone():
            return self.account(case_id).exhausted
        return False

    def validate_all(self):
        for row in self.store._db.execute("SELECT claimed_case_id FROM admission_accounts").fetchall():
            self.account(row[0])
        for row in self.store._db.execute("SELECT attempt_id FROM admission_attempts").fetchall():
            self.attempt(row[0])
        for row in self.store._db.execute("SELECT entry_id FROM admission_entries").fetchall():
            self.entry(row[0])
        for row in self.store._db.execute("SELECT claimed_case_id,event_json FROM admission_audit").fetchall():
            audit = _read(AdmissionAudit, row[1])
            if audit.entry_id is not None and self.entry(audit.entry_id).claimed_case_id != row[0]:
                raise JournalFailure("Admission audit references another correlation account")
