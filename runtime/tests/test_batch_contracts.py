"""Additive bookkeeping rejects invented joins/windows, not business permission."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import subprocess
import sys
import unittest

from proofkey.contracts import ExportReceipt
from proofkey.execution import ExecutionContext
from proofkey.host_contracts import (BatchPositionInventoryV1, ConsumedExportV1, ExecutionWindowV1,
                                    InterfaceLimitsV1, PublicationWindowV1)


START = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)


def window(seconds=200.0, reserve=2.0):
    context = ExecutionContext(START + timedelta(seconds=seconds), START, -100.0, -100.0 + seconds)
    return PublicationWindowV1(execution=ExecutionWindowV1.from_context(context),
        deadline=context.deadline + timedelta(seconds=reserve), reserve_seconds=reserve,
        monotonic_deadline=context.monotonic_deadline + reserve)


class BatchContractTests(unittest.TestCase):
    def test_positions_and_manifests_cannot_invent_results_ids_or_final_self_reference(self):
        from proofkey.host_contracts import (BatchInputV1, BatchManifestV1, BatchPositionReceiptV1,
                                            CommandReceiptV1, RunReferenceV1)
        inventory = BatchPositionInventoryV1(ordinal=0, supplied_id_shape="string", supplied_case_id="C1")
        position = BatchPositionReceiptV1(inventory=inventory)
        for update in ({"result_hash": "a" * 64}, {"admission_status": "joined"},
                       {"execution_outcome": "result"}, {"export_outcome": "written"}):
            with self.assertRaises(ValueError):
                position.model_copy(update=update)
        summary = BatchInputV1(input_hash="b" * 64, input_bytes=2, position_count=1,
                               encoding="canonical_json_array_v1")
        manifest = BatchManifestV1(run_id="a" * 32, input=summary, release_id="registered",
            mode="synthetic_replay", clock_mode="synthetic_replay", window=window(),
            inventories=(inventory,), positions=(position,), as_of=START)
        for update in ({"positions": ()}, {"pending_command_ids": ("c" * 32,)},
                       {"unresolved_admission_ordinals": (0,)},
                       {"references": (RunReferenceV1(name="FINAL-MANIFEST.json", file_hash="d" * 64),)}):
            with self.assertRaises(ValueError):
                manifest.model_copy(update=update)
        command = CommandReceiptV1(command_id="c" * 32, command_tag="run", release_id="registered",
            mode="synthetic_replay", clock_mode="synthetic_replay", outcome="denied",
            inventory_status="not_admitted", failure="scope_denied")
        joined = position.model_copy(update={"command": command, "admission_status": "joined",
                                             "execution_outcome": "denied"})
        self.assertEqual(joined.command.command_id, "c" * 32)
        with self.assertRaises(ValueError):
            RunReferenceV1(name="../../C1.json", file_hash="a" * 64)

    def test_invalid_document_receipt_cannot_claim_n_or_committed_completion(self):
        from proofkey.host_contracts import BatchRunReceiptV1
        base = dict(run_id="a" * 32, input_outcome="invalid_document", input=None, position_count=None,
            positions=(), release_id="registered", mode="synthetic_replay", clock_mode="synthetic_replay",
            window=window(), outcome="invalid_document", started_at=START, finished_at=START,
            elapsed_seconds=0.0, publication_seconds=0.0, overrun_seconds=0.0)
        actual = BatchRunReceiptV1(**base)
        self.assertEqual(actual.publication_status, "not_started")
        for update in ({"position_count": 0}, {"outcome": "completed"}, {"publication_status": "committed"},
                       {"command_elapsed_basis": "completion_recorded"}):
            with self.assertRaises(ValueError):
                actual.model_copy(update=update)

    def test_publication_window_cannot_extend_or_recapture_original_cutoff(self):
        actual = window()
        self.assertEqual(actual.execution.captured_monotonic, -100.0)
        self.assertEqual(actual.execution.monotonic_deadline, 100.0)
        for update in ({"deadline": actual.deadline + timedelta(seconds=1)},
                       {"monotonic_deadline": 103.0}, {"reserve_seconds": -1.0},
                       {"reserve_seconds": 0.0000001}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                actual.model_copy(update=update)

    def test_original_id_shape_never_invents_or_normalizes_supplied_string(self):
        for value in ("", "../C1", "C1", "é", "e\u0301"):
            row = BatchPositionInventoryV1(ordinal=0, supplied_id_shape="string", supplied_case_id=value)
            self.assertEqual(row.supplied_case_id, value)
        for shape in ("missing", "non_string", "non_object"):
            with self.assertRaises(ValueError):
                BatchPositionInventoryV1(ordinal=0, supplied_id_shape=shape, supplied_case_id="C1")
        with self.assertRaises(ValueError):
            BatchPositionInventoryV1(ordinal=0, supplied_id_shape="string", supplied_case_id=None)

    def test_consumed_export_requires_actual_fixed_order_hash_and_no_failed_success(self):
        files = (("ANSWER.md", "a" * 64), ("REASONING.md", "b" * 64))
        # Hand-derived canonical mapping hash, independent of the consumer's validator.
        digest = sha256(('{' + '"ANSWER.md":"' + 'a' * 64 + '","REASONING.md":"' + 'b' * 64 + '"}').encode()).hexdigest()
        receipt = ExportReceipt(supplied_case_id="C1", output_name="C1", output_hash=digest,
                                status="written", as_of=START)
        actual = ConsumedExportV1(actual_receipt=receipt, actual_file_hashes=files)
        self.assertEqual(actual.actual_file_hashes, files)
        for hashes in ((), tuple(reversed(files)), (("ANSWER.md", "c" * 64), files[1])):
            with self.assertRaises(ValueError):
                ConsumedExportV1(actual_receipt=receipt, actual_file_hashes=hashes)
        with self.assertRaises(ValueError):
            ConsumedExportV1(actual_receipt=receipt.model_copy(update={"failure": "export_io_error"}),
                             actual_file_hashes=files)
        failed = ExportReceipt(supplied_case_id="C1", status="failed", failure="output_conflict", as_of=START)
        self.assertEqual(ConsumedExportV1(actual_receipt=failed, actual_file_hashes=()).actual_file_hashes, ())
        with self.assertRaises(ValueError):
            ConsumedExportV1(actual_receipt=failed, actual_file_hashes=files)

    def test_limits_are_exact_positive_integers_not_body_coercion(self):
        self.assertEqual(InterfaceLimitsV1().max_positions, 256)
        for update in ({"max_positions": True}, {"max_depth": 0}, {"max_input_bytes": 1.0},
                       {"max_run_bytes": -1}, {"permission": True}):
            with self.assertRaises(ValueError):
                InterfaceLimitsV1(**update)

    def test_plain_package_import_does_not_construct_or_import_runtime(self):
        code = "import proofkey,sys; assert not any(x.startswith(('proofkey.adapters','proofkey.providers','proofkey.host','proofkey.batch','fastapi')) for x in sys.modules)"
        completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_finite_lazy_library_exports_do_not_enable_auth_or_optional_api(self):
        code = '''
import proofkey,sys
assert set(('run_command','run_batch','read_run_inventory','RunPublisher','InterfaceLimitsV1','BatchRunReceiptV1')) <= set(proofkey.__all__)
assert proofkey.InterfaceLimitsV1().max_positions == 256
assert 'proofkey.host' not in sys.modules and 'proofkey.adapters.world' not in sys.modules
try: proofkey.enable_live
except AttributeError: pass
else: raise AssertionError('unknown activation export')
assert callable(proofkey.run_batch)
assert 'proofkey.providers.clients' not in sys.modules and 'fastapi' not in sys.modules
'''
        completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_json_readback_tuple_bridge_does_not_convert_business_arrays_or_python_lists(self):
        from proofkey.host_contracts import BatchInputV1, BatchManifestV1, BatchPositionReceiptV1
        row = BatchPositionInventoryV1(ordinal=0, supplied_id_shape="string", supplied_case_id="C1")
        actual = BatchManifestV1(run_id="a" * 32, input=BatchInputV1(encoding="canonical_json_array_v1",
            input_hash="b" * 64, input_bytes=2, position_count=1), release_id="registered",
            mode="synthetic_replay", clock_mode="synthetic_replay", window=window(), inventories=(row,),
            positions=(BatchPositionReceiptV1(inventory=row),), as_of=START)
        self.assertEqual(BatchManifestV1.model_validate_json(actual.model_dump_json()), actual)
        with self.assertRaises(ValueError):
            actual.model_copy(update={"inventories": [row]})
