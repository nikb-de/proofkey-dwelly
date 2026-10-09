"""Trusted J06 CLI composition; real registered execution and authority denial."""
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from proofkey import synthetic_provisioning as provisioning
from proofkey.bootstrap import CliConfiguration, CliReceiptV1
from proofkey.cli import main
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext
from proofkey.host import AuthResolver, ProfileRegistry, RuntimeFactory
from proofkey.host_admission import (LocalAdmissionCompositionV1, ProvisionedReviewResolverV1,
    SyntheticReviewGrantV1)
from proofkey.host_contracts import HostLimitsV1, InterfaceLimitsV1
from support_synthetic_provisioning import case_data, cj, context
from test_host_admission import paced_clock


class RegisteredCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.parent.chmod(0o700)

    def prepare(self, clock, kind="reschedule_window"):
        request, source = case_data(kind)
        # Retained-source validation includes operator material even for a case
        # that never requests an operator packet. Declare an empty inventory.
        catalog = dict(version="packet-catalog-v1", case_id=request.case_id,
            object_id=request.object_id, complete=True, revision="v1",
            relevant_set_id="j06-empty-artifacts", originals=[], extracts=[], restrictions=[])
        access = dict(version="packet-access-v1", decision_id="j06-operator-access", revision="v1",
            case_id=request.case_id, object_id=request.object_id, sender=request.principal_id,
            recipient="J06-OPERATOR", role="operator", purpose="operator_packet",
            catalog_hash=sha256(cj(catalog)).hexdigest(), permitted_originals=[], permitted_extracts=[],
            issued_at="2026-10-08T10:00:00Z", expires_at="2026-10-08T12:00:00Z", metadata_restrictions=[])
        for key, value in (("operator.packet_catalog", catalog), ("operator.packet_access", access)):
            source["facts"][key] = dict(value=value, revision="v1", case_id=request.case_id,
                object_id=request.object_id, evidence_ref="synthetic-j06:" + key)
        prepared = provisioning.prepare_synthetic_release(
            provisioning.SyntheticCaseReleaseSpecV1("J06-H", "J06-L", "J06-R", request, cj(source)),
            parent=self.parent, clock=clock, execution=context(clock))
        return prepared, request

    def options(self, prepared, request, clock, **changes):
        grant = SyntheticReviewGrantV1("j06-review", prepared.binding.artifact_hash,
            "j06-reviewer", "admit_fixed_local_replay", "synthetic_rehearsal",
            clock.now(), clock.now() + timedelta(minutes=20))
        return dict(approvals=ProvisionedReviewResolverV1((grant,)), review_id="j06-review",
            auth_resolver=AuthResolver({"j06-user": AuthContext(caller_id=request.principal_id,
                proof_reference="j06-synthetic-proof")}), clock=clock, execution=context(clock),
            host_limits=HostLimitsV1(), interface_limits=InterfaceLimitsV1(),
            total_seconds=120.0, publication_reserve_seconds=10.0, shutdown_seconds=2.0,
            **changes)

    def configure(self, prepared, options):
        function = getattr(provisioning, "configure_registered_cli", None)
        self.assertTrue(callable(function), "trusted prepared-release configuration API is missing")
        return function(prepared, **options)

    def invoke(self, prepared, request, configuration, *, release="J06-H", command=None):
        request_path = self.parent / "request.json"
        request_path.write_bytes(request.model_dump_json().encode())
        args = command or ["run", "--input", str(request_path)]
        args = [*args, "--credential-ref", "j06-user"]
        if release is not None:
            args += ["--release", release]
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(args, configuration=configuration)
        raw = output.getvalue()
        self.assertEqual(len(raw.splitlines()), 1)
        for private in ("j06-synthetic-proof", "j06-reviewer", "j06-review", "route-source-declaration-v1"):
            self.assertNotIn(private, raw)
        return code, CliReceiptV1.model_validate_json(raw)

    def assert_no_runtime(self, prepared):
        self.assertEqual(list(prepared.control_parent.iterdir()), [])
        self.assertEqual(list(prepared.host_release.resource_root.iterdir()), [])
        self.assertEqual(list(prepared.inventory_parent.iterdir()), [])
        self.assertEqual(list(prepared.output_parent.iterdir()), [])

    def effect_rows(self, prepared):
        path = prepared.host_release.resource_root / "world.sqlite"
        if not path.exists():
            return []
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            return connection.execute("SELECT operation FROM effects ORDER BY operation").fetchall()

    def test_configuration_accepts_exact_composition_and_cli_forwards_it(self):
        # Omitting the field or dispatcher forwarding breaks the trusted entrypoint.
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            options = self.options(prepared, request, clock)
            composition = LocalAdmissionCompositionV1(prepared.registry, prepared.binding,
                options["approvals"], options["review_id"], prepared.control_parent)
            configuration = CliConfiguration(factory=RuntimeFactory(),
                auth_resolver=options["auth_resolver"], profile_registry=ProfileRegistry((prepared.host_release,)),
                clock=clock, host_limits=options["host_limits"], interface_limits=options["interface_limits"],
                output_parent=prepared.output_parent, inventory_parent=prepared.inventory_parent,
                admission_composition=composition)
            self.assertIs(configuration.admission_composition, composition)
            # Ordinary diagnostic repr must not expand newly attached grant data.
            self.assertFalse("j06-reviewer" in repr(configuration), "configuration repr exposed grant data")
            # A constructor spy halts before runtime execution; integration below uses the real dispatcher.
            observed = []
            def constructor(*args, **kwargs):
                observed.append((args, kwargs))
                raise ValueError("constructor boundary")
            with patch("proofkey.cli.HostDispatcher", constructor):
                code, receipt = self.invoke(prepared, request, configuration)
            self.assertEqual((code, receipt.failure), (4, "bootstrap_unavailable"))
            self.assertEqual(len(observed), 1)
            self.assertIs(observed[0][1]["admission_composition"], composition)
            self.assert_no_runtime(prepared)

    def test_new_cases_execute_registered_cli_and_preserve_effects_and_claims(self):
        # Falling back to builtin execution, bypassing claims, or duplicate effects fails these checks.
        for kind, wanted in (("reschedule_window", [("reschedule",)]),
                             ("goods_refusal", [("create_return",), ("register_goods_refusal",)])):
            with self.subTest(kind=kind), paced_clock() as (clock, state):
                prepared, request = self.prepare(clock, kind)
                configuration = self.configure(prepared, self.options(prepared, request, clock))
                self.assert_no_runtime(prepared)
                code, receipt = self.invoke(prepared, request, configuration)
                self.assertEqual(code, 0)
                self.assertTrue(receipt.shutdown.owner_closed)
                self.assertEqual(receipt.run.command.result.status, "authorized")
                self.assertTrue(all(effect.status == "verified" for effect in receipt.run.command.result.effects.values()))
                self.assertEqual(self.effect_rows(prepared), wanted)
                with sqlite3.connect(prepared.control_parent / "host-claims.sqlite") as connection:
                    claims = connection.execute("SELECT state,wire FROM claims").fetchall()
                self.assertEqual(len(claims), 1)
                self.assertEqual(claims[0][0], "admission_observed")
                claim = json.loads(claims[0][1])
                self.assertEqual(claim["request"], request.model_dump(mode="json"))
                self.assertEqual(claim["artifact_hash"], prepared.binding.artifact_hash)
                self.assertEqual(claim["auth_claim"]["caller_id"], request.principal_id)
                before_claim = claims[0][1]
                # Reconfiguration must not reset or rebind existing claims.
                repeated = self.configure(prepared, self.options(prepared, request, clock))
                code, replay = self.invoke(prepared, request, repeated)
                self.assertEqual(code, 2)
                self.assertEqual((replay.run.command.outcome, replay.run.command.failure),
                                 ("denied", "scope_denied"))
                self.assertEqual(self.effect_rows(prepared), wanted)
                with sqlite3.connect(prepared.control_parent / "host-claims.sqlite") as connection:
                    self.assertEqual(connection.execute("SELECT wire FROM claims").fetchone()[0], before_claim)

    def test_delayed_review_uses_fresh_context_and_expired_context_fails(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            expired = context(clock)
            state["tick"] += 8
            options = self.options(prepared, request, clock)
            with self.assertRaises(ValueError):
                self.configure(prepared, {**options, "execution": expired})
            self.assert_no_runtime(prepared)
            configuration = self.configure(prepared, options)
            self.assert_no_runtime(prepared)
            code, receipt = self.invoke(prepared, request, configuration)
            self.assertEqual(code, 0)
            self.assertTrue(receipt.shutdown.owner_closed)

    def test_review_mismatch_expiry_future_unknown_and_nonexact_resolver_fail(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            options = self.options(prepared, request, clock)
            original = options["approvals"].grants[0]
            variants = [
                {"approvals": None}, {"approvals": object()}, {"review_id": "unknown"},
                {"approvals": ProvisionedReviewResolverV1((replace(original, artifact_hash="0" * 64),))},
                {"approvals": ProvisionedReviewResolverV1((replace(original,
                    issued_at=clock.now() + timedelta(seconds=1)),))},
                {"approvals": ProvisionedReviewResolverV1((replace(original,
                    issued_at=clock.now() - timedelta(seconds=2), expires_at=clock.now()),))},
            ]
            for changes in variants:
                with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                    self.configure(prepared, {**options, **changes})
                self.assert_no_runtime(prepared)

    def test_grant_expiring_between_configuration_and_launch_fails_without_effect(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            options = self.options(prepared, request, clock)
            options["approvals"] = ProvisionedReviewResolverV1((replace(options["approvals"].grants[0],
                expires_at=clock.now() + timedelta(seconds=1)),))
            configuration = self.configure(prepared, options)
            state["tick"] += 2
            code, receipt = self.invoke(prepared, request, configuration)
            self.assertNotEqual(code, 0)
            self.assertNotEqual(receipt.run.command.outcome, "result")
            self.assertEqual(self.effect_rows(prepared), [])

    def test_wrong_proof_has_no_business_effect_and_retains_audited_denial(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            options = self.options(prepared, request, clock)
            options["auth_resolver"] = AuthResolver({"j06-user": AuthContext(
                caller_id=request.principal_id, proof_reference="wrong-proof")})
            configuration = self.configure(prepared, options)
            code, receipt = self.invoke(prepared, request, configuration)
            self.assertEqual(code, 2)
            self.assertTrue(receipt.shutdown.owner_closed)
            self.assertEqual(self.effect_rows(prepared), [])
            self.assertTrue((prepared.control_parent / "host-claims.sqlite").exists())

    def test_omitted_or_wrong_release_fails_before_runtime(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            configuration = self.configure(prepared, self.options(prepared, request, clock))
            for release in (None, "foreign", "host-window-replay-v1", "host-goods-replay-v1"):
                with self.subTest(release=release):
                    code, receipt = self.invoke(prepared, request, configuration, release=release)
                    self.assertEqual((code, receipt.failure), (2, "invalid_input"))
                    self.assertIsNone(receipt.shutdown)
                    self.assert_no_runtime(prepared)

    def test_prepared_and_original_clock_must_be_exact(self):
        class ClockSubclass(SyntheticReplayClock):
            pass
        class PreparedSubclass(provisioning.PreparedSyntheticReleaseV1):
            pass
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            options = self.options(prepared, request, clock)
            for wrong in (SyntheticReplayClock(), ClockSubclass(), object()):
                with self.subTest(clock=type(wrong)), self.assertRaises(ValueError):
                    self.configure(prepared, {**options, "clock": wrong})
            for wrong in (object(), PreparedSubclass(**{name: getattr(prepared, name)
                            for name in prepared.__dataclass_fields__})):
                with self.subTest(prepared=type(wrong)), self.assertRaises(ValueError):
                    self.configure(wrong, options)
            self.assert_no_runtime(prepared)

    def test_configuration_checks_exact_types_selection_and_commitments(self):
        class FactorySubclass(RuntimeFactory):
            pass
        class ClockSubclass(SyntheticReplayClock):
            pass
        class CompositionSubclass(LocalAdmissionCompositionV1):
            pass
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            configuration = self.configure(prepared, self.options(prepared, request, clock))
            composition = configuration.admission_composition
            forged = object.__new__(CompositionSubclass)
            for name in composition.__dataclass_fields__:
                object.__setattr__(forged, name, getattr(composition, name))
            second = replace(prepared.host_release, release_id="J06-H2")
            mismatched_key = ProfileRegistry((second,))
            mismatched_key._entries = {"J06-H": second}
            wrong_hosts = [mismatched_key, ProfileRegistry((second,)), ProfileRegistry((prepared.host_release, second)),
                ProfileRegistry((replace(prepared.host_release, admitted_request_fingerprint="0" * 64),)),
                ProfileRegistry((replace(prepared.host_release, resource_root=self.parent),)),
                ProfileRegistry((replace(prepared.host_release, fixture_hash="0" * 64),))]
            for changes in [{"factory": FactorySubclass()}, {"clock": ClockSubclass()},
                            {"admission_composition": object()}, {"admission_composition": forged},
                            *({"profile_registry": registry} for registry in wrong_hosts)]:
                with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                    replace(configuration, **changes)
            # Frozen objects can still be tampered with by trusted Python; reconstitute typed fields.
            for target, field, value in ((composition.binding, "artifact_hash", "0" * 64),
                    (composition.approvals.grants[0], "provenance", "human_review"),
                    (composition, "review_id", "")):
                old = getattr(target, field)
                try:
                    object.__setattr__(target, field, value)
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        replace(configuration)
                finally:
                    object.__setattr__(target, field, old)
            records = prepared.registry._releases
            try:
                object.__setattr__(prepared.registry, "_releases", records + records)
                with self.assertRaises(ValueError):
                    replace(configuration)
            finally:
                object.__setattr__(prepared.registry, "_releases", records)
            self.assert_no_runtime(prepared)

    def test_mismatched_host_kind_is_denied_at_launch(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            configuration = self.configure(prepared, self.options(prepared, request, clock))
            changed = replace(prepared.host_release, admitted_request_kind="goods_refusal")
            configuration = replace(configuration, profile_registry=ProfileRegistry((changed,)))
            code, receipt = self.invoke(prepared, request, configuration)
            self.assertEqual((code, receipt.run.command.outcome), (2, "denied"))
            self.assertEqual(self.effect_rows(prepared), [])
            self.assertEqual(list(prepared.control_parent.iterdir()), [])

    def test_pending_claim_survives_reconfiguration_and_blocks_launch(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            configuration = self.configure(prepared, self.options(prepared, request, clock))
            runtime = RuntimeFactory().create_registered(prepared.host_release, clock,
                composition=configuration.admission_composition, execution=context(clock))
            try:
                runtime.admission.prepare_entry(request, AuthContext(caller_id=request.principal_id,
                    proof_reference="j06-synthetic-proof"), execution=context(clock, 110))
            finally:
                runtime.close()
            claims_path = prepared.control_parent / "host-claims.sqlite"
            with sqlite3.connect(claims_path) as connection:
                before = connection.execute("SELECT state,wire FROM claims").fetchall()
            self.assertEqual(before[0][0], "prepared")
            configuration = self.configure(prepared, self.options(prepared, request, clock))
            code, receipt = self.invoke(prepared, request, configuration)
            self.assertEqual((code, receipt.run.command.outcome), (2, "denied"))
            self.assertEqual(self.effect_rows(prepared), [])
            with sqlite3.connect(claims_path) as connection:
                self.assertEqual(connection.execute("SELECT state,wire FROM claims").fetchall(), before)

    def test_invalid_durations_fail_without_allocating_runtime(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            options = self.options(prepared, request, clock)
            for changes in ({"total_seconds": 0}, {"total_seconds": True}, {"total_seconds": float("nan")},
                            {"total_seconds": 1000}, {"publication_reserve_seconds": 120},
                            {"publication_reserve_seconds": -1}, {"shutdown_seconds": 0},
                            {"shutdown_seconds": 1000}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    self.configure(prepared, {**options, **changes})
                self.assert_no_runtime(prepared)

    def test_revalidation_rejects_source_binding_and_root_drift(self):
        for mutation in ("source", "pin", "root"):
            with self.subTest(mutation=mutation), paced_clock() as (clock, state):
                prepared, request = self.prepare(clock)
                options = self.options(prepared, request, clock)
                if mutation == "source":
                    prepared.host_release.fixture_path.write_bytes(b"{}")
                elif mutation == "pin":
                    pins = prepared.binding.implementation_pins
                    object.__setattr__(prepared.binding, "implementation_pins", ((pins[0][0], "0" * 64), *pins[1:]))
                else:
                    moved = prepared.root.with_name(prepared.root.name + "-moved")
                    prepared.root.rename(moved)
                    prepared.root.mkdir(mode=0o700)
                with self.assertRaises(ValueError):
                    self.configure(prepared, options)

    def test_registered_controls_remain_denied_and_do_not_change_effects(self):
        with paced_clock() as (clock, state):
            prepared, request = self.prepare(clock)
            configuration = self.configure(prepared, self.options(prepared, request, clock))
            code, first = self.invoke(prepared, request, configuration)
            self.assertEqual(code, 0)
            reply_path = self.parent / "reply.json"
            reply_path.write_bytes(cj(dict(question_id="absent", binding=first.run.command.result.binding.model_dump(mode="json"),
                actor_id=request.principal_id, proof_reference="j06-synthetic-proof", request_revision="v1", consent_revision="v1",
                owner_state_revision="v1", fields={}, received_at=clock.now().isoformat(), simulated=True)))
            commands = [["recover", "--case-id", request.case_id],
                ["stop", "--case-id", request.case_id, "--generation", "G1"],
                ["reply", "--input", str(reply_path)], ["transfer"]]
            for command in commands:
                with self.subTest(command=command[0]):
                    code, receipt = self.invoke(prepared, request, configuration, command=command)
                    self.assertEqual(code, 2)
                    self.assertIn(receipt.run.command.outcome, ("denied", "unavailable"))
                    self.assertTrue(receipt.shutdown.owner_closed)
                    self.assertEqual(self.effect_rows(prepared), [("reschedule",)])

    def test_default_none_keeps_existing_factory_and_clock_interfaces(self):
        class FactorySubclass(RuntimeFactory):
            pass
        class ClockSubclass(SyntheticReplayClock):
            pass
        clock = ClockSubclass()
        configuration = CliConfiguration(FactorySubclass(), AuthResolver({"synthetic-user": AuthContext(
            caller_id="U1", proof_reference="synthetic-proof")}), ProfileRegistry.builtin(self.parent / "resources"),
            clock, HostLimitsV1(), InterfaceLimitsV1(), self.parent, self.parent)
        self.assertIsNone(configuration.admission_composition)
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["inspect-profile"], configuration=configuration)
        receipt = CliReceiptV1.model_validate_json(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(receipt.run.command.outcome, "inspection")
        self.assertTrue(receipt.shutdown.owner_closed)


if __name__ == "__main__":
    unittest.main()
