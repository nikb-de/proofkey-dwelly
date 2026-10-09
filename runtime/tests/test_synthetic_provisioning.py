"""Finite input and exclusive private preparation regression tests."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from proofkey.clock import SyntheticReplayClock, SystemClock
from proofkey.contracts import CanonicalRequest
from proofkey.synthetic_provisioning import (
    SyntheticCaseReleaseSpecV1, SyntheticPreparationFailureV1,
    _allocate_private, _stage_private, _validate_input,
)
from support_synthetic_provisioning import case_data, cj, context


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        # macOS /var is a symlink; the actual temporary parent is deliberate.
        self.parent = Path(self.temporary.name).resolve()
        self.parent.chmod(0o700)
        self.clock = SyntheticReplayClock()

    def spec(self, request=None, fixture=None, raw=None):
        original, source = case_data()
        return SyntheticCaseReleaseSpecV1("J06-H", "J06-L", "J06-R",
            request if request is not None else original,
            raw if raw is not None else cj(source if fixture is None else fixture))

    def invalid(self, *, request=None, fixture=None, raw=None):
        before = tuple(self.parent.iterdir())
        with self.assertRaises(SyntheticPreparationFailureV1) as caught:
            _validate_input(self.spec(request, fixture, raw), self.clock, context(self.clock))
        self.assertEqual(caught.exception.code, "invalid_input")
        self.assertEqual(str(caught.exception), "invalid_input")
        self.assertIsNone(caught.exception.retained_root)
        self.assertEqual(tuple(self.parent.iterdir()), before)

    def test_both_cases_keep_exact_source_and_independent_business_hash(self):
        for kind in ("reschedule_window", "goods_refusal"):
            request, fixture = case_data(kind)
            raw = b" \n" + cj(fixture) + b"\n"
            result = _validate_input(self.spec(request, raw=raw), self.clock, context(self.clock))
            self.assertEqual(result.fixture_bytes, raw)
            self.assertEqual(result.business_fingerprint,
                             fixture["facts"]["customer.request_fingerprint"]["value"])
            self.assertEqual(raw.decode(), json.loads(dict(result.declarations)["source"])["documents"][0]["text"])
            self.assertTrue(result.implementations)
            self.assertEqual(tuple(self.parent.iterdir()), ())

    def test_spec_detaches_nested_request_containers(self):
        request, fixture = case_data()
        spec = self.spec(request, fixture)
        dict.__setitem__(request.arguments["inventory"], "j06-widget", 900)
        self.assertEqual(spec.request.arguments["inventory"]["j06-widget"], 2)
        result = _validate_input(spec, self.clock, context(self.clock))
        self.assertEqual(result.request.arguments["inventory"]["j06-widget"], 2)

    def test_validation_rechecks_mutated_spec_request(self):
        spec = self.spec()
        dict.__setitem__(spec.request.arguments["inventory"], "j06-widget", 900)
        with self.assertRaises(SyntheticPreparationFailureV1):
            _validate_input(spec, self.clock, context(self.clock))

    def test_exact_spec_request_clock_and_identifier_types(self):
        request, fixture = case_data()
        class RequestSubclass(CanonicalRequest):
            pass
        class SpecSubclass(SyntheticCaseReleaseSpecV1):
            pass
        class ClockSubclass(SyntheticReplayClock):
            pass
        for bad in (request.model_dump(), RequestSubclass.model_validate(request.model_dump())):
            with self.subTest(request=type(bad)), self.assertRaises(SyntheticPreparationFailureV1):
                self.spec(bad, fixture)
        with self.assertRaises(SyntheticPreparationFailureV1):
            SpecSubclass("J06-H", "J06-L", "J06-R", request, cj(fixture))
        for bad in ({}, object()):
            with self.assertRaises(SyntheticPreparationFailureV1):
                _validate_input(bad, self.clock, context(self.clock))
        for bad in (SystemClock(), ClockSubclass()):
            with self.assertRaises(SyntheticPreparationFailureV1):
                _validate_input(self.spec(), bad, context(bad))
        for bad in ("", " ", "x" * 257, 1):
            with self.subTest(identifier=bad), self.assertRaises(SyntheticPreparationFailureV1):
                SyntheticCaseReleaseSpecV1(bad, "J06-L", "J06-R", request, cj(fixture))

    def test_rejects_unsupported_or_unstructured_request(self):
        request, _ = case_data()
        for update in ({"kind": "transfer"}, {"narrative": "hello"}, {"narrative": ""},
                       {"evidence_ids": ["E1"]}, {"arguments": {"x": "x" * 65536}}):
            with self.subTest(update=next(iter(update))):
                self.invalid(request=request.model_copy(update=update))

    def test_invalid_fixture_bytes_and_encoding(self):
        for raw in (b"", b" " * 1048577, bytearray(b"{}"), "{}", b"\xff", b"{} trailing"):
            with self.subTest(raw_type=type(raw), size=len(raw)):
                self.invalid(raw=raw)

    def test_duplicate_keys_at_every_envelope_level(self):
        _, fixture = case_data()
        raw = cj(fixture)
        for key in (b'"version":', b'"scopes":', b'"readers":', b'"J06-USER-WINDOW":',
                    b'"case.binding":', b'"revision":', b'"request_id":', b'"j06-widget":'):
            with self.subTest(key=key):
                self.invalid(raw=raw.replace(key, key + b'null,' + key, 1))

    def test_nonfinite_numbers_in_nested_values(self):
        _, fixture = case_data()
        raw = cj(fixture)
        for number in (b"NaN", b"Infinity", b"-Infinity", b"1e9999"):
            with self.subTest(number=number):
                self.invalid(raw=raw.replace(b'"goods.quantity":{"case_id":', b'"goods.quantity":{"bad":' + number + b',"case_id":', 1))
                self.invalid(raw=raw.replace(b'"value":3', b'"value":' + number, 1))

    def test_depth_boundary_and_string_delimiters(self):
        request, fixture = case_data()
        for total_depth in (64, 65):
            # Root/facts/fact envelope consume three container levels.
            value = 'braces {} [] and quote " and backslash \\'
            for _ in range(total_depth - 3):
                value = [value]
            fixture["facts"]["goods.quantity"]["value"] = value
            if total_depth == 64:
                _validate_input(self.spec(request, fixture), self.clock, context(self.clock))
            else:
                self.invalid(fixture=fixture)

    def test_exact_envelope_fields(self):
        for level in ("root", "scope", "fact"):
            for alteration in ("missing", "extra"):
                _, fixture = case_data()
                target = fixture if level == "root" else (fixture["scopes"][0] if level == "scope" else fixture["facts"]["goods.quantity"])
                if alteration == "extra":
                    target["unexpected"] = 1
                else:
                    del target[next(iter(target))]
                with self.subTest(level=level, alteration=alteration):
                    self.invalid(fixture=fixture)

    def test_scope_shape_timestamp_and_version(self):
        for field, value in (("version", "other"), ("as_of", "2026-10-08"),
                             ("as_of", 1), ("scopes", []), ("facts", {})):
            _, fixture = case_data()
            fixture[field] = value
            self.invalid(fixture=fixture)
        _, fixture = case_data()
        fixture["scopes"] *= 2
        self.invalid(fixture=fixture)
        for readers in ({}, {"": "proof"}, {"user": ""}, {"user": 1}, []):
            _, fixture = case_data()
            fixture["scopes"][0]["readers"] = readers
            self.invalid(fixture=fixture)

    def test_matching_ids_and_commitments(self):
        for level, fields in (("scope", ("case_id", "object_id", "principal_id")),
                              ("fact", ("case_id", "object_id")),
                              ("binding", ("case_id", "object_id", "principal_id", "request_id"))):
            for field in fields:
                _, fixture = case_data()
                target = fixture["scopes"][0] if level == "scope" else fixture["facts"]["case.binding"]
                if level == "binding":
                    target = target["value"]
                target[field] = "WRONG"
                self.invalid(fixture=fixture)
        for key in ("case.binding", "customer.request_fingerprint"):
            _, fixture = case_data()
            del fixture["facts"][key]
            self.invalid(fixture=fixture)
        _, fixture = case_data()
        fixture["facts"]["customer.request_fingerprint"]["value"] = "0" * 64
        self.invalid(fixture=fixture)
        _, fixture = case_data()
        fixture["facts"]["case.binding"]["value"]["extra"] = "x"
        self.invalid(fixture=fixture)

    def test_qualified_fact_names_and_nonempty_metadata(self):
        for key in ("bad", ".bad", "bad.", "bad..name", ""):
            _, fixture = case_data()
            fixture["facts"][key] = fixture["facts"].pop("goods.quantity")
            self.invalid(fixture=fixture)
        for field in ("revision", "evidence_ref"):
            _, fixture = case_data()
            fixture["facts"]["goods.quantity"][field] = ""
            self.invalid(fixture=fixture)

    def test_encoded_source_limit_fails_before_allocation(self):
        _, fixture = case_data()
        fixture["facts"]["goods.quantity"]["value"] = '\\"' * 150000
        raw = cj(fixture)
        self.assertLess(len(raw), 1048576)
        self.invalid(raw=raw)

    def test_expired_preparation_context(self):
        expired = context(self.clock, -1)
        with self.assertRaises(SyntheticPreparationFailureV1) as caught:
            _validate_input(self.spec(), self.clock, expired)
        self.assertEqual(caught.exception.code, "timeout")
        self.assertEqual(tuple(self.parent.iterdir()), ())

    def test_allocation_is_private_opaque_and_empty(self):
        with _allocate_private(self.parent, self.clock, context(self.clock)) as allocation:
            self.assertEqual(allocation.root.parent, self.parent)
            self.assertRegex(allocation.root.name, r"^case-[a-f0-9]{32}$")
            self.assertEqual({p.name for p in allocation.root.iterdir()},
                             {"data", "resources", "control", "inventories", "outputs"})
            for path in (allocation.root, allocation.data, allocation.resources,
                         allocation.control, allocation.inventories, allocation.outputs):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
                self.assertEqual(path.stat().st_uid, os.geteuid())
            root = allocation.root
        self.assertTrue(root.is_dir())

    def test_rejects_unsafe_parent_targets_without_children(self):
        import proofkey
        unsafe = (Path("relative"), self.parent / ".." / self.parent.name,
                  Path("/"), Path.home(), Path.cwd(), Path(proofkey.__file__).parent)
        for parent in unsafe:
            with self.subTest(parent=parent), self.assertRaises(SyntheticPreparationFailureV1) as caught:
                with _allocate_private(parent, self.clock, context(self.clock)):
                    self.fail("unsafe target accepted")
            self.assertEqual(caught.exception.code, "invalid_target")
            self.assertIsNone(caught.exception.retained_root)
        self.assertEqual(tuple(self.parent.iterdir()), ())

    def test_symlink_ancestor_preserves_outside_sentinel(self):
        real = self.parent / "real"
        real.mkdir(mode=0o700)
        sentinel = real / "sentinel"
        sentinel.write_bytes(b"unchanged")
        alias = self.parent / "alias"
        alias.symlink_to(real, target_is_directory=True)
        with self.assertRaises(SyntheticPreparationFailureV1) as caught:
            with _allocate_private(alias, self.clock, context(self.clock)):
                self.fail("alias accepted")
        self.assertEqual(caught.exception.code, "invalid_target")
        self.assertEqual(sentinel.read_bytes(), b"unchanged")
        self.assertEqual({p.name for p in real.iterdir()}, {"sentinel"})

    def test_nonprivate_mode_and_wrong_owner(self):
        self.parent.chmod(0o755)
        with self.assertRaises(SyntheticPreparationFailureV1):
            with _allocate_private(self.parent, self.clock, context(self.clock)):
                self.fail("public parent accepted")
        self.parent.chmod(0o700)
        with patch("proofkey.synthetic_provisioning.os.geteuid", return_value=os.geteuid() + 1):
            with self.assertRaises(SyntheticPreparationFailureV1):
                with _allocate_private(self.parent, self.clock, context(self.clock)):
                    self.fail("foreign parent accepted")
        self.assertEqual(tuple(self.parent.iterdir()), ())

    def test_exclusive_uuid_collision_never_adopts_child(self):
        identifier = UUID(int=1)
        child = self.parent / ("case-" + identifier.hex)
        child.mkdir(mode=0o700)
        (child / "sentinel").write_bytes(b"preserved")
        with patch("proofkey.synthetic_provisioning.uuid4", return_value=identifier):
            with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                with _allocate_private(self.parent, self.clock, context(self.clock)):
                    self.fail("collision adopted")
        self.assertIsNone(caught.exception.retained_root)
        self.assertEqual(tuple(child.iterdir()), (child / "sentinel",))
        self.assertEqual((child / "sentinel").read_bytes(), b"preserved")

    def test_staging_is_exclusive_private_and_read_back(self):
        with _allocate_private(self.parent, self.clock, context(self.clock)) as allocation:
            path = _stage_private(allocation, "data", "fixture.json", b"exact bytes", self.clock, context(self.clock))
            self.assertEqual(path.read_bytes(), b"exact bytes")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(path.stat().st_nlink, 1)
            with self.assertRaises(SyntheticPreparationFailureV1):
                _stage_private(allocation, "data", "fixture.json", b"overwrite", self.clock, context(self.clock))
            self.assertEqual(path.read_bytes(), b"exact bytes")

    def test_parent_replacement_at_io_barrier_retains_partial_child(self):
        import proofkey.synthetic_provisioning as provisioning
        real_mkdir = os.mkdir
        renamed = self.parent.with_name(self.parent.name + "-old")
        self.addCleanup(lambda: __import__("shutil").rmtree(renamed, ignore_errors=True))
        def replace(name, *args, **kwargs):
            result = real_mkdir(name, *args, **kwargs)
            if str(name).startswith("case-"):
                self.parent.rename(renamed)
                self.parent.mkdir(mode=0o700)
                (self.parent / "sentinel").write_bytes(b"outside")
            return result
        with patch.object(provisioning.os, "mkdir", side_effect=replace):
            with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                with _allocate_private(self.parent, self.clock, context(self.clock)):
                    self.fail("replaced parent accepted")
        self.assertEqual(caught.exception.code, "identity_changed")
        self.assertIsNotNone(caught.exception.retained_root)
        self.assertEqual((self.parent / "sentinel").read_bytes(), b"outside")
        self.assertEqual(len(tuple(renamed.iterdir())), 1)

    @contextmanager
    def tracked_descriptors(self):
        original_open, original_close = os.open, os.close
        active = set()
        def opened(*args, **kwargs):
            descriptor = original_open(*args, **kwargs)
            active.add(descriptor)
            return descriptor
        def closed(descriptor):
            original_close(descriptor)
            active.discard(descriptor)
        with patch("proofkey.synthetic_provisioning.os.open", side_effect=opened), patch("proofkey.synthetic_provisioning.os.close", side_effect=closed):
            yield active
        self.assertEqual(active, set())

    def test_descriptor_closure_success_io_failure_timeout_and_baseexception(self):
        for failure in (None, OSError("secret path"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure)), self.tracked_descriptors():
                try:
                    with _allocate_private(self.parent, self.clock, context(self.clock)) as allocation:
                        if failure is not None:
                            with patch("proofkey.synthetic_provisioning._write", side_effect=failure):
                                _stage_private(allocation, "data", "fixture.json", b"bytes", self.clock, context(self.clock))
                except SyntheticPreparationFailureV1 as caught:
                    self.assertIsInstance(failure, OSError)
                    self.assertEqual(str(caught), "io_failure")
                    self.assertTrue(caught.retained_root.is_dir())
                except KeyboardInterrupt:
                    self.assertIsInstance(failure, KeyboardInterrupt)
        with self.tracked_descriptors():
            with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                with _allocate_private(self.parent, self.clock, context(self.clock)) as allocation:
                    _stage_private(allocation, "data", "fixture.json", b"bytes", self.clock, context(self.clock, -1))
            self.assertEqual(caught.exception.code, "timeout")
            self.assertTrue(caught.exception.retained_root.is_dir())

    def test_descriptor_closure_when_ancestry_open_is_interrupted(self):
        real_fstat = os.fstat
        calls = 0
        def interrupted(fd):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise KeyboardInterrupt()
            return real_fstat(fd)
        with self.tracked_descriptors(), patch("proofkey.synthetic_provisioning.os.fstat", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                with _allocate_private(self.parent, self.clock, context(self.clock)):
                    self.fail("interruption ignored")

    def test_snapshots_do_not_expose_private_contents_in_repr(self):
        spec = self.spec()
        result = _validate_input(spec, self.clock, context(self.clock))
        for value in (spec, result):
            for secret in ("j06-synthetic-proof", "j06-widget", "source-declaration", "J06-USER-WINDOW"):
                self.assertNotIn(secret, repr(value))

    def test_staging_detects_mode_change_during_readback(self):
        import proofkey.synthetic_provisioning as provisioning
        original_read = provisioning._read
        def changed(root, name, limit):
            data = original_read(root, name, limit)
            os.chmod(name, 0o644, dir_fd=root)
            return data
        with _allocate_private(self.parent, self.clock, context(self.clock)) as allocation:
            with patch.object(provisioning, "_read", side_effect=changed):
                with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                    _stage_private(allocation, "data", "fixture.json", b"bytes", self.clock, context(self.clock))
            self.assertEqual(caught.exception.code, "identity_changed")

    def test_staging_detects_inode_change_during_readback(self):
        import proofkey.synthetic_provisioning as provisioning
        original_read = provisioning._read
        def changed(root, name, limit):
            data = original_read(root, name, limit)
            os.rename(name, "original.json", src_dir_fd=root, dst_dir_fd=root)
            provisioning._write(root, name, data)
            return data
        with _allocate_private(self.parent, self.clock, context(self.clock)) as allocation:
            with patch.object(provisioning, "_read", side_effect=changed):
                with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                    _stage_private(allocation, "data", "fixture.json", b"bytes", self.clock, context(self.clock))
            self.assertEqual(caught.exception.code, "identity_changed")

    def test_installed_snapshot_rejects_symlink_ancestor(self):
        from proofkey.synthetic_provisioning import _installed_bytes
        real = self.parent / "real"
        real.mkdir(mode=0o700)
        (real / "module.py").write_bytes(b"module")
        alias = self.parent / "alias"
        alias.symlink_to(real, target_is_directory=True)
        with self.assertRaises((OSError, ValueError)):
            _installed_bytes(alias / "module.py")

    def test_packaged_profile_keeps_existing_byte_pin(self):
        import proofkey.synthetic_provisioning as provisioning
        original_read = provisioning._installed_bytes
        def changed(path):
            raw = original_read(path)
            return raw + b"\n" if path.name == "flat-v1.3.json" else raw
        with patch.object(provisioning, "_installed_bytes", side_effect=changed):
            with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                _validate_input(self.spec(), self.clock, context(self.clock))
        self.assertEqual(caught.exception.code, "invalid_input")
        self.assertEqual(tuple(self.parent.iterdir()), ())

    def test_ordinary_write_failure_exposes_only_bounded_code(self):
        with _allocate_private(self.parent, self.clock, context(self.clock)) as allocation:
            with patch("proofkey.synthetic_provisioning._write", side_effect=RuntimeError("private detail")):
                with self.assertRaises(SyntheticPreparationFailureV1) as caught:
                    _stage_private(allocation, "data", "fixture.json", b"bytes", self.clock, context(self.clock))
            self.assertEqual(str(caught.exception), "io_failure")
            self.assertNotIn("private detail", repr(caught.exception))


if __name__ == "__main__":
    unittest.main()
