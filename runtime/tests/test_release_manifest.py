"""Task-owned synthetic release trees; no current candidate/rights qualification."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from proofkey.identity import fingerprint
from proofkey.release import (ArtifactPinV1, DependencyReleaseV1, ReleasePreparationError, ReleaseRightsError,
                              ReleaseVerificationUnavailable, RootIdentityV1, SourceReleaseContextV1,
                              SyntheticScanExceptionV1, prepare_release, verify_release, verify_release_static)
import proofkey.release as release_module


def digest(data):
    return sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class ReleaseManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source = self.base / "synthetic-source"
        self.source.mkdir()
        self.output = self.base / "new-release"
        self.data = {
            "src/demo.py": b"answer = 42\n",
            "pyproject.toml": b'[project]\nname = "owned-demo"\nversion = "1.0"\ndependencies = ["owned-demo==1.0"]\n',
            "requirements.lock": b"owned-demo==1.0\n",
            "DEPENDENCIES.json": encoded({"dependencies": [{"name": "owned-demo", "version": "1.0",
                "license": "TestFixtureOnly", "notice": "NOTICE"}]}),
            "NOTICE": b"Task-owned synthetic dependency notice; not actual license clearance.\n",
            "RIGHTS.md": b"Task-owned synthetic tree only; no actual source custody or legal approval.\n",
        }
        for relative, data in self.data.items():
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.pins = {path: digest(data) for path, data in self.data.items()}
        self.rights = {path: {"file_hash": self.pins[path], "classification": "synthetic",
            "origin": "task-owned-test-fixture", "license": "TestFixtureOnly",
            "evidence_refs": ["task-owned-synthetic-test"], "notices": ["NOTICE"],
            "include_in_release": True, "public_rights": True} for path in self.data}
        self.groups = {"source": ["src/demo.py"], "profile": [], "process": [], "policy": [],
            "test": [], "rights": ["RIGHTS.md"], "dependency": ["pyproject.toml", "DEPENDENCIES.json"],
            "lock": ["requirements.lock"], "notice": ["NOTICE"]}
        self.dependency = DependencyReleaseV1(pyproject_path="pyproject.toml", lock_path="requirements.lock",
            inventory_path="DEPENDENCIES.json", file_hashes={path: self.pins[path] for path in
                ("pyproject.toml", "requirements.lock", "DEPENDENCIES.json", "NOTICE")},
            notice_paths=["NOTICE"], artifacts={}, verification_mode="static_unverified")
        self.context = self.make_context()

    def make_context(self, **changes):
        rights_hash = digest(encoded(self.rights))
        dependency_hash = digest(encoded(self.dependency.model_dump(mode="json")))
        expected = fingerprint({"kind": "SourceReleaseCandidateV1", "file_hashes": dict(sorted(self.pins.items())),
            "rights_hash": rights_hash, "dependency_hash": dependency_hash, "groups": self.groups})
        data = dict(source_root=RootIdentityV1.capture(self.source),
            output_parent=RootIdentityV1.capture(self.base), file_hashes=self.pins, rights_hash=rights_hash,
            rights_evidence=["task-owned-synthetic-test-not-legal-clearance"], dependency=self.dependency,
            expected_candidate_hash=expected, groups=self.groups, max_files=16, max_file_bytes=4096,
            max_total_bytes=16384, scan_exceptions=[], mode="offline_synthetic",
            unsupported_modes=["native", "live", "reproduction", "rights_certification"],
            captured_at=datetime(2026, 10, 9, tzinfo=timezone.utc))
        data.update(changes)
        return SourceReleaseContextV1(**data)

    def replace_source(self, path, data):
        # Explicit new trusted TEST pin, not repair of a real frozen candidate.
        self.data[path] = data
        (self.source / path).parent.mkdir(parents=True, exist_ok=True)
        (self.source / path).write_bytes(data)
        self.pins[path] = digest(data)
        self.rights[path] = {"file_hash": self.pins[path], "classification": "synthetic",
            "origin": "task-owned-test-fixture", "license": "TestFixtureOnly",
            "evidence_refs": ["task-owned-synthetic-test"], "notices": ["NOTICE"],
            "include_in_release": True, "public_rights": True}
        if path in self.dependency.file_hashes:
            self.dependency = self.dependency.model_copy(update={"file_hashes": {
                **self.dependency.file_hashes, path: self.pins[path]}})
        if not any(path in entries for entries in self.groups.values()):
            self.groups["source"].append(path)
        self.context = self.make_context()

    def test_private_file_without_trusted_context_never_creates_output(self):
        # A caller's include/public flags must never become a trusted context.
        private = self.source / "private-call.wav"
        private.write_bytes(b"Task-owned synthetic private-like recording bytes")
        with self.assertRaises(ReleaseRightsError):
            prepare_release(self.source, {"private-call.wav": {"classification": "private",
                "public_rights": False, "include_in_release": True}}, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(private.read_bytes(), b"Task-owned synthetic private-like recording bytes")

    def test_exact_owned_synthetic_package_has_actual_bytes_and_static_only_receipt(self):
        # Missing copy/hash/mode separation must fail this real filesystem path.
        receipt = prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertEqual(dict(receipt.file_hashes), self.pins)
        self.assertEqual(receipt.candidate_hash, self.context.expected_candidate_hash)
        self.assertEqual(receipt.rights_hash, digest(encoded(self.rights)))
        for relative, data in self.data.items():
            self.assertEqual((self.output / relative).read_bytes(), data)
        static = verify_release_static(receipt, release_root=self.output, context=self.context)
        self.assertEqual(static.kind, "static_source_readback")
        self.assertEqual(static.outcome, "verified")
        self.assertEqual(dict(static.observed_file_hashes), self.pins)
        self.assertEqual(static.mode, "offline_synthetic")
        self.assertIn("reproduction", static.unsupported_modes)
        self.assertFalse(hasattr(static, "commands"))

    def test_preexisting_output_is_unchanged_and_never_reused(self):
        self.output.mkdir()
        marker = self.output / "user-owned.txt"
        marker.write_bytes(b"keep exact user bytes")
        with self.assertRaises(ReleaseRightsError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertEqual(marker.read_bytes(), b"keep exact user bytes")
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_malformed_output_root_is_generic_denial_before_claim(self):
        with self.assertRaises(ReleaseRightsError) as raised:
            prepare_release(self.source, self.rights, None, context=self.context)
        self.assertEqual(str(raised.exception), "Invalid trusted release scope, rights or bytes")
        self.assertFalse(self.output.exists())

    def test_forbidden_rights_classifications_cannot_be_authorized_by_booleans(self):
        for classification in ("private", "restricted", "provider", "org", "raw_archive", "credential", "unknown"):
            with self.subTest(classification=classification):
                self.rights["src/demo.py"]["classification"] = classification
                context = self.make_context()
                with self.assertRaises(ReleaseRightsError):
                    prepare_release(self.source, self.rights, self.output, context=context)
                self.assertFalse(self.output.exists())

    def test_missing_orphan_stale_rights_are_visible_without_copy(self):
        for kind in ("missing", "orphan", "stale"):
            rights = {key: dict(value) for key, value in self.rights.items()}
            if kind == "missing":
                del rights["src/demo.py"]
            elif kind == "orphan":
                rights["not-present.txt"] = dict(rights["src/demo.py"])
            else:
                rights["src/demo.py"]["file_hash"] = "0" * 64
            with self.subTest(kind=kind), self.assertRaises(ReleaseRightsError):
                prepare_release(self.source, rights, self.output, context=self.context)
            self.assertFalse(self.output.exists())

    def test_credential_and_private_like_bytes_fail_even_with_exact_synthetic_pins(self):
        for ordinal, data in enumerate((b'api_key = "synthetic_only_token_000000000000"\n',
                     b"ORGANIZER PRIVATE RECORDING - task-owned negative fixture only\n")):
            self.replace_source("src/demo.py", data)
            output = self.base / ("scan-" + str(ordinal))
            with self.subTest(data_kind=data[:8]):
                with self.assertRaises(ReleaseRightsError) as raised:
                    prepare_release(self.source, self.rights, output, context=self.context)
                self.assertNotIn("synthetic_only_token", str(raised.exception))
                self.assertFalse(output.exists())

    def test_synthetic_scan_exception_is_exact_field_origin_and_full_file_pin_only(self):
        value = "synthetic_only_token_000000000000"
        self.replace_source("fixture.json", encoded({"api_key": value, "safe": "owned synthetic"}))
        exception = SyntheticScanExceptionV1(path="fixture.json", file_hash=self.pins["fixture.json"],
            field=["api_key"], value_hash=digest(encoded(value)), origin="task-owned-test-fixture")
        context = self.make_context(scan_exceptions=[exception])
        receipt = prepare_release(self.source, self.rights, self.output, context=context)
        self.assertEqual((self.output / "fixture.json").read_bytes(), self.data["fixture.json"])
        self.assertEqual(verify_release_static(receipt, release_root=self.output, context=context).outcome, "verified")
        # New trusted test file pin does not update the old narrow exception.
        self.replace_source("fixture.json", encoded({"api_key": value, "extra": "changed"}))
        context = self.make_context(scan_exceptions=[exception])
        with self.assertRaises(ReleaseRightsError):
            prepare_release(self.source, self.rights, self.base / "changed-release", context=context)
        self.assertFalse((self.base / "changed-release").exists())

    def test_dependency_version_join_rejects_hash_valid_but_semantically_changed_lock(self):
        self.replace_source("requirements.lock", b"owned-demo==2.0\n")
        with self.assertRaises(ReleaseRightsError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertFalse(self.output.exists())

    def test_artifact_pinned_mode_without_actual_artifact_inventory_denies(self):
        self.dependency = self.dependency.model_copy(update={"verification_mode": "artifact_pinned"})
        context = self.make_context()
        with self.assertRaises(ReleaseRightsError):
            prepare_release(self.source, self.rights, self.output, context=context)
        self.assertFalse(self.output.exists())

    def test_exact_synthetic_artifact_pin_joins_bytes_without_installer_qualification(self):
        path = "artifacts/owned-demo.whl"
        self.replace_source(path, b"Task-owned hash-join fixture; NOT an installable wheel.\n")
        self.dependency = self.dependency.model_copy(update={"verification_mode": "artifact_pinned",
            "artifacts": {"owned-demo": ArtifactPinV1(path=path, file_hash=self.pins[path])}})
        context = self.make_context()
        receipt = prepare_release(self.source, self.rights, self.output, context=context)
        self.assertEqual((self.output / path).read_bytes(), self.data[path])
        self.assertEqual(receipt.dependency_hash, digest(encoded(self.dependency.model_dump(mode="json"))))
        static = verify_release_static(receipt, release_root=self.output, context=context)
        self.assertIn("reproduction", static.unsupported_modes)
        self.assertFalse(hasattr(static, "commands"))

    def test_exception_wrong_origin_or_value_or_other_credential_denies(self):
        value = "task_owned_synthetic_secret_000000"
        for kind in ("origin", "value", "other"):
            body = {"api_key": value}
            if kind == "other":
                body["password"] = "another_task_owned_synthetic_secret_000000"
            self.replace_source("fixture.json", encoded(body))
            exception = SyntheticScanExceptionV1(path="fixture.json", file_hash=self.pins["fixture.json"],
                field=["api_key"], value_hash="0" * 64 if kind == "value" else digest(encoded(value)),
                origin="wrong-test-origin" if kind == "origin" else "task-owned-test-fixture")
            context = self.make_context(scan_exceptions=[exception])
            output = self.base / ("denied-exception-" + kind)
            with self.subTest(kind=kind):
                with self.assertRaises(ReleaseRightsError):
                    prepare_release(self.source, self.rights, output, context=context)
                self.assertFalse(output.exists())

    def test_static_replaced_trusted_parent_denies_even_when_clone_has_exact_files(self):
        parent = self.base / "registered-parent"
        parent.mkdir()
        output = parent / "new-release"
        context = self.make_context(output_parent=RootIdentityV1.capture(parent))
        receipt = prepare_release(self.source, self.rights, output, context=context)
        retained = self.base / "retained-parent"
        parent.rename(retained)
        parent.mkdir()
        shutil.copytree(retained / "new-release", output)
        manifest = output / "RELEASE-MANIFEST.json"
        value = json.loads(manifest.read_bytes())
        value["release_root"] = RootIdentityV1.capture(output).model_dump(mode="json")
        manifest.write_bytes(encoded(value))
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(receipt, release_root=output, context=context)

    def test_late_parent_substitution_preserving_output_inode_never_returns_prepared_receipt(self):
        # Omitting the final trusted-parent check wrongly certifies the same
        # output inode/bytes after its registered parent has been replaced.
        parent = self.base / "registered-parent"
        parent.mkdir()
        output = parent / "new-release"
        context = self.make_context(output_parent=RootIdentityV1.capture(parent))
        retained = self.base / "retained-parent"
        real = release_module._write
        output_before = []

        def forward(root, path, data):
            result = real(root, path, data)
            if path == "SOURCE-RECEIPT.json":
                output_before.append(RootIdentityV1.capture(output))
                parent.rename(retained)
                parent.mkdir()
                (retained / "new-release").rename(output)
            return result

        with patch.object(release_module, "_write", side_effect=forward):
            with self.assertRaises(ReleasePreparationError) as raised:
                prepare_release(self.source, self.rights, output, context=context)
        self.assertEqual(str(raised.exception), "Release preparation failed; no valid receipt returned")
        self.assertTrue(raised.exception.failure_recorded)
        self.assertEqual(RootIdentityV1.capture(output), output_before[0])
        self.assertNotEqual(RootIdentityV1.capture(parent), context.output_parent)
        self.assertEqual(RootIdentityV1.capture(self.source), context.source_root)
        for path, data in self.data.items():
            self.assertEqual((output / path).read_bytes(), data)
            self.assertEqual((self.source / path).read_bytes(), data)
        self.assertTrue((output / "PREPARATION-PENDING.json").exists())
        failure = json.loads((output / "PREPARATION-FAILED.json").read_bytes())
        self.assertEqual(failure, {"kind": "release_failed", "reason": "preparation_failed", "valid_receipt": False})
        # Published receipt bytes are partial evidence, not a returned success;
        # the already-strict public verifier must still deny this parent.
        from proofkey.contracts import SourceReleaseReceipt
        partial_receipt = SourceReleaseReceipt.model_validate_json((output / "SOURCE-RECEIPT.json").read_bytes())
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(partial_receipt, release_root=output, context=context)

    def test_late_source_root_substitution_never_returns_prepared_receipt(self):
        # The final publication boundary must retain the trusted source-root
        # identity, not only an earlier successful copy of identical bytes.
        retained = self.base / "retained-source"
        real = release_module._write

        def forward(root, path, data):
            result = real(root, path, data)
            if path == "SOURCE-RECEIPT.json":
                self.source.rename(retained)
                shutil.copytree(retained, self.source)
            return result

        with patch.object(release_module, "_write", side_effect=forward):
            with self.assertRaises(ReleasePreparationError) as raised:
                prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertTrue(raised.exception.failure_recorded)
        self.assertNotEqual(RootIdentityV1.capture(self.source), self.context.source_root)
        self.assertTrue((self.output / "PREPARATION-PENDING.json").exists())
        self.assertFalse(json.loads((self.output / "PREPARATION-FAILED.json").read_bytes())["valid_receipt"])
        for path, data in self.data.items():
            self.assertEqual((self.output / path).read_bytes(), data)
            self.assertEqual((retained / path).read_bytes(), data)
            self.assertEqual((self.source / path).read_bytes(), data)

    def test_hash_valid_malformed_dependency_tables_fail_generically_before_output(self):
        malformed = (b'project = "not-a-table"\n',
                     b'[project]\noptional-dependencies = ["not-a-table"]\n')
        for ordinal, data in enumerate(malformed):
            self.replace_source("pyproject.toml", data)
            output = self.base / ("bad-toml-" + str(ordinal))
            with self.subTest(ordinal=ordinal):
                with self.assertRaises(ReleaseRightsError) as raised:
                    prepare_release(self.source, self.rights, output, context=self.context)
                self.assertEqual(str(raised.exception), "Invalid trusted release scope, rights or bytes")
                self.assertFalse(output.exists())

    def test_source_symlink_nonregular_and_hardlink_never_copy(self):
        path = self.source / "src/demo.py"
        original = self.data["src/demo.py"]
        for kind in ("symlink", "directory", "hardlink"):
            path.unlink()
            if kind == "symlink":
                path.symlink_to(self.source / "NOTICE")
            elif kind == "directory":
                path.mkdir()
            else:
                path.hardlink_to(self.source / "NOTICE")
            with self.subTest(kind=kind), self.assertRaises(ReleaseRightsError):
                prepare_release(self.source, self.rights, self.output, context=self.context)
            self.assertFalse(self.output.exists())
            if kind == "directory":
                path.rmdir()
            else:
                path.unlink()
            path.write_bytes(original)

    def test_static_readback_rejects_extra_empty_directory_and_directory_symlink(self):
        receipt = prepare_release(self.source, self.rights, self.output, context=self.context)
        extra = self.output / "unexpected"
        extra.mkdir()
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(receipt, release_root=self.output, context=self.context)
        extra.rmdir()
        extra.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(receipt, release_root=self.output, context=self.context)

    def test_static_manifest_duplicate_keys_and_changed_actual_file_never_verify(self):
        receipt = prepare_release(self.source, self.rights, self.output, context=self.context)
        manifest = self.output / "RELEASE-MANIFEST.json"
        raw = manifest.read_bytes()
        manifest.write_bytes(raw[:-1] + b',"kind":"SourceReleaseManifestV1"}')
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(receipt, release_root=self.output, context=self.context)
        manifest.write_bytes(raw)
        (self.output / "src/demo.py").write_bytes(b"changed after preparation\n")
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(receipt, release_root=self.output, context=self.context)

    def test_actual_reproduction_remains_unavailable_and_has_no_empty_command_receipt(self):
        with self.assertRaises(ReleaseVerificationUnavailable):
            verify_release(None, release_root=self.output, context=self.context, reproduction_plan=None)

    def test_actual_copy_failure_retains_pending_and_safe_failure_without_valid_receipt(self):
        real = release_module._write
        def forward(root, path, data):
            if path == "src/demo.py":
                raise OSError("synthetic-only sensitive-like failure bytes must not leak")
            return real(root, path, data)
        with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError) as raised:
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertTrue(raised.exception.failure_recorded)
        self.assertNotIn("sensitive-like", str(raised.exception))
        self.assertTrue((self.output / "PREPARATION-PENDING.json").exists())
        self.assertTrue((self.output / "PREPARATION-FAILED.json").exists())
        self.assertFalse((self.output / "SOURCE-RECEIPT.json").exists())
        self.assertEqual((self.source / "src/demo.py").read_bytes(), self.data["src/demo.py"])

    def test_failed_marker_write_exposes_durability_limit_and_retains_owned_partial(self):
        real = release_module._write
        def forward(root, path, data):
            if path in {"src/demo.py", "PREPARATION-FAILED.json"}:
                raise OSError("task-owned synthetic I/O fault")
            return real(root, path, data)
        with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError) as raised:
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertFalse(raised.exception.failure_recorded)
        self.assertTrue((self.output / "PREPARATION-PENDING.json").exists())
        self.assertFalse((self.output / "SOURCE-RECEIPT.json").exists())

    def test_source_changes_during_actual_copy_invalidate_pins_not_repair_them(self):
        real = release_module._write
        def forward(root, path, data):
            result = real(root, path, data)
            if path == "src/demo.py":
                (self.source / path).write_bytes(b"changed during copy by deliberate local injection\n")
            return result
        with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertEqual(self.context.file_hashes["src/demo.py"], digest(b"answer = 42\n"))
        self.assertTrue((self.output / "PREPARATION-PENDING.json").exists())
        self.assertFalse((self.output / "SOURCE-RECEIPT.json").exists())

    def test_output_root_replacement_during_actual_copy_cannot_return_receipt_for_wrong_directory(self):
        real = release_module._write
        retained = self.base / "retained-original-output"
        def forward(root, path, data):
            result = real(root, path, data)
            if path == "src/demo.py":
                self.output.rename(retained)
                self.output.mkdir()
            return result
        with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertTrue((retained / "PREPARATION-PENDING.json").exists())
        self.assertFalse((self.output / "SOURCE-RECEIPT.json").exists())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_actual_output_hash_substitution_never_certifies_correct_subset(self):
        real = release_module._write
        def forward(root, path, data):
            result = real(root, path, data)
            if path == "src/demo.py":
                (self.output / path).write_bytes(b"wrong actual copied bytes\n")
            return result
        with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError) as raised:
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertTrue(raised.exception.failure_recorded)
        self.assertFalse((self.output / "SOURCE-RECEIPT.json").exists())

    def test_unapproved_file_injected_during_copy_cannot_receive_prepared_receipt(self):
        real = release_module._write
        def forward(root, path, data):
            result = real(root, path, data)
            if path == "src/demo.py":
                (self.output / "unapproved.txt").write_bytes(b"task-owned injected extra bytes")
            return result
        with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertTrue((self.output / "unapproved.txt").exists())
        self.assertFalse((self.output / "SOURCE-RECEIPT.json").exists())

    def test_late_output_byte_change_and_control_substitution_cannot_return_receipt(self):
        real = release_module._write
        for boundary in ("NOTICE", "SOURCE-RECEIPT.json"):
            output = self.base / ("late-" + boundary.replace(".", "-"))
            def forward(root, path, data):
                result = real(root, path, data)
                if path == boundary:
                    changed = "src/demo.py" if boundary == "NOTICE" else "SOURCE-RECEIPT.json"
                    (output / changed).write_bytes(b"deliberate task-owned late byte substitution")
                return result
            with self.subTest(boundary=boundary):
                with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError):
                    prepare_release(self.source, self.rights, output, context=self.context)
                self.assertTrue((output / "PREPARATION-PENDING.json").exists())

    def test_overdeep_dependency_json_is_bounded_generic_denial_without_output(self):
        self.replace_source("DEPENDENCIES.json", b"[" * 1500 + b"0" + b"]" * 1500)
        with self.assertRaises(ReleaseRightsError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertFalse(self.output.exists())

    def test_scan_exception_cannot_mask_private_marker_or_an_entire_object(self):
        for ordinal, value in enumerate(("ORGANIZER PRIVATE RECORDING task-owned negative only",
                                        {"password": "task_owned_synthetic_password_0000"})):
            self.replace_source("fixture.json", encoded({"proof": value}))
            exception = SyntheticScanExceptionV1(path="fixture.json", file_hash=self.pins["fixture.json"],
                field=["proof"], value_hash=digest(encoded(value)), origin="task-owned-test-fixture")
            context = self.make_context(scan_exceptions=[exception])
            output = self.base / ("not-narrow-" + str(ordinal))
            with self.subTest(ordinal=ordinal):
                with self.assertRaises(ReleaseRightsError):
                    prepare_release(self.source, self.rights, output, context=context)
                self.assertFalse(output.exists())

    def test_encoded_json_private_marker_denies_with_or_without_exact_exception(self):
        value = "ORGANIZER PRIVATE RECORDING task-owned negative only"
        data = b'{"proof":"ORGANIZER \\u0050RIVATE RECORDING task-owned negative only"}'
        self.replace_source("fixture.json", data)
        exception = SyntheticScanExceptionV1(path="fixture.json", file_hash=self.pins["fixture.json"],
            field=["proof"], value_hash=digest(encoded(value)), origin="task-owned-test-fixture")
        for exempt in (False, True):
            context = self.make_context(scan_exceptions=[exception] if exempt else [])
            output = self.base / ("encoded-private-" + str(exempt))
            with self.subTest(exempt=exempt):
                with self.assertRaises(ReleaseRightsError) as raised:
                    prepare_release(self.source, self.rights, output, context=context)
                self.assertNotIn(value, str(raised.exception))
                self.assertFalse(output.exists())

    def test_static_root_outside_trusted_parent_cannot_self_relabel_its_manifest(self):
        receipt = prepare_release(self.source, self.rights, self.output, context=self.context)
        outside = self.base / "unregistered-parent"
        outside.mkdir()
        clone = outside / "copied-by-test"
        shutil.copytree(self.output, clone)
        path = clone / "RELEASE-MANIFEST.json"
        manifest = json.loads(path.read_bytes())
        manifest["release_root"] = RootIdentityV1.capture(clone).model_dump(mode="json")
        path.write_bytes(encoded(manifest))
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(receipt, release_root=clone, context=self.context)

    def test_untyped_context_or_changed_hash_identity_cannot_replace_host_registry(self):
        for context in (self.context.model_dump(),
                        self.context.model_copy(update={"expected_candidate_hash": "f" * 64})):
            with self.subTest(context_kind=type(context).__name__), self.assertRaises(ReleaseRightsError):
                prepare_release(self.source, self.rights, self.output, context=context)
            self.assertFalse(self.output.exists())
        receipt = prepare_release(self.source, self.rights, self.output, context=self.context)
        for changed in (receipt.model_dump(), receipt.model_copy(update={"release_hash": "0" * 64})):
            with self.subTest(receipt_kind=type(changed).__name__), self.assertRaises(ReleaseRightsError):
                verify_release_static(changed, release_root=self.output, context=self.context)

    def test_source_root_replacement_before_prepare_is_denied_without_output(self):
        self.source.rename(self.base / "retained-source")
        self.source.mkdir()
        with self.assertRaises(ReleaseRightsError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        self.assertFalse(self.output.exists())

    def test_unsafe_and_normalized_colliding_allowlist_paths_deny(self):
        for path in ("../escape", "/absolute", "work/private.txt", "src\\alias.py", "src/./alias.py",
                     "src//alias.py", "src/Demo.py", "archives/private.zip", "e\u0301.py"):
            pins = {**self.pins, path: "a" * 64}
            groups = {key: list(value) for key, value in self.groups.items()}
            groups["source"].append(path)
            rights = {**self.rights, path: {**self.rights["src/demo.py"], "file_hash": "a" * 64}}
            rights_hash = digest(encoded(rights))
            candidate = fingerprint({"kind": "SourceReleaseCandidateV1", "file_hashes": dict(sorted(pins.items())),
                "rights_hash": rights_hash, "dependency_hash": digest(encoded(self.dependency.model_dump(mode="json"))),
                "groups": groups})
            context = self.make_context(file_hashes=pins, groups=groups, rights_hash=rights_hash,
                                        expected_candidate_hash=candidate)
            with self.subTest(path=path), self.assertRaises(ReleaseRightsError):
                prepare_release(self.source, rights, self.output, context=context)
            self.assertFalse(self.output.exists())

    def test_host_count_individual_and_total_byte_limits_are_enforced(self):
        for limit in ({"max_files": 1}, {"max_file_bytes": 8}, {"max_total_bytes": 8}):
            context = self.make_context(**limit)
            with self.subTest(limit=limit), self.assertRaises(ReleaseRightsError):
                prepare_release(self.source, self.rights, self.output, context=context)
            self.assertFalse(self.output.exists())

    def test_missing_notice_or_dependency_artifact_pin_cannot_join(self):
        for update in ({"notice_paths": []},
                       {"file_hashes": {**self.dependency.file_hashes, "NOTICE": "a" * 64}}):
            original = self.dependency
            self.dependency = self.dependency.model_copy(update=update)
            context = self.make_context()
            with self.subTest(update=list(update)), self.assertRaises(ReleaseRightsError):
                prepare_release(self.source, self.rights, self.output, context=context)
            self.assertFalse(self.output.exists())
            self.dependency = original

    def test_manifest_publication_failure_retains_all_copies_but_never_static_success(self):
        real = release_module._write
        def forward(root, path, data):
            if path == "SOURCE-RECEIPT.json":
                raise OSError("task-owned publication failure")
            return real(root, path, data)
        with patch.object(release_module, "_write", side_effect=forward), self.assertRaises(ReleasePreparationError):
            prepare_release(self.source, self.rights, self.output, context=self.context)
        for path, data in self.data.items():
            self.assertEqual((self.output / path).read_bytes(), data)
        self.assertTrue((self.output / "PREPARATION-FAILED.json").exists())
        manifest = json.loads((self.output / "RELEASE-MANIFEST.json").read_bytes())
        from proofkey.contracts import SourceReleaseReceipt
        receipt = SourceReleaseReceipt.model_validate(manifest["receipt"])
        with self.assertRaises(ReleaseRightsError):
            verify_release_static(receipt, release_root=self.output, context=self.context)

    def test_modes_remain_unsupported_and_static_wrong_root_or_stale_receipt_denies(self):
        for mode in ("replay", "unavailable"):
            context = self.make_context(mode=mode)
            output = self.base / (mode + "-release")
            receipt = prepare_release(self.source, self.rights, output, context=context)
            static = verify_release_static(receipt, release_root=output, context=context)
            self.assertEqual(static.mode, mode)
            self.assertIn("rights_certification", static.unsupported_modes)
            stale = receipt.model_copy(update={"candidate_hash": "f" * 64})
            with self.assertRaises(ReleaseRightsError):
                verify_release_static(stale, release_root=output, context=context)
            with self.assertRaises(ReleaseRightsError):
                verify_release_static(receipt, release_root=self.source, context=context)
