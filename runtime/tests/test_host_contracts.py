"""Host-local intake/state tests; body fields never provide host authority."""
from datetime import datetime, timedelta, timezone
import json
import unittest

from proofkey.contracts import CanonicalRequest
from proofkey.execution import ExecutionContext
from proofkey.host_contracts import (CommandInventoryV1, CommandReceiptV1, ExecutionWindowV1,
                                    HostLimitsV1, RunCommandV1, parse_command)


def request():
    return CanonicalRequest(case_id="C1", object_id="O1", principal_id="U1", request_id="REQ1",
        request_revision="v1", consent_revision="v1", kind="reschedule_window", consent_mode="window",
        arguments={"window_start": "2026-10-08T10:00:00+00:00", "window_end": "2026-10-08T12:00:00+00:00",
                   "inventory": {"item-1": 1}}, evidence_ids=[])


class HostContractTests(unittest.TestCase):
    def test_closed_command_revalidates_and_freezes_nested_business_payload(self):
        payload = {"tag": "run", "release_id": "host-window-replay-v1", "request": request().model_dump()}
        command = parse_command(payload)
        payload["request"]["arguments"]["inventory"]["item-1"] = 7
        self.assertEqual(command.request.arguments["inventory"], {"item-1": 1})
        with self.assertRaises(TypeError):
            command.request.arguments["inventory"]["item-1"] = 2
        with self.assertRaises(ValueError):
            command.model_copy(update={"auth": {"caller_id": "U1", "proof_reference": "body-proof"}})

    def test_auth_context_paths_and_unknown_tags_cannot_be_command_intake(self):
        base = {"tag": "run", "release_id": "host-window-replay-v1", "request": request().model_dump()}
        for field in ("auth", "execution", "grant", "profile_path", "callback"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_command({**base, field: "body-cannot-configure-host"})
        for value in ({"tag": "unknown", "release_id": "registered"},
                      {"tag": "stop", "release_id": "registered", "case_id": "C1"},
                      {"tag": "batch", "release_id": "registered", "requests": []}):
            with self.assertRaises(ValueError):
                parse_command(value)

    def test_bounded_exact_json_rejects_duplicate_nonfinite_cycles_and_custom_serialization(self):
        cycle = {}
        cycle["self"] = cycle
        deep = {"tag": "inspect-profile", "release_id": "registered"}
        for _ in range(40):
            deep = {"nested": deep}
        for value in (b'{"tag":"inspect-profile","tag":"stop","release_id":"registered"}',
                      {"tag": "inspect-profile", "release_id": float("nan")}, cycle, deep, object()):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                parse_command(value)
        with self.assertRaises(ValueError):
            parse_command({"tag": "inspect-profile", "release_id": "x" * 100}, max_bytes=20)
        raw = json.dumps({"tag": "inspect-profile", "release_id": "registered"}).encode()
        self.assertEqual(parse_command(raw).tag, "inspect-profile")

    def test_host_limits_reject_nonfinite_zero_and_boolean_ceilings(self):
        for update in ({"queue_capacity": 0}, {"queue_capacity": True}, {"max_execution_seconds": float("inf")},
                       {"shutdown_max_seconds": 0.0}, {"max_command_bytes": -1}):
            with self.assertRaises(ValueError):
                HostLimitsV1(**update)

    def test_original_window_snapshot_cannot_reconstruct_a_longer_context(self):
        start = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
        context = ExecutionContext(start + timedelta(seconds=10), start, -100.0, -90.0)
        window = ExecutionWindowV1.from_context(context)
        self.assertEqual(window.captured_monotonic, -100.0)
        with self.assertRaises(ValueError):
            window.model_copy(update={"monotonic_deadline": -80.0})

    def test_receipt_cannot_invent_a_result_or_cancel_started_work(self):
        base = dict(command_id="a" * 32, command_tag="run", release_id="registered", mode="synthetic_replay",
                    clock_mode="synthetic_replay", payload_hash="b" * 64, inventory_status="not_admitted")
        with self.assertRaises(ValueError):
            CommandReceiptV1(**base, outcome="result")
        with self.assertRaises(ValueError):
            CommandReceiptV1(**base, outcome="cancelled_before_start", started_at=datetime.now(timezone.utc))
        pending = CommandReceiptV1(**base, outcome="started_pending", started_at=datetime.now(timezone.utc))
        self.assertIsNone(pending.result)

    def test_inventory_is_safe_digest_only_and_cannot_claim_unreturned_result(self):
        start = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
        window = ExecutionWindowV1.from_context(ExecutionContext(start + timedelta(seconds=10), start, 0.0, 10.0))
        base = dict(command_id="a" * 32, command_tag="run", release_id="registered", mode="synthetic_replay",
                    payload_hash="b" * 64, execution=window, phase="queued", timestamp=start)
        for update in ({"proof": "never-store-this"}, {"body": {"principal_id": "U1"}},
                       {"result_hash": "c" * 64}, {"outcome": "result"}):
            with self.assertRaises(ValueError):
                CommandInventoryV1(**{**base, **update})
