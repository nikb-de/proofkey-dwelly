"""Subprocess fixture with a real separate SQLite external authority."""
from pathlib import Path
import signal
import sqlite3
import sys

from proofkey.contracts import VerificationResult
from proofkey.journal import CaseStore
from support import NOW, make_binding, make_checkpoint, make_intent, make_request


def boundary(stage, wanted):
    if stage == wanted:
        print("BOUNDARY " + stage, flush=True)
        signal.pause()


def main():
    folder, wanted = Path(sys.argv[1]), sys.argv[2]
    if wanted == "admission":
        from support import make_auth
        store = CaseStore(folder / "journal.sqlite")
        attempt = store.start_admission("attempt-1", make_auth(), make_request(), NOW, make_checkpoint().deadline)
        lease = store.begin_admission_read(attempt.attempt_id, NOW)
        print("ENTRY " + lease.entry_id, flush=True)
        boundary("admission", wanted)
        return
    if wanted.startswith("provider:"):
        from proofkey.contracts import BudgetLedger, RoleAllowance
        from test_provider_invocation_recovery import permit, invocation
        role = wanted.split(":", 1)[1]
        store = CaseStore(folder / "journal.sqlite")
        budget = BudgetLedger(case_id="C1", deadline=make_checkpoint().deadline,
            role_allowances={role: RoleAllowance(max_invocations=2, max_cost=4.0, usage_allowances={"tokens": 40.0})})
        store.admit(make_binding(), make_request(), make_checkpoint(budget=budget))
        grant = permit(role)
        store.register_campaign(grant)
        store.reserve_invocation(invocation(grant), NOW)
        # This is the post-commit entry boundary; no actual provider is called.
        boundary(wanted, wanted)
        return
    external = sqlite3.connect(folder / "external.sqlite")
    external.execute("PRAGMA journal_mode=WAL")
    external.execute("PRAGMA synchronous=FULL")
    external.execute("CREATE TABLE writes(action_id TEXT PRIMARY KEY,slot TEXT NOT NULL)")
    external.commit()
    store = CaseStore(folder / "journal.sqlite")
    store.bind(make_binding())
    store.save_request(make_binding(), make_request())
    store.save_checkpoint(make_checkpoint())
    intent = make_intent()
    store.prepare(intent)
    if wanted == "read":
        lease = store.begin_read("C1", NOW, action_id=intent.action_id)
        print("ENTRY " + lease.entry_id, flush=True)
        boundary("read", wanted)
        return
    boundary("prepare", wanted)
    store.begin_dispatch(intent, NOW)
    boundary("mark", wanted)
    external.execute("INSERT INTO writes VALUES(?,?)", (intent.action_id, "S1"))
    external.commit()
    boundary("external", wanted)
    # Read the distinct provider database before committing verification.
    assert external.execute("SELECT slot FROM writes WHERE action_id=?", (intent.action_id,)).fetchone()[0] == "S1"
    boundary("preverify", wanted)
    store.record_verification(intent.action_id, VerificationResult(status="verified", object_id="O1",
        action_id=intent.action_id, fingerprint=intent.argument_fingerprint, postcondition={"slot": "S1"},
        evidence_refs=["separate-sqlite-authority"], as_of=NOW))
    boundary("postverify", wanted)


if __name__ == "__main__":
    main()
