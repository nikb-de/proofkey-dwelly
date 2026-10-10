"""Transactional reviewed model context and explicitly simulated acceptance."""
from copy import deepcopy
import json
import uuid

import pytest

from tools.dwelly_analysis import model
from tools.dwelly_platform.models import project_snapshot
from tools.dwelly_platform.tests import test_coordination as existing


@pytest.fixture
def case():
    if not existing.DSN:
        pytest.skip("requires local PostgreSQL")
    fixture = existing.CoordinationTests()
    fixture.setUp()
    try:
        yield fixture
    finally:
        fixture.doCleanups()


def reviewed(case, ids):
    snapshot = case.store.get("demo-1")
    source = project_snapshot(snapshot)
    candidate = model.parse(source, {"text": json.dumps({
        "state": "ready", "waiting_for": [], "evidence_event_ids": ids,
        "uncertainty": [], "next_action": {"type": "operator_review", "target_actor_id": None,
                                                "description": "Review the cancellation source."}})})
    return {"run_id": "run-1", "status": "succeeded", "case_id": "demo-1",
            "step_index": snapshot["revision"], "input": source, "reference": None,
            "source": {"kind": "platform_case", "case_id": "demo-1", "revision": snapshot["revision"],
                       "snapshot_hash": snapshot["snapshot_hash"]}, "candidate": candidate}


def request_with_model(case):
    case.initialize()
    eid = case.source("Please cancel")
    return case.body("request_cancellation", evidence_event_ids=[eid],
                     model_run_id="run-1", model_review_note="I checked the source and chose this command."), reviewed(case, [eid])


def apply_review(case, body, job=None, resolver=None, key=None):
    return case.store.coordination_command("demo-1", key or uuid.uuid4().hex, body,
                                           model_resolver=resolver or (lambda run_id: deepcopy(job)))


def test_reviewed_context_is_audited_without_model_authority_and_replay_skips_resolver(case):
    body, job = request_with_model(case)
    result = apply_review(case, body, job, key="reviewed")
    assert result["phase"] == "cancellation_pending"
    context = result["audit_history"][-1]["model_context"]
    assert context["run_id"] == "run-1"
    assert context["input_hash"] == job["input"]["input_hash"]
    assert context["model_review_note"] == body["model_review_note"]
    assert "next_action" not in context
    assert json.loads(case.store.get("demo-1")["events"][-1]["text"])["model_context"] == context
    def disappeared(run_id):
        raise AssertionError("A replay must never resolve a model job")
    assert apply_review(case, body, resolver=disappeared, key="reviewed") == result


@pytest.mark.parametrize("change,code", [
    (lambda job: job.update(status="queued"), "model_context_unavailable"),
    (lambda job: job.update(status="failed"), "model_context_unavailable"),
    (lambda job: job.update(case_id="other"), "model_context_stale"),
    (lambda job: job["source"].update(revision=0), "model_context_stale"),
    (lambda job: job["source"].update(snapshot_hash="0" * 64), "model_context_stale"),
    (lambda job: job["input"].update(goal="Tampered source"), "model_context_stale"),
    (lambda job: job.update(reference={"label": "secret"}), "invalid_model_context"),
    (lambda job: job["candidate"].update(schema_version="other"), "invalid_model_context"),
    (lambda job: job["candidate"].update(input_hash="0" * 64), "model_context_stale"),
    (lambda job: job["candidate"].update(evidence_event_ids=["missing"]), "invalid_model_context"),
    (lambda job: job["candidate"]["next_action"].update(type="request_cancellation"), "invalid_model_context"),
])
def test_bad_model_context_is_atomic(case, change, code):
    body, job = request_with_model(case)
    before, state = case.store.get("demo-1"), case.store.coordination_detail("demo-1")
    change(job)
    case.error(code, apply_review, case, body, job)
    assert case.store.get("demo-1") == before
    assert case.store.coordination_detail("demo-1") == state


def test_model_selected_evidence_subset_and_normal_actor_policy_both_apply(case):
    body, job = request_with_model(case)
    job["candidate"]["evidence_event_ids"] = [case.store.get("demo-1")["events"][0]["event_id"]]
    case.error("invalid_model_context", apply_review, case, body, job)
    wrong = case.source("Cancel please", "courier-1")
    body = case.body("request_cancellation", evidence_event_ids=[wrong], model_run_id="run-1", model_review_note="Checked")
    case.error("evidence_actor_mismatch", apply_review, case, body, reviewed(case, [wrong]))


def test_missing_model_unknown_resolver_error_and_optimistic_checks_are_sanitized(case):
    body, job = request_with_model(case)
    case.error("model_context_unavailable", case.store.coordination_command, "demo-1", "missing", body)
    def failed(run_id):
        raise RuntimeError("provider secret must not escape")
    case.error("model_context_unavailable", apply_review, case, body, resolver=failed)
    def unexpected(run_id):
        raise AssertionError("Must reject stale state before resolving")
    case.error("workflow_conflict", apply_review, case, {**body, "expected_workflow_version": 0}, resolver=unexpected)
    case.source("New event")
    case.error("revision_conflict", apply_review, case, body, resolver=unexpected)


@pytest.mark.parametrize("change", [
    lambda body: body.pop("model_review_note"),
    lambda body: body.pop("model_run_id"),
    lambda body: body.update(model_review_note=" "),
    lambda body: body.update(model_review_note="x" * 1001),
    lambda body: body.update(model_review_note=" " * 1000 + "x"),
    lambda body: body.update(model_run_id=""),
])
def test_optional_model_fields_must_be_paired_and_bounded(case, change):
    body, job = request_with_model(case)
    change(body)
    case.error("invalid_model_context", apply_review, case, body, job)


def test_combined_model_and_command_audit_size_is_bounded_atomically(case):
    case.initialize()
    ids = [case.source("Need help") for _ in range(5)]
    body = case.body("escalate", reason="x" * 2048, evidence_event_ids=ids,
                     model_run_id="run-1", model_review_note="y" * 1000)
    before = case.store.get("demo-1")
    state = case.store.coordination_detail("demo-1")
    case.error("coordination_audit_too_large", apply_review, case, body, reviewed(case, ids))
    assert case.store.get("demo-1") == before
    assert case.store.coordination_detail("demo-1") == state


def test_initialization_cannot_attach_model_review(case):
    body = case.body("initialize", dispatch_actor_id="courier-1",
                     original_booking={"booking_id": "old", "terms": case.terms()},
                     model_run_id="run-1", model_review_note="Checked")
    case.error("invalid_model_context", apply_review, case, body)
    assert case.store.get("demo-1")["revision"] == 0


def local_acceptance(case, state):
    return case.body("record_local_acceptance", offer_id=state["offer"]["offer_id"],
                     terms_hash=state["offer"]["terms_hash"], acknowledged=True)


def test_local_acceptance_appends_simulated_source_then_final_revision_consent_and_replays(case):
    state = case.offered()
    before = case.store.get("demo-1")
    body = local_acceptance(case, state)
    result = case.store.coordination_command("demo-1", "accept", body)
    snapshot = case.store.get("demo-1")
    assert result["phase"] == "ready_to_book"
    assert snapshot["revision"] == before["revision"] + 2
    assert result["consent"]["created_revision"] == snapshot["revision"]
    simulated, audit = snapshot["events"][-2:]
    assert simulated["sender_id"] == "customer-1"
    assert simulated["channel"] != "internal"
    assert simulated["recipient_ids"] == ["operator-1"]
    assert "simulat" in simulated["text"].lower() and "not authenticated" in simulated["text"].lower()
    assert state["offer"]["offer_id"] in simulated["text"] and state["offer"]["terms_hash"] in simulated["text"]
    assert result["consent"]["evidence_event_ids"] == [simulated["event_id"]]
    assert json.loads(audit["text"])["command"] == "record_local_acceptance"
    assert result["external_effects"] == 0 and result["physical_delivery"] == "not_confirmed"
    assert case.store.coordination_command("demo-1", "accept", body) == result
    assert case.store.get("demo-1") == snapshot
    booked = case.command("request_booking", offer_id=state["offer"]["offer_id"], terms_hash=state["offer"]["terms_hash"])
    assert booked["phase"] == "booking_pending"


@pytest.mark.parametrize("change,code", [
    ({"acknowledged": False}, "invalid_coordination_request"),
    ({"acknowledged": 1}, "invalid_coordination_request"),
    ({"offer_id": "changed"}, "offer_mismatch"),
    ({"terms_hash": "0" * 64}, "offer_mismatch"),
    ({"expected_revision": 0}, "revision_conflict"),
    ({"model_run_id": "run-1", "model_review_note": "Checked"}, "invalid_model_context"),
])
def test_invalid_local_acceptance_appends_nothing(case, change, code):
    state = case.offered()
    before = case.store.get("demo-1")
    case.error(code, case.store.coordination_command, "demo-1", "accept", {**local_acceptance(case, state), **change})
    assert case.store.get("demo-1") == before
    assert case.store.coordination_detail("demo-1") == state


def test_local_acceptance_audit_failure_rolls_back_synthetic_source_and_idempotency(case):
    state = case.offered()
    before = case.store.get("demo-1")
    body = local_acceptance(case, state)
    with case.store._transaction(write=True) as connection:
        connection.execute("""CREATE FUNCTION reject_acceptance_audit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.revision = %s THEN RAISE EXCEPTION 'injected final audit failure'; END IF; RETURN NEW; END $$""" % (before["revision"] + 2))
        connection.execute("CREATE TRIGGER reject_acceptance_audit BEFORE INSERT ON case_snapshots FOR EACH ROW EXECUTE FUNCTION reject_acceptance_audit()")
    case.error("case_storage_error", case.store.coordination_command, "demo-1", "retry-accept", body)
    assert case.store.get("demo-1") == before
    assert case.store.coordination_detail("demo-1") == state
    with case.store._transaction(write=True) as connection:
        assert connection.execute("SELECT count(*) FROM platform_requests WHERE scope='coordination:demo-1' AND idempotency_key='retry-accept'").fetchone()[0] == 0
        connection.execute("DROP TRIGGER reject_acceptance_audit ON case_snapshots")
    assert case.store.coordination_command("demo-1", "retry-accept", body)["phase"] == "ready_to_book"


def test_fresh_second_local_acceptance_is_phase_blocked(case):
    state = case.offered()
    case.store.coordination_command("demo-1", "first", local_acceptance(case, state))
    before = case.store.get("demo-1")
    case.error("coordination_transition_blocked", case.store.coordination_command,
               "demo-1", "second", local_acceptance(case, state))
    assert case.store.get("demo-1") == before
