"""Point-in-time shadow association against actual admitted synthetic state."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import importlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

RUNTIME_AVAILABLE = importlib.util.find_spec("proofkey") is not None
if RUNTIME_AVAILABLE:
    from proofkey.identity import fingerprint
    from proofkey.journal import CaseStore
    from support import NOW, DEADLINE, make_auth, make_binding, make_checkpoint, make_request


@unittest.skipUnless(RUNTIME_AVAILABLE, "Requires runtime environment and PYTHONPATH=runtime/src:runtime/tests")
class ShadowBindingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "journal.sqlite"
        self.store = CaseStore(self.path)
        self.addCleanup(self.store.close)
        self.store.admit(make_binding(), make_request(), make_checkpoint())
        self.checkpoint = self.store.checkpoint("C1")
        self.source_case_id = "source-case-1"
        self.snapshot_hash = "a" * 64

    def api(self):
        try:
            return importlib.import_module("tools.dwelly_bridge.runtime_binding")
        except ImportError:
            self.fail("Optional runtime shadow resolver is unavailable")

    def target(self, **changes):
        fields = dict(source_case_id=self.source_case_id, source_snapshot_hash=self.snapshot_hash,
                      binding=make_binding(), checkpoint_hash=fingerprint(self.checkpoint.model_dump(mode="json")),
                      profile_version="v1", process_version="v1", policy_version="v1", allowed_caller_ids=("U1",))
        return self.api().RuntimeShadowTarget(**{**fields, **changes})

    def resolver(self, *, authorized=True, registrations=None, **changes):
        args = dict(authorize=lambda target, auth: authorized and auth.proof_reference == "synthetic-proof",
                    auth=make_auth(), clock=lambda: NOW)
        return self.api().RuntimeShadowResolver(self.store, (self.target(),) if registrations is None else registrations,
                                                **{**args, **changes})

    def resolve(self, resolver=None):
        return (resolver or self.resolver())(self.source_case_id, self.snapshot_hash)

    def contents(self):
        return list(self.store._db.iterdump())

    def test_exact_admitted_binding_and_versions_are_returned_without_writes(self):
        before, total = self.contents(), self.store._db.total_changes
        result = self.resolve()
        self.assertEqual(result, {"status": "bound", "reason": None, "target": {
            "binding": {"case_id": "C1", "object_id": "O1", "principal_id": "U1", "request_id": "REQ1",
                        "request_revision": "v1", "consent_revision": "v1", "generation": "G1",
                        "fingerprint": make_binding().fingerprint, "supersedes_generation": None},
            "profile_version": "v1", "process_version": "v1", "policy_version": "v1",
            "checkpoint_hash": fingerprint(self.checkpoint.model_dump(mode="json")), "checked_at": NOW.isoformat()}})
        self.assertEqual(self.contents(), before)
        self.assertEqual(self.store._db.total_changes, total)
        self.assertFalse(self.store._db.in_transaction)

    def test_denied_scope_does_not_disclose_binding(self):
        self.assertEqual(self.resolve(self.resolver(authorized=False)), {"status": "rejected", "reason": "scope_denied"})

    def test_absent_mapping_does_not_disclose_binding(self):
        self.assertEqual(self.resolve(self.resolver(registrations=())), {"status": "unmapped", "reason": "mapping_absent"})

    def test_different_source_snapshot_is_rejected(self):
        self.assertEqual(self.resolver()(self.source_case_id, "b" * 64), {"status": "rejected", "reason": "source_mismatch"})

    def test_changed_checkpoint_is_rejected(self):
        resolver = self.resolver()
        self.store.save_checkpoint(make_checkpoint(phase="next"))
        self.assertEqual(self.resolve(resolver), {"status": "rejected", "reason": "binding_stale"})

    def test_superseding_generation_is_rejected(self):
        resolver = self.resolver()
        request = make_request(request_revision="v2")
        binding = make_binding(request, generation="G2", supersedes_generation="G1")
        self.store.admit(binding, request, make_checkpoint(binding))
        self.assertEqual(self.resolve(resolver), {"status": "rejected", "reason": "binding_stale"})

    def test_stopped_case_is_rejected_even_with_current_registered_hash(self):
        self.store.set_stop("C1", "G1")
        self.checkpoint = self.store.checkpoint("C1")
        self.assertEqual(self.resolve(), {"status": "rejected", "reason": "case_stopped"})

    def test_expired_checkpoint_is_rejected(self):
        self.assertEqual(self.resolve(self.resolver(clock=lambda: DEADLINE)), {"status": "rejected", "reason": "checkpoint_expired"})

    def test_versions_and_all_binding_fields_must_match(self):
        for changes in ({"profile_version": "v2"}, {"process_version": "v2"}, {"policy_version": "v2"},
                        {"binding": make_binding(fingerprint="b" * 64)},
                        {"binding": make_binding(supersedes_generation="earlier")},
                        *({"binding": make_binding(**{name: "other"})} for name in
                          ("case_id", "object_id", "principal_id", "request_id", "request_revision", "consent_revision", "generation"))):
            with self.subTest(changes=changes):
                result = self.resolve(self.resolver(registrations=(self.target(**changes),)))
                self.assertEqual(result["status"], "rejected")
                self.assertNotIn("target", result)

    def test_wrong_auth_caller_and_proof_are_denied(self):
        for auth in (make_auth(caller_id="other"), make_auth(proof_reference="other")):
            self.assertEqual(self.resolve(self.resolver(auth=auth)), {"status": "rejected", "reason": "scope_denied"})

    def test_authorization_requires_literal_true(self):
        for value in (1, "yes", None, {}):
            self.assertEqual(self.resolve(self.resolver(authorize=lambda target, auth: value)),
                             {"status": "rejected", "reason": "scope_denied"})

    def test_callback_exception_is_sanitized(self):
        def denied(target, auth):
            raise RuntimeError("SECRET proof contents")
        self.assertEqual(self.resolve(self.resolver(authorize=denied)), {"status": "rejected", "reason": "scope_denied"})
        self.assertFalse(self.store._db.in_transaction)

    def test_naive_clock_is_rejected_and_connection_restored(self):
        self.assertEqual(self.resolve(self.resolver(clock=lambda: NOW.replace(tzinfo=None))),
                         {"status": "rejected", "reason": "clock_invalid"})
        self.assertFalse(self.store._db.in_transaction)
        self.assertEqual(self.store._db.execute("PRAGMA query_only").fetchone()[0], 0)

    def test_foreign_thread_is_rejected_without_using_sqlite_connection(self):
        resolver = self.resolver()
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(resolver, self.source_case_id, self.snapshot_hash).result()
        self.assertEqual(result, {"status": "rejected", "reason": "runtime_unavailable"})

    def test_existing_transaction_remains_owned_by_caller(self):
        resolver = self.resolver()
        self.store._db.execute("BEGIN")
        try:
            self.assertEqual(self.resolve(resolver), {"status": "rejected", "reason": "runtime_unavailable"})
            self.assertTrue(self.store._db.in_transaction)
        finally:
            self.store._db.execute("ROLLBACK")

    def test_preexisting_read_only_connection_state_is_preserved(self):
        self.store._db.execute("PRAGMA query_only=ON")
        try:
            self.assertEqual(self.resolve()["status"], "bound")
            self.assertEqual(self.store._db.execute("PRAGMA query_only").fetchone()[0], 1)
        finally:
            self.store._db.execute("PRAGMA query_only=OFF")

    def test_registration_is_detached_from_host_objects(self):
        target = self.target()
        resolver = self.resolver(registrations=[target])
        object.__setattr__(target, "profile_version", "changed")
        object.__setattr__(target.binding, "principal_id", "changed")
        self.assertEqual(self.resolve(resolver)["target"]["binding"]["principal_id"], "U1")

    def test_invalid_copied_registration_and_duplicate_are_rejected(self):
        target = self.target()
        object.__setattr__(target, "checkpoint_hash", "invalid")
        with self.assertRaises(ValueError):
            self.resolver(registrations=[target])
        with self.assertRaises(ValueError):
            self.resolver(registrations=[self.target(), self.target()])

    def test_malformed_source_identity_is_rejected(self):
        resolver = self.resolver()
        for source, snapshot in (("../case", self.snapshot_hash), (self.source_case_id, "bad"), (None, self.snapshot_hash)):
            self.assertEqual(resolver(source, snapshot), {"status": "rejected", "reason": "source_invalid"})

    def test_active_execution_scope_is_rejected_without_leaving_it(self):
        from proofkey.execution import ExecutionContext
        from test_execution_context_storage import DeterministicClock
        clock = DeterministicClock()
        execution = ExecutionContext.capture(NOW + timedelta(seconds=1), clock)
        resolver = self.resolver()
        with self.store.execution_scope(execution, clock):
            self.assertEqual(self.resolve(resolver), {"status": "rejected", "reason": "runtime_unavailable"})
            self.assertIsNotNone(self.store._execution)
        self.assertIsNone(self.store._execution)

    def test_corrupted_original_is_rejected_without_leaking_stored_text(self):
        resolver = self.resolver()
        self.store._db.execute("UPDATE original_requests SET request_json=?", ('{"secret":"not-a-request"}',))
        before = self.contents()
        self.assertEqual(self.resolve(resolver), {"status": "rejected", "reason": "runtime_unavailable"})
        self.assertEqual(before, self.contents())
        self.assertFalse(self.store._db.in_transaction)

    def test_authorization_callback_cannot_write_runtime_state(self):
        before = self.contents()
        def write_attempt(target, auth):
            self.store.set_stop("C1", "G1")
            return True
        self.assertEqual(self.resolve(self.resolver(authorize=write_attempt)),
                         {"status": "rejected", "reason": "scope_denied"})
        self.assertEqual(before, self.contents())
        self.assertFalse(self.store._db.in_transaction)

    def test_one_read_snapshot_survives_concurrent_committed_stop(self):
        resolver = self.resolver()
        original_request = self.store.original_request
        def stop_elsewhere():
            writer = CaseStore(self.path)
            try:
                writer.set_stop("C1", "G1")
            finally:
                writer.close()
        def read_after_concurrent_stop(case_id, generation):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(stop_elsewhere).result(timeout=10)
            return original_request(case_id, generation)
        # The wrapper schedules a real independent writer, then delegates to
        # the real validated getter. No stored values or query outputs are mocked.
        with patch.object(self.store, "original_request", read_after_concurrent_stop):
            observed = self.resolve(resolver)
        self.assertEqual(observed["status"], "bound")
        self.assertEqual(observed["target"]["checkpoint_hash"], fingerprint(self.checkpoint.model_dump(mode="json")))
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.assertFalse(self.store._db.in_transaction)

    def test_configuration_rejects_unbounded_invalid_and_caller_supplied_mapping(self):
        for fields in ({"source_case_id": "../source"}, {"profile_version": "x" * 257},
                       {"allowed_caller_ids": ()}, {"allowed_caller_ids": ("U1", "U1")},
                       {"binding": make_binding(object_id="x" * 257)}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.target(**fields)
        with self.assertRaises(ValueError):
            self.resolver(registrations=[self.target().model_dump()])

    def test_closed_store_does_not_reopen_or_disclose_target(self):
        resolver = self.resolver()
        self.store.close()
        self.assertEqual(self.resolve(resolver), {"status": "rejected", "reason": "runtime_unavailable"})

    def test_bound_result_mutation_does_not_change_next_association(self):
        resolver = self.resolver()
        result = self.resolve(resolver)
        result["target"]["binding"]["principal_id"] = "changed"
        self.assertEqual(self.resolve(resolver)["target"]["binding"]["principal_id"], "U1")

    def test_protected_roots_exposes_existing_main_database_parent_without_writes(self):
        resolver = self.resolver()
        self.assertTrue(hasattr(type(resolver), "shadow_protected_roots"), "Protected runtime roots API is unavailable")
        before, total = self.contents(), self.store._db.total_changes
        self.assertEqual(resolver.shadow_protected_roots, (self.path.parent.resolve(),))
        self.assertEqual(self.contents(), before)
        self.assertEqual(self.store._db.total_changes, total)
        self.assertFalse(self.store._db.in_transaction)
        with self.assertRaises(AttributeError):
            resolver.shadow_protected_roots = ()

    def test_protected_roots_fails_closed_for_closed_or_missing_database(self):
        resolver = self.resolver()
        self.assertTrue(hasattr(type(resolver), "shadow_protected_roots"), "Protected runtime roots API is unavailable")
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "^runtime_unavailable$"):
            resolver.shadow_protected_roots
        self.store.close()
        with self.assertRaisesRegex(ValueError, "^runtime_unavailable$"):
            resolver.shadow_protected_roots


if __name__ == "__main__":
    unittest.main()
