"""Trusted entry deadlines constrain real SQLite effects without changing intent identity."""
from contextlib import contextmanager
from datetime import timedelta, timezone
import inspect
from pathlib import Path
import sqlite3
import tempfile
import unittest

from proofkey.adapters.world import SimulatedWorld
from proofkey.identity import fingerprint
from proofkey import ports
from support import FakeClock, NOW, make_intent, load_test_profile

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/development/world.json"
EFFECTS = {
    "reschedule": ("scheduling", {"slot": "S1"}),
    "register_goods_refusal": ("delivery", {"inventory": {"item-1": 1}}),
    "register_service_refusal": ("delivery", {"scope": "service"}),
    "create_return": ("returns", {"inventory": {"item-1": 1}, "destination": "D1"}),
    "send_clarification": ("messaging", {"question_id": "Q1", "recipient": "U1", "text": "Which slot?"}),
    "send_status": ("messaging", {"recipient": "U1", "text": "Saved"}),
    "enqueue_handoff": ("operator", {"packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "recipient": "OP1"}),
    "transfer_owner": ("operator", {"transfer_id": "T1", "packet_id": "P1", "packet_revision": "v1", "packet_hash": "packet-hash", "target_owner": "OP2"}),
}


class DeadlineFaultWorld(SimulatedWorld):
    """Test driver: move the shared clock at selected real transaction boundaries."""
    fault_point = None
    advance_seconds = 2
    expired_point = None

    def expire(self, point):
        if self.fault_point == point:
            self.fault_point = None
            self.expired_point = point
            self._clock.advance(self.advance_seconds)

    @contextmanager
    def _connect(self):
        with super()._connect() as connection:
            def trace(statement):
                if statement.startswith("INSERT INTO reservations"):
                    self.expire("reservation_insert")
                elif statement.startswith("INSERT INTO effects"):
                    self.expire("effect_insert")
                elif statement.startswith("INSERT INTO final_rejections"):
                    self.expire("rejection_insert")
            connection.set_trace_callback(trace)
            yield connection

    def _write_identity_allowed(self, connection, intent):
        result = super()._write_identity_allowed(connection, intent)
        self.expire("identity")
        return result

    def _effect_observation_data(self, connection, intent, values):
        result = super()._effect_observation_data(connection, intent, values)
        self.expire("observations")
        return result


class AdapterDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.serial = 0
        self.fresh()

    def fresh(self, **kwargs):
        self.serial += 1
        self.path = Path(self.folder.name) / f"world-{self.serial}.sqlite"
        self.clock = FakeClock()
        self.world = DeadlineFaultWorld(self.path, FIXTURE, clock=self.clock, **kwargs)
        self.bundle = self.world.bundle()

    def intent(self, operation="reschedule", **kwargs):
        if operation == "create_return":
            self.world.mutate("goods.refusal", "verified")
        return make_intent(operation=operation, arguments=EFFECTS[operation][1],
                           expected_revisions=self.world.material_revisions(), **kwargs)

    def dispatch(self, intent, **kwargs):
        return getattr(getattr(self.bundle, EFFECTS[intent.operation][0]), intent.operation)(intent, **kwargs)

    def count(self, table):
        with sqlite3.connect(self.path) as connection:
            return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_all_effect_ports_and_protocols_accept_keyword_only_scope(self):
        for operation, (port, _) in EFFECTS.items():
            with self.subTest(operation=operation):
                method = getattr(getattr(self.bundle, port), operation)
                protocol = getattr(ports, port.title() + "Port")
                for function in (method, getattr(protocol, operation), self.world._dispatch):
                    parameter = inspect.signature(function).parameters["deadline"]
                    self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
                    self.assertIsNone(parameter.default)

    def test_all_eight_effects_honor_expired_scope(self):
        for operation in EFFECTS:
            with self.subTest(operation=operation):
                self.fresh()
                result = self.dispatch(self.intent(operation), deadline=NOW)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(self.count("effects"), 0)
                self.assertEqual(self.count("reservations"), 0)
                self.assertEqual(self.count("pressure"), 0)

    def test_all_eight_effects_succeed_within_scope_and_none_compatibility(self):
        for operation in EFFECTS:
            for scope in (None, NOW + timedelta(seconds=1)):
                with self.subTest(operation=operation, scope=scope):
                    self.fresh()
                    result = self.dispatch(self.intent(operation), deadline=scope)
                    self.assertEqual(result.status, "acknowledged")
                    self.assertEqual(self.world.effect_count(operation), 1)

    def test_invalid_deadlines_fail_closed_before_reservation(self):
        for scope in (NOW.replace(tzinfo=None), "2026-10-08T10:00:01Z", 1, False, object()):
            with self.subTest(scope=scope):
                self.fresh()
                result = self.dispatch(self.intent(), deadline=scope)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(self.count("effects"), 0)
                self.assertEqual(self.count("pressure"), 0)

    def test_short_scope_expiry_during_identity_check_fences_business_write(self):
        intent = self.intent()
        self.world.fault_point = "identity"
        result = self.dispatch(intent, deadline=NOW + timedelta(seconds=1))
        self.assertEqual(result.status, "rejected")
        self.assertEqual(self.world.effect_count("reschedule"), 0)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT value FROM facts WHERE identity='scheduling.slot'").fetchone()[0], '"S0"')

    def test_final_transaction_guard_rolls_back_after_observations_and_effect_insert(self):
        for point in ("observations", "effect_insert"):
            with self.subTest(point=point):
                self.fresh()
                intent = self.intent()
                self.world.fault_point = point
                result = self.dispatch(intent, deadline=NOW + timedelta(seconds=1))
                self.assertEqual(self.world.expired_point, point, "real transaction expiry hook did not fire")
                self.assertEqual(self.clock.now(), NOW + timedelta(seconds=self.world.advance_seconds))
                self.assertEqual(result.status, "rejected")
                self.assertEqual(self.world.effect_count("reschedule"), 0)
                with sqlite3.connect(self.path) as connection:
                    self.assertEqual(connection.execute("SELECT value FROM facts WHERE identity='scheduling.slot'").fetchone()[0], '"S0"')

    def test_expiry_fences_saved_rejection_and_duplicate_acknowledgement(self):
        for point in ("identity", "rejection_insert"):
            with self.subTest(point=point):
                self.fresh()
                intent = self.intent()
                self.world.set_fault("reschedule", "business_rejection")
                self.world.fault_point = point
                result = self.dispatch(intent, deadline=NOW + timedelta(seconds=1))
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.reason, "deadline_expired")
                self.assertEqual(self.count("final_rejections"), 0)
        self.fresh()
        intent = self.intent()
        self.assertEqual(self.dispatch(intent).status, "acknowledged")
        self.world.fault_point = "identity"
        result = self.dispatch(intent, deadline=NOW + timedelta(seconds=1))
        self.assertEqual(result.status, "rejected")
        self.assertIsNone(result.provider_request_id)
        self.assertEqual(self.world.effect_count("reschedule"), 1)

    def test_reservation_expires_at_short_scope_without_identity_change(self):
        # Model a crashed provider's deferred cleanup with the real durable reservation.
        self.world._release = lambda account, token: None
        intent = self.intent()
        original_json = intent.model_dump_json()
        original_hash = fingerprint(intent.model_dump(mode="json"))
        scope = (NOW + timedelta(seconds=1)).astimezone(timezone(timedelta(hours=1)))
        first = self.dispatch(intent, deadline=scope)
        self.assertEqual(first.status, "acknowledged")
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT expires_at FROM reservations").fetchone()[0], (NOW + timedelta(seconds=1)).timestamp())
            identity = connection.execute("SELECT identity_hash,provider_key,fingerprint FROM effects").fetchone()
            self.assertEqual(identity, (original_hash, intent.provider_key, intent.argument_fingerprint))
        self.assertEqual(self.dispatch(intent, deadline=NOW + timedelta(seconds=3)).status, "rejected")
        self.clock.advance(1)
        second = self.dispatch(intent, deadline=NOW + timedelta(seconds=3))
        self.assertEqual(second.status, "acknowledged")
        self.assertEqual(second.provider_request_id, first.provider_request_id)
        self.assertEqual(self.world.effect_count("reschedule"), 1)
        self.assertEqual(intent.model_dump_json(), original_json)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT used FROM pressure").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT identity_hash,provider_key,fingerprint FROM effects").fetchone(), identity)

    def test_original_and_native_bounds_are_never_extended(self):
        for original_seconds, native_seconds, supplied_seconds, advance_seconds in ((1, 10, 30, 2), (7200, 10, 30, 11), (7200, 1, 30, 2)):
            with self.subTest(original=original_seconds, native=native_seconds):
                data = load_test_profile().model_dump()
                data["capabilities"]["reschedule"]["timeout_seconds"] = native_seconds
                self.fresh(profile=ports_profile(data))
                intent = self.intent(deadline=NOW + timedelta(seconds=original_seconds))
                self.world.fault_point = "identity"
                self.world.advance_seconds = advance_seconds
                result = self.dispatch(intent, deadline=NOW + timedelta(seconds=supplied_seconds))
                self.assertEqual(result.status, "rejected")
                self.assertEqual(self.count("effects"), 0)

    def test_expiry_during_reservation_rolls_back_durable_slot(self):
        intent = self.intent()
        self.world.fault_point = "reservation_insert"
        result = self.dispatch(intent, deadline=NOW + timedelta(seconds=1))
        self.assertEqual(result.status, "rejected")
        self.assertEqual(self.count("reservations"), 0)
        self.assertEqual(self.count("pressure"), 0)
        self.assertEqual(self.count("effects"), 0)


def ports_profile(data):
    from proofkey.contracts import EnvironmentProfile
    return EnvironmentProfile.model_validate(data)
