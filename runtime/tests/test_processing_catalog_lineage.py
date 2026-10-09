"""Private synthetic catalog lineage, never live processing authorization."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from proofkey.contracts import (AssertionsOutput, BudgetLedger, EvidenceAssertion,
    ActionProposal, AudioTime, AuthorityObservation, InvocationRequest, ProcessingReceipt,
    ProcessorIdentity, ProposalOutput, RoleAllowance, TextSpan, TranscriptOutput, TranscriptSegment,
    UnknownLocator)
from proofkey.evidence.catalog import EvidenceCatalog
from proofkey.identity import fingerprint
from proofkey.journal import CaseStore
from support import (FakeClock, NOW, DEADLINE, make_auth, make_binding,
    make_checkpoint, make_fixture_campaign, make_request)

CHILD_MODULE_PATHS = set()


def runtime_module_paths():
    import sys
    runtime = Path(__file__).resolve().parents[1]
    paths = set()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(runtime / "src") or path.is_relative_to(runtime / "tests"):
                paths.add(str(path))
    return sorted(paths)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def crash_worker(folder, boundary):
    """Actual child-only public resources; parent sends SIGKILL at a printed barrier."""
    import signal
    from proofkey.evidence.processing_contracts import ProcessingCatalogBindings, SavedOriginalScope
    folder = Path(folder).resolve()
    store = CaseStore(folder / "journal.sqlite")
    clock, auth = FakeClock(), make_auth()
    original = make_request(narrative="  Box damaged.\n")
    binding = make_binding(original)
    def lookup(candidate):
        if store.find_request(candidate.case_id, candidate.request_id, candidate.request_revision,
                candidate.consent_revision, candidate.fingerprint) != candidate:
            raise ValueError("Not registered exact saved binding")
        return store.original_request(candidate.case_id, candidate.generation)
    def scope(candidate, saved, proof, purpose):
        if candidate != binding or saved != original or proof != auth or clock.now() >= DEADLINE:
            return None
        raw = dict(allowed_actors=["U1"], case_id="C1", object_id="O1",
            binding_hash=fingerprint(binding.model_dump(mode="json")),
            original_request_hash=fingerprint(original.model_dump(mode="json")), scope_id="saved-scope",
            policy_id="local-policy", authorization_reference="local-proof",
            provenance="synthetic_host_registration", expires_at=DEADLINE.isoformat())
        return SavedOriginalScope(canonical(binding.model_dump(mode="json")), raw["original_request_hash"],
            "saved-scope", canonical(raw), "local-policy", "synthetic_host_registration", "local-proof", DEADLINE)
    def access(proof, record, saved_scope, purpose):
        return (proof == auth and record.case_id == "C1" and saved_scope["allowed_actors"] == ("U1",)
                and saved_scope.get("scope_id") == "saved-scope")
    catalog = EvidenceCatalog(folder / "catalog", clock, allowed_input_roots=[folder], access_resolver=access,
        processing_bindings=ProcessingCatalogBindings(lookup, lambda b: store.checkpoint(b.case_id),
                                                     store.invocation, scope))
    record = catalog.register_saved_narrative(binding, auth)
    grant = make_fixture_campaign(input_hashes=[record.original_hash])
    store.register_campaign(grant)
    identity = ProcessorIdentity(case_id="C1", generation="G1", role="extraction",
        campaign_id=grant.campaign_id, permit_hash=grant.permit_hash, input_hashes=grant.input_hashes,
        provider=grant.provider, model=grant.model, endpoint=grant.endpoint,
        prompt_hash="2" * 64, version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
    store.reserve_invocation(InvocationRequest(identity=identity, invocation_id="invoke-1",
        requested_usage={"tokens": 2}, worst_case_cost=1), NOW)
    def barrier():
        print("CHILD_MODULES " + json.dumps(runtime_module_paths()), flush=True)
        print("BOUNDARY " + boundary, flush=True)
        signal.pause()
        raise RuntimeError("Barrier unexpectedly resumed")
    if boundary == "reserved-before-seal":
        barrier()
    catalog.seal_invocation_inputs(binding, "invoke-1", (record.artifact_id,), auth)
    output = AssertionsOutput(kind="assertions", assertions=[])
    receipt = ProcessingReceipt(invocation_id="invoke-1", role="extraction", provider=identity.provider,
        requested_model=identity.model, prompt_hash=identity.prompt_hash, version="v1", input_hashes=identity.input_hashes,
        mode="synthetic", status="completed", latency_seconds=0, usage={}, processed_at=NOW, output=output,
        output_hashes=[hashlib.sha256(output.model_dump_json().encode()).hexdigest()])
    store.record_processing("invoke-1", receipt)
    old = catalog._store
    def interrupted(path, payload):
        if path.name.startswith("output-marker-"):
            barrier()
        return old(path, payload)
    catalog._store = interrupted
    catalog.publish_processing_output(binding, "invoke-1", auth)
    raise RuntimeError("Expected interruption did not occur")


class ProcessingCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.store = CaseStore(self.folder / "journal.sqlite")
        self.addCleanup(self.store.close)
        self.clock = FakeClock()
        self.auth = make_auth()
        self.original = make_request(narrative="  Box damaged.\n")
        self.binding = make_binding(self.original)
        self.checkpoint = make_checkpoint(binding=self.binding, budget=BudgetLedger(
            case_id="C1", deadline=DEADLINE, role_allowances={role: RoleAllowance(
                max_invocations=4, max_cost=4, usage_allowances={"tokens": 40})
                for role in ("extraction", "planning", "transcription")}))
        self.store.admit(self.binding, self.original, self.checkpoint)
        self.revoked = set()
        self.catalog = self.make_catalog()

    def access(self, auth, record, scope, purpose):
        return (auth == self.auth and record.case_id == self.binding.case_id
                and scope["allowed_actors"] == ("U1",)
                and scope.get("scope_id", "parent") not in self.revoked)

    def scope(self, binding, original, auth, purpose):
        from proofkey.evidence.processing_contracts import SavedOriginalScope
        if (binding != self.binding or original != self.original or auth != self.auth
                or "saved-scope" in self.revoked or self.clock.now() >= DEADLINE):
            return None
        raw = dict(allowed_actors=["U1"], case_id=binding.case_id, object_id=binding.object_id,
            binding_hash=fingerprint(binding.model_dump(mode="json")),
            original_request_hash=fingerprint(original.model_dump(mode="json")),
            scope_id="saved-scope", policy_id="local-policy", authorization_reference="local-proof",
            provenance="synthetic_host_registration", expires_at=DEADLINE.isoformat())
        return SavedOriginalScope(canonical(binding.model_dump(mode="json")),
            raw["original_request_hash"], raw["scope_id"], canonical(raw), raw["policy_id"],
            raw["provenance"], raw["authorization_reference"], DEADLINE)

    def make_catalog(self, **limits):
        from proofkey.evidence.processing_contracts import ProcessingCatalogBindings
        def original(binding):
            found = self.store.find_request(binding.case_id, binding.request_id,
                binding.request_revision, binding.consent_revision, binding.fingerprint)
            if found != binding:
                raise ValueError("Not the saved original binding")
            return self.store.original_request(binding.case_id, binding.generation)
        bindings = ProcessingCatalogBindings(original,
            lambda binding: self.store.checkpoint(binding.case_id), self.store.invocation,
            self.scope, **limits)
        return EvidenceCatalog(self.folder / "catalog", self.clock,
            allowed_input_roots=[self.folder], access_resolver=self.access,
            processing_bindings=bindings)

    def planning(self):
        from proofkey.profiles import load_profile
        profile = load_profile("flat-v1")
        checkpoint = self.store.checkpoint("C1").model_copy(update={"phase": "window_gate", "next_gate": "reschedule"})
        self.store.save_checkpoint(checkpoint)
        self.catalog = self.make_catalog(profile_lookup=lambda binding, original: profile)
        return checkpoint

    def reserve(self, records, role="extraction", invocation_id="invoke-1"):
        hashes = [record.original_hash for record in records]
        grant = make_fixture_campaign(role=role, input_hashes=hashes,
            campaign_id="campaign-" + invocation_id)
        self.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id="C1", generation="G1", role=role,
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash,
            input_hashes=hashes, provider=grant.provider, model=grant.model,
            endpoint=grant.endpoint, prompt_hash="2" * 64, version="v1",
            profile_version="v1", process_version="v1", deadline=DEADLINE)
        self.store.reserve_invocation(InvocationRequest(identity=identity,
            invocation_id=invocation_id, requested_usage={"tokens": 2}, worst_case_cost=1), NOW)
        return identity

    def save_output(self, identity, output, invocation_id="invoke-1", **changes):
        receipt = ProcessingReceipt(invocation_id=invocation_id, role=identity.role,
            provider=identity.provider, requested_model=identity.model, prompt_hash=identity.prompt_hash,
            version=identity.version, input_hashes=identity.input_hashes, mode="synthetic",
            status="completed", latency_seconds=0, usage={"tokens": 1}, processed_at=NOW,
            output=output, output_hashes=[hashlib.sha256(output.model_dump_json().encode()).hexdigest()])
        receipt = receipt.model_copy(update=changes)
        self.store.record_processing(invocation_id, receipt)
        return receipt

    def assertion(self, record, **changes):
        return EvidenceAssertion(artifact_id=record.artifact_id, content_hash=record.original_hash,
            lineage_hash=record.lineage_hash, locator=TextSpan(kind="text_span", start=0, end=2),
            uncertainty="uncertain", processing_receipt_id="invoke-1", claim="Damaged").model_copy(update=changes)

    def extraction(self, **changes):
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        identity = self.reserve([record])
        seal = self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        assertion = self.assertion(record, **changes)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[assertion]))
        return record, seal, assertion

    def wav(self):
        import wave
        path = self.folder / "local.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(100)
            out.writeframes(b"\0\0" * 100)
        return self.catalog.register(path, "C1", "synthetic-local-audio",
                                     {"allowed_actors": ["U1"], "scope_id": "audio-parent"})

    def transcript(self):
        audio = self.wav()
        identity = self.reserve([audio], "transcription")
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (audio.artifact_id,), self.auth)
        output = TranscriptOutput(kind="transcript", text="Private synthetic transcript",
            segments=[TranscriptSegment(text="Private", locator=AudioTime(kind="audio_time", start_seconds=0, end_seconds=1))])
        self.save_output(identity, output)
        return audio, self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)

    def fix_legacy_input(self):
        # Two real constructor policies intentionally disagree; no body grants.
        from proofkey.evidence.processing_contracts import ProcessingCatalogBindings
        self.saved_access_denied = False
        self.denied_saved_records = set()
        self.fix_access_calls = []
        def access(auth, record, scope, purpose):
            self.fix_access_calls.append((record.artifact_id, scope.get("scope_id"), purpose))
            return self.access(auth, record, scope, purpose) and not (
                scope.get("scope_id") == "saved-scope" and (self.saved_access_denied
                    or record.artifact_id in self.denied_saved_records))
        def original(binding):
            if self.store.find_request(binding.case_id, binding.request_id, binding.request_revision,
                    binding.consent_revision, binding.fingerprint) != binding:
                raise ValueError("Not exact saved binding")
            return self.store.original_request(binding.case_id, binding.generation)
        self.catalog = EvidenceCatalog(self.folder / "catalog", self.clock,
            allowed_input_roots=[self.folder], access_resolver=access,
            processing_bindings=ProcessingCatalogBindings(original,
                lambda binding: self.store.checkpoint(binding.case_id), self.store.invocation, self.scope))
        path = self.folder / "legacy-parent.txt"
        path.write_bytes(b"Box damaged.\n")
        return self.catalog.register(path, "C1", "synthetic-local-text",
            {"allowed_actors": ["U1"], "scope_id": "parent"})

    def fix_files(self):
        return {str(p.relative_to(self.catalog.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.catalog.root.rglob("*") if p.is_file()}

    def test_legacy_seal_intersects_independent_saved_scope_before_new_bytes(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        self.reserve([record])
        before, debt = self.fix_files(), self.store.checkpoint("C1").budget
        self.saved_access_denied = True
        # The registered original/proof still validates, and legacy get still allows.
        self.assertIsNotNone(self.scope(self.binding, self.original, self.auth, "provider_processing"))
        self.assertEqual(self.catalog.get(record.artifact_id, self.auth), record)
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertIn((record.artifact_id, "saved-scope", "provider_processing"), self.fix_access_calls)
        self.assertEqual(before, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)
        self.assertEqual(self.store.invocation("invoke-1")[0].status, "consumed")

    def test_legacy_output_intersects_saved_scope_after_lawful_seal(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[self.assertion(record)]))
        before, debt = self.fix_files(), self.store.checkpoint("C1").budget
        self.saved_access_denied = True
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(before, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)

    def test_real_marker_write_crossing_expiry_denies_return_preserves_marker_and_debt(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[self.assertion(record)]))
        debt = self.store.checkpoint("C1").budget
        real_store, forwarded = self.catalog._store, []
        def write_then_expire(path, payload):
            result = real_store(path, payload)
            if path.name.startswith("output-marker-"):
                forwarded.append(path)
                self.assertEqual(path.read_bytes(), payload)
                self.clock.advance((DEADLINE - self.clock.now()).total_seconds())
            return result
        self.catalog._store = write_then_expire
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(len(forwarded), 1)
        self.assertEqual(self.clock.now(), DEADLINE)
        self.assertEqual(json.loads(forwarded[0].read_bytes())["status"], "completed")
        after = self.fix_files()
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(after, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)
        self.assertEqual(self.store.invocation("invoke-1")[0].status, "completed")

    def test_real_seal_write_crossing_expiry_denies_usable_input_without_refund(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        self.reserve([record])
        debt, real_store, forwarded = self.store.checkpoint("C1").budget, self.catalog._store, []
        def write_then_expire(path, payload):
            result = real_store(path, payload)
            if path.name.startswith("inputs-"):
                forwarded.append(path)
                self.assertEqual(path.read_bytes(), payload)
                self.clock.advance((DEADLINE - self.clock.now()).total_seconds())
            return result
        self.catalog._store = write_then_expire
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(len(forwarded), 1)
        after = self.fix_files()
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(after, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)
        self.assertEqual(self.store.invocation("invoke-1")[0].status, "consumed")

    def test_planning_final_record_write_cannot_return_stale_predebit_checkpoint(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        checkpoint = self.planning()
        real_store, forwarded = self.catalog._store, []
        def write_then_stop(path, payload):
            result = real_store(path, payload)
            if path.parent.name == "records":
                forwarded.append(path)
                self.store.set_stop("C1", "G1")
            return result
        self.catalog._store = write_then_stop
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.register_planning_snapshot(checkpoint, (), self.auth)
        self.assertEqual(denied.exception.code, "identity_mismatch")
        self.assertEqual(len(forwarded), 1)
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)
        after = self.fix_files()
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.register_planning_snapshot(checkpoint, (), self.auth)
        self.assertEqual(after, self.fix_files())

    def test_intersected_legacy_publication_positive_is_exact_idempotent_and_no_new_debit(self):
        record = self.fix_legacy_input()
        identity = self.reserve([record])
        seal = self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(seal.input_records(), (record,))
        assertion = self.assertion(record)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[assertion]))
        before = self.store.checkpoint("C1").budget
        result = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(result.assertions(), (assertion,))
        self.assertIn((record.artifact_id, "parent", "provider_processing"), self.fix_access_calls)
        self.assertIn((record.artifact_id, "saved-scope", "provider_processing"), self.fix_access_calls)
        after = self.fix_files()
        self.assertEqual(result, self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth))
        self.assertEqual(after, self.fix_files())
        self.assertEqual(before, self.store.checkpoint("C1").budget)
        self.assertEqual(before.tool_calls, 1)
        self.assertEqual(before.active_seconds, 10.0)
        self.assertEqual(before.planner_calls, 0)

    def test_saved_scope_allow_cannot_replace_denied_original_opaque_parent(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        self.reserve([record])
        before, debt = self.fix_files(), self.store.checkpoint("C1").budget
        self.revoked.add("parent")
        self.assertIsNotNone(self.scope(self.binding, self.original, self.auth, "provider_processing"))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(before, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)

    def test_derived_input_intersection_reaches_actual_original_ancestor(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.fix_legacy_input()
        audio, publication = self.transcript()
        record = publication.transcript_record()
        self.reserve([record], "extraction", "extract-transcript")
        # Legacy derived get and both original opaque ACLs still allow.
        self.denied_saved_records.add(audio.artifact_id)
        self.assertEqual(self.catalog.get(record.artifact_id, self.auth), record)
        before, debt = self.fix_files(), self.store.checkpoint("C1").budget
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.seal_invocation_inputs(self.binding, "extract-transcript", (record.artifact_id,), self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertIn((audio.artifact_id, "saved-scope", "provider_processing"), self.fix_access_calls)
        self.assertEqual(before, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)

    def test_real_marker_parent_revocation_denies_return_and_repeat_without_file_growth(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[self.assertion(record)]))
        debt, real_store, paths = self.store.checkpoint("C1").budget, self.catalog._store, []
        def write_then_revoke(path, payload):
            result = real_store(path, payload)
            if path.name.startswith("output-marker-"):
                paths.append(path)
                self.revoked.add("parent")
            return result
        self.catalog._store = write_then_revoke
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(len(paths), 1)
        self.assertEqual(json.loads(paths[0].read_bytes())["status"], "completed")
        after = self.fix_files()
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(after, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)

    def test_real_marker_original_proof_revocation_denies_usable_return_keeps_private_marker(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[self.assertion(record)]))
        debt, real_store, paths = self.store.checkpoint("C1").budget, self.catalog._store, []
        def write_then_revoke(path, payload):
            result = real_store(path, payload)
            if path.name.startswith("output-marker-"):
                paths.append(path)
                self.revoked.add("saved-scope")
            return result
        self.catalog._store = write_then_revoke
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(len(paths), 1)
        after = self.fix_files()
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(after, self.fix_files())
        self.assertEqual(debt, self.store.checkpoint("C1").budget)

    def test_final_seal_rechecks_actual_saved_attempt_after_real_write(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.fix_legacy_input()
        identity = self.reserve([record])
        debt, real_store, paths = self.store.checkpoint("C1").budget, self.catalog._store, []
        def write_then_record(path, payload):
            result = real_store(path, payload)
            if path.name.startswith("inputs-"):
                paths.append(path)
                self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[]))
            return result
        self.catalog._store = write_then_record
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(denied.exception.code, "identity_mismatch")
        self.assertEqual(len(paths), 1)
        self.assertEqual(self.store.invocation("invoke-1")[0].status, "completed")
        self.assertEqual(debt, self.store.checkpoint("C1").budget)

    def test_saved_narrative_real_final_write_expiry_stays_unavailable_with_private_bytes(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        real_store, paths = self.catalog._store, []
        def write_then_expire(path, payload):
            result = real_store(path, payload)
            if path.parent.name == "records":
                paths.append(path)
                self.clock.advance((DEADLINE - self.clock.now()).total_seconds())
            return result
        self.catalog._store = write_then_expire
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.register_saved_narrative(self.binding, self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(len(paths), 1)
        after = self.fix_files()
        self.assertEqual(self.store.checkpoint("C1").budget.tool_calls, 0)
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.register_saved_narrative(self.binding, self.auth)
        self.assertEqual(after, self.fix_files())

    def test_saved_narrative_preserves_exact_original_and_repeat_identity(self):
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        self.assertEqual(self.catalog.read_original(record.artifact_id, self.auth),
                         self.original.narrative.encode())
        self.assertEqual(record.source, "saved-request-narrative")
        self.assertEqual(record, self.catalog.register_saved_narrative(self.binding, self.auth))

    def test_saved_narrative_scope_is_revocable_and_bad_proof_cannot_register(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        from proofkey.evidence.catalog import EvidenceAccessDenied
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.register_saved_narrative(self.binding, make_auth(proof_reference="wrong"))
        self.assertEqual(denied.exception.code, "scope_denied")
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        self.revoked.add("saved-scope")
        with self.assertRaises(EvidenceAccessDenied):
            self.catalog.read_original(record.artifact_id, self.auth)

    def test_planning_snapshot_is_exact_predebit_anthropic_bytes(self):
        checkpoint = self.planning()
        record = self.catalog.register_planning_snapshot(checkpoint, (), self.auth)
        expected = canonical({"checkpoint": checkpoint.model_dump(mode="json"), "observations": []})
        self.assertEqual(self.catalog.read_original(record.artifact_id, self.auth), expected)
        self.reserve([record], "planning")
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.register_planning_snapshot(checkpoint, (), self.auth)

    def test_planning_missing_profile_and_illegal_selected_gate_are_unavailable(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        checkpoint = self.planning()
        self.catalog = self.make_catalog()
        with self.assertRaises(ProcessingPublicationError) as missing:
            self.catalog.register_planning_snapshot(checkpoint, (), self.auth)
        self.assertEqual(missing.exception.code, "input_unavailable")
        self.planning()
        bad = self.store.checkpoint("C1").model_copy(update={"next_gate": "read_authority"})
        self.store.save_checkpoint(bad)
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.register_planning_snapshot(bad, (), self.auth)

    def test_reserved_inputs_and_saved_assertions_publish_exact_lineage_idempotently(self):
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        identity = self.reserve([record])
        seal = self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(seal.input_records(), (record,))
        assertion = EvidenceAssertion(artifact_id=record.artifact_id,
            content_hash=record.original_hash, lineage_hash=record.lineage_hash,
            locator=TextSpan(kind="text_span", start=2, end=5), uncertainty="conflicting",
            processing_receipt_id="invoke-1", claim="Box damaged")
        receipt = self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[assertion]))
        before = self.store.checkpoint("C1").budget
        publication = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(publication.assertions(), (assertion,))
        self.assertEqual(publication.receipt_hash, fingerprint(receipt.model_dump(mode="json")))
        self.assertEqual(publication, self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth))
        self.assertEqual(before, self.store.checkpoint("C1").budget)
        self.assertEqual(self.catalog.assertions(record.artifact_id, self.auth), [])

    def test_repeat_publication_has_exact_private_inventory_without_parser_uuid_growth(self):
        self.extraction()
        result = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        def inventory():
            return {str(p.relative_to(self.catalog.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in self.catalog.root.rglob("*") if p.is_file()}
        before = inventory()
        self.clock.advance(1)
        self.assertEqual(result, self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth))
        self.assertEqual(before, inventory())
        self.assertEqual(list((self.catalog.root / "receipts").glob("format-*")), [])

    def test_public_invocation_callback_seals_before_processor_and_saved_output_publish(self):
        from proofkey.providers.invocations import InvocationService
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        grant = make_fixture_campaign(input_hashes=[record.original_hash])
        self.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id="C1", generation="G1", role="extraction",
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash, input_hashes=grant.input_hashes,
            provider=grant.provider, model=grant.model, endpoint=grant.endpoint,
            prompt_hash="2" * 64, version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
        service = InvocationService("C1", self.store, self.clock, grant, identity,
                                    worst_case_cost=1, invocation_id_factory=lambda: "invoke-1")
        events = []
        def processor():
            self.assertEqual(self.store.invocation("invoke-1")[0].status, "consumed")
            seal = self.catalog.seal_invocation_inputs(self.binding, service.current_request.invocation_id,
                                                      (record.artifact_id,), self.auth)
            events.append("sealed")
            context = service.processing_context(self.catalog, self.auth, input_records=seal.input_records())
            events.append("processor")
            output = AssertionsOutput(kind="assertions", assertions=[self.assertion(record)])
            return ProcessingReceipt(invocation_id=context.invocation_id, role="extraction",
                provider=identity.provider, requested_model=identity.model, prompt_hash=identity.prompt_hash,
                version="v1", input_hashes=identity.input_hashes, mode="synthetic", status="completed",
                latency_seconds=0, usage={"tokens": 1}, processed_at=NOW, output=output,
                output_hashes=[hashlib.sha256(output.model_dump_json().encode()).hexdigest()])
        service.call("extraction", [record.original_hash], {"tokens": 2}, processor)
        publication = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(events, ["sealed", "processor"])
        self.assertEqual(publication.assertions()[0].processing_receipt_id, "invoke-1")
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].invocations, 1)

    def test_transcript_keeps_audio_parent_and_separately_charged_extraction(self):
        audio, publication = self.transcript()
        record = publication.transcript_record()
        self.assertEqual(record.parent_hashes, [audio.original_hash])
        self.assertEqual(self.catalog.read_original(record.artifact_id, self.auth), b"Private synthetic transcript")
        identity = self.reserve([record], "extraction", "extract-transcript")
        self.catalog.seal_invocation_inputs(self.binding, "extract-transcript", (record.artifact_id,), self.auth)
        assertion = self.assertion(record, processing_receipt_id="extract-transcript")
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[assertion]), "extract-transcript")
        result = self.catalog.publish_processing_output(self.binding, "extract-transcript", self.auth)
        self.assertEqual(result.assertions(), (assertion,))
        budget = self.store.checkpoint("C1").budget
        self.assertEqual(budget.role_allowances["transcription"].invocations, 1)
        self.assertEqual(budget.role_allowances["extraction"].invocations, 1)

    def test_parent_revocation_denies_derived_read_and_repeat_publication(self):
        from proofkey.evidence.catalog import EvidenceAccessDenied
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        _, publication = self.transcript()
        self.revoked.add("audio-parent")
        with self.assertRaises(EvidenceAccessDenied):
            self.catalog.read_original(publication.transcript_record().artifact_id, self.auth)
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")

    def test_planning_saved_proposal_is_private_and_not_an_effect(self):
        checkpoint = self.planning()
        observations = (AuthorityObservation(authority="delivery", fact="status", object_id="O1",
            value="scheduled", revision="v1", observed_at=NOW, evidence_ref="unattested-typed"),)
        record = self.catalog.register_planning_snapshot(checkpoint, observations, self.auth)
        identity = self.reserve([record], "planning")
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        output = ProposalOutput(kind="proposal", proposal=ActionProposal(operation="reschedule",
            stage="commit", arguments={"slot": "S1"}, evidence_refs=["unattested-typed"]))
        self.save_output(identity, output)
        before = self.store.checkpoint("C1")
        result = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertTrue(result.proposal_receipt_ref.startswith("private-proposal-"))
        self.assertEqual(before, self.store.checkpoint("C1"))
        self.assertEqual(result.assertions(), ())

    def test_assertion_coordinates_beyond_actual_source_deny(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.extraction(locator=TextSpan(kind="text_span", start=0, end=999))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "output_invalid")

    def test_assertion_foreign_receipt_and_content_hash_deny(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.extraction(processing_receipt_id="other-receipt", content_hash="9" * 64)
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)

    def test_unknown_locator_and_conflict_are_retained_not_manufactured(self):
        _, _, assertion = self.extraction(locator=UnknownLocator(reason="missing-coordinates"), uncertainty="conflicting")
        result = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(result.assertions(), (assertion,))

    def test_equal_hash_different_acl_logical_inputs_cannot_replace_seal(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        path = self.folder / "same.txt"
        path.write_bytes(b"same")
        first = self.catalog.register(path, "C1", "first", {"allowed_actors": ["U1"], "scope_id": "first"})
        second = self.catalog.register(path, "C1", "second", {"allowed_actors": ["U1"], "scope_id": "second"})
        self.assertEqual(first.original_hash, second.original_hash)
        self.reserve([first])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (first.artifact_id,), self.auth)
        with self.assertRaises(ProcessingPublicationError) as conflict:
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (second.artifact_id,), self.auth)
        self.assertEqual(conflict.exception.code, "publication_conflict")

    def test_duplicate_inputs_and_post_output_seal_deny_without_new_debit(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        identity = self.reserve([record])
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id, record.artifact_id), self.auth)
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[]))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.assertEqual(denied.exception.code, "not_reserved")
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].invocations, 1)

    def test_derived_parent_equal_hash_record_substitution_denies_read(self):
        from proofkey.evidence.catalog import EvidenceAccessDenied
        audio, publication = self.transcript()
        record = publication.transcript_record()
        audio_path = self.folder / "copy.wav"
        audio_path.write_bytes(self.catalog.read_original(audio.artifact_id, self.auth))
        substitute = self.catalog.register(audio_path, "C1", "another-audio",
            {"allowed_actors": ["U1"], "scope_id": "another-parent"})
        metadata_path = self.catalog.root / "records" / (record.artifact_id + ".json")
        envelope = json.loads(metadata_path.read_bytes())
        envelope["processing"]["parents"] = [substitute.model_dump(mode="json")]
        metadata_path.write_bytes(canonical(envelope))
        with self.assertRaises(EvidenceAccessDenied):
            self.catalog.read_original(record.artifact_id, self.auth)

    def test_publication_marker_conflict_is_not_repaired_and_keeps_debt(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.extraction()
        result = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        marker = next(p for p in (self.catalog.root / "receipts").glob("output-marker-*.json"))
        marker.write_bytes(b"corrupt")
        before = self.store.checkpoint("C1").budget
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "publication_conflict")
        self.assertEqual(marker.read_bytes(), b"corrupt")
        self.assertEqual(before, self.store.checkpoint("C1").budget)
        self.assertEqual(result.status, "completed")

    def test_exact_incomplete_publication_finishes_without_overwrite_or_new_timestamp(self):
        from unittest.mock import patch
        self.extraction()
        original_write = self.catalog._store
        def fault(path, payload):
            if path.name.startswith("output-marker-"):
                raise OSError("Injected temporary marker write interruption")
            return original_write(path, payload)
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        with patch.object(self.catalog, "_store", side_effect=fault), self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        controls = {p.name: p.read_bytes() for p in (self.catalog.root / "receipts").glob("output-control-*.json")}
        self.clock.advance(1)
        reopened = self.make_catalog()
        result = reopened.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(controls, {p.name: p.read_bytes() for p in (self.catalog.root / "receipts").glob("output-control-*.json")})
        self.assertEqual(result, reopened.publish_processing_output(self.binding, "invoke-1", self.auth))

    def test_new_registration_access_denial_is_closed_error_not_raw_access_exception(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.catalog.access_resolver = lambda auth, record, scope, purpose: False
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.register_saved_narrative(self.binding, self.auth)
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(list((self.catalog.root / "receipts").iterdir()), [])

    def test_default_none_keeps_legacy_and_all_new_operations_unavailable(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        catalog = EvidenceCatalog(self.folder / "legacy", self.clock,
            allowed_input_roots=[self.folder], access_resolver=self.access)
        path = self.folder / "legacy.txt"
        path.write_bytes(b"legacy exact")
        record = catalog.register(path, "C1", "legacy", {"allowed_actors": ["U1"]})
        self.assertEqual(catalog.read_original(record.artifact_id, self.auth), b"legacy exact")
        for call in (lambda: catalog.register_saved_narrative(self.binding, self.auth),
            lambda: catalog.register_planning_snapshot(self.checkpoint, (), self.auth),
            lambda: catalog.seal_invocation_inputs(self.binding, "missing", (), self.auth),
            lambda: catalog.publish_processing_output(self.binding, "missing", self.auth)):
            with self.assertRaises(ProcessingPublicationError) as unavailable:
                call()
            self.assertEqual(unavailable.exception.code, "input_unavailable")

    def test_wrong_binding_and_scope_expiry_deny(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.register_saved_narrative(self.binding.model_copy(update={"generation": "foreign"}), self.auth)
        self.clock.advance(7200)
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.register_saved_narrative(self.binding, self.auth)

    def test_saved_receipt_output_digest_mismatch_denies_without_rewrite(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[]), output_hashes=["9" * 64])
        before = self.store.invocation("invoke-1")
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "output_invalid")
        self.assertEqual(before, self.store.invocation("invoke-1"))

    def test_noncomplete_and_nonsynthetic_saved_attempts_stay_unusable_consumed(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        for index, (status, mode) in enumerate((("outcome_unknown", "synthetic"), ("failed", "synthetic"),
                                               ("unavailable", "unavailable"), ("completed", "replay"))):
            invocation_id = "attempt-" + str(index)
            identity = self.reserve([record], invocation_id=invocation_id)
            self.catalog.seal_invocation_inputs(self.binding, invocation_id, (record.artifact_id,), self.auth)
            output = AssertionsOutput(kind="assertions", assertions=[]) if status == "completed" else None
            receipt = ProcessingReceipt(invocation_id=invocation_id, role="extraction", provider=identity.provider,
                requested_model=identity.model, prompt_hash=identity.prompt_hash, version=identity.version,
                input_hashes=identity.input_hashes, mode=mode, status=status, latency_seconds=0,
                usage={}, processed_at=NOW, output=output,
                output_hashes=[] if output is None else [hashlib.sha256(output.model_dump_json().encode()).hexdigest()])
            self.store.record_processing(invocation_id, receipt)
            with self.assertRaises(ProcessingPublicationError) as denied:
                self.catalog.publish_processing_output(self.binding, invocation_id, self.auth)
            self.assertEqual(denied.exception.code, "not_complete")
        self.assertEqual(self.store.checkpoint("C1").budget.role_allowances["extraction"].invocations, 4)

    def test_private_symlink_and_public_mode_objects_deny_without_repair(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        record, _, _ = self.extraction()
        object_path = self.catalog.root / "objects" / record.original_hash
        object_path.chmod(0o644)
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        object_path.chmod(0o600)
        private_target = self.folder / "private-target.txt"
        private_target.write_bytes(object_path.read_bytes())
        private_target.chmod(0o600)
        object_path.unlink()
        object_path.symlink_to(private_target)
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertTrue(object_path.is_symlink())

    def test_tight_claim_limit_does_not_truncate(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.catalog = self.make_catalog(max_claim_bytes=2)
        self.extraction()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "output_invalid")

    def test_tight_output_count_and_aggregate_input_limits_deny(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.catalog = self.make_catalog(max_output_items=1)
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[self.assertion(record)] * 2))
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        # Existing generic originals remain legacy-compatible; the new input seal is stricter.
        limited = self.make_catalog(max_publication_bytes=4096)
        originals = []
        for index in range(2):
            path = self.folder / ("bounded-" + str(index) + ".txt")
            path.write_bytes(bytes([65 + index]) * 3000)
            originals.append(limited.register(path, "C1", "synthetic", {"allowed_actors": ["U1"]}))
        self.reserve(originals, invocation_id="large-inputs")
        with self.assertRaises(ProcessingPublicationError) as denied:
            limited.seal_invocation_inputs(self.binding, "large-inputs", tuple(r.artifact_id for r in originals), self.auth)
        self.assertEqual(denied.exception.code, "input_unavailable")

    def test_planning_wrong_versions_unknown_phase_and_terminal_state_deny(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        from proofkey.contracts import EnvironmentProfile
        from proofkey.profiles import load_profile
        checkpoint = self.planning()
        profile = load_profile("flat-v1")
        raw = profile.model_dump(mode="json")
        raw["version"] = "wrong-version"
        raw["release_hash"] = fingerprint({k: v for k, v in raw.items() if k != "release_hash"})
        wrong = EnvironmentProfile.model_validate(raw)
        catalog = self.make_catalog(profile_lookup=lambda binding, original: wrong)
        with self.assertRaises(ProcessingPublicationError) as unavailable:
            catalog.register_planning_snapshot(checkpoint, (), self.auth)
        self.assertEqual(unavailable.exception.code, "input_unavailable")
        raw = profile.model_dump(mode="json")
        process = raw["processes"][self.original.kind]
        process["version"] = "wrong-process"
        process["release_hash"] = fingerprint({k: v for k, v in process.items() if k != "release_hash"})
        raw["process_hash"] = fingerprint(raw["processes"])
        raw["release_hash"] = fingerprint({k: v for k, v in raw.items() if k != "release_hash"})
        wrong_process = EnvironmentProfile.model_validate(raw)
        catalog = self.make_catalog(profile_lookup=lambda binding, original: wrong_process)
        with self.assertRaises(ProcessingPublicationError):
            catalog.register_planning_snapshot(checkpoint, (), self.auth)
        for phase in ("unregistered-phase", "stop", "stopped", profile.processes[self.original.kind].completion.phase):
            candidate = self.store.checkpoint("C1").model_copy(update={"phase": phase})
            self.store.save_checkpoint(candidate)
            with self.assertRaises(ProcessingPublicationError):
                self.catalog.register_planning_snapshot(candidate, (), self.auth)

    def test_missing_narrative_is_not_invented(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        self.original = make_request(case_id="C2", narrative=None)
        self.binding = make_binding(self.original)
        self.store.admit(self.binding, self.original, make_checkpoint(binding=self.binding))
        with self.assertRaises(ProcessingPublicationError) as missing:
            self.catalog.register_saved_narrative(self.binding, self.auth)
        self.assertEqual(missing.exception.code, "input_unavailable")

    def test_wrong_role_and_excess_usage_are_not_usable_outputs(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        from proofkey.journal import JournalFailure
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        output = ProposalOutput(kind="proposal", proposal=ActionProposal(operation="reschedule", stage="commit",
            arguments={}, evidence_refs=[]))
        with self.assertRaises(JournalFailure):
            self.save_output(identity, output, usage={"tokens": 3})
        self.assertIsNone(self.store.invocation("invoke-1")[1])
        self.save_output(identity, output)
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "output_invalid")

    def test_completed_historical_publication_does_not_require_current_generation(self):
        self.extraction()
        original_publication = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        newer = make_request(request_revision="v2")
        newer_binding = make_binding(newer, generation="G2", supersedes_generation="G1")
        self.store.admit(newer_binding, newer, make_checkpoint(binding=newer_binding, budget=self.checkpoint.budget))
        self.assertEqual(self.store.checkpoint("C1").binding, newer_binding)
        self.assertEqual(original_publication, self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth))

    def test_sticky_stop_denies_new_planning_but_saved_output_inspection_keeps_debt(self):
        from proofkey.contracts import StopState
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        checkpoint = self.planning()
        self.extraction()
        current = self.store.checkpoint("C1")
        stopped = current.model_copy(update={"stop": StopState(requested=True, requested_at=NOW, reason="local stop")})
        self.store.save_checkpoint(stopped)
        with self.assertRaises(ProcessingPublicationError):
            self.catalog.register_planning_snapshot(stopped, (), self.auth)
        before = self.store.checkpoint("C1")
        self.assertEqual(self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth).status, "completed")
        self.assertEqual(before, self.store.checkpoint("C1"))

    def test_ancestry_ceiling_and_unknown_audio_timing_remain_explicit(self):
        from proofkey.evidence.catalog import EvidenceAccessDenied
        audio, publication = self.transcript()
        strict = self.make_catalog(max_ancestry_records=1)
        with self.assertRaises(EvidenceAccessDenied):
            strict.read_original(publication.transcript_record().artifact_id, self.auth)
        identity = self.reserve([audio], "transcription", "untimed")
        self.catalog.seal_invocation_inputs(self.binding, "untimed", (audio.artifact_id,), self.auth)
        self.save_output(identity, TranscriptOutput(kind="transcript", text="No timing", segments=[]), "untimed")
        result = self.catalog.publish_processing_output(self.binding, "untimed", self.auth)
        path = self.catalog.root / "records" / (result.transcript_record().artifact_id + ".json")
        metadata = json.loads(path.read_bytes())["processing"]["identity"]
        self.assertEqual((metadata["timing"], metadata["segments"]), ("unknown", []))

    def test_decoder_unavailable_or_malformed_is_not_unknown_success(self):
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        path = self.folder / "unsupported.bin"
        path.write_bytes(b"not a supported format")
        record = self.catalog.register(path, "C1", "local-private", {"allowed_actors": ["U1"]})
        identity = self.reserve([record])
        self.catalog.seal_invocation_inputs(self.binding, "invoke-1", (record.artifact_id,), self.auth)
        self.save_output(identity, AssertionsOutput(kind="assertions", assertions=[self.assertion(record,
            locator=UnknownLocator(reason="unknown"))]))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        self.assertEqual(denied.exception.code, "input_unavailable")

    def test_companions_are_canonical_immutable_detached_and_not_authority(self):
        from dataclasses import FrozenInstanceError, replace
        from proofkey.evidence.processing_contracts import SavedOriginalScope, ProcessingCatalogBindings
        scope = self.scope(self.binding, self.original, self.auth, "provider_processing")
        with self.assertRaises(FrozenInstanceError):
            scope.policy_id = "forged"
        detached = scope.scope()
        detached["allowed_actors"].append("OTHER")
        self.assertEqual(scope.scope()["allowed_actors"], ["U1"])
        with self.assertRaises(ValueError):
            replace(scope, scope_bytes=json.dumps(scope.scope()).encode())
        with self.assertRaises(ValueError):
            replace(scope, scope_bytes=canonical({**scope.scope(), "extra": True}))
        with self.assertRaises(ValueError):
            replace(self.catalog._processing_bindings, max_inputs=True)
        with self.assertRaises(TypeError):
            ProcessingCatalogBindings(None, None, None, None)

    def test_actual_sigkill_after_reservation_before_seal_preserves_consumed_debt(self):
        self.interruption("reserved-before-seal")

    def test_actual_sigkill_before_publication_marker_reopens_exact_saved_output(self):
        self.interruption("before-marker")

    def interruption(self, boundary):
        import select
        import signal
        import subprocess
        import sys
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--crash-worker",
            str(self.folder), boundary], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            ready, _, _ = select.select([child.stdout], [], [], 5)
            self.assertTrue(ready, "Child did not reach finite boundary")
            modules = child.stdout.readline().strip()
            self.assertTrue(modules.startswith("CHILD_MODULES "), modules)
            CHILD_MODULE_PATHS.update(json.loads(modules[len("CHILD_MODULES "):]))
            self.assertEqual(child.stdout.readline().strip(), "BOUNDARY " + boundary)
            child.send_signal(signal.SIGKILL)
            output, errors = child.communicate(timeout=5)
            self.assertEqual(child.returncode, -signal.SIGKILL, (output, errors))
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)
        self.store.close()
        self.store = CaseStore(self.folder / "journal.sqlite")
        self.addCleanup(self.store.close)
        self.catalog = self.make_catalog()
        reservation, receipt = self.store.invocation("invoke-1")
        budget = self.store.checkpoint("C1").budget
        self.assertEqual(budget.role_allowances["extraction"].invocations, 1)
        self.assertEqual(budget.role_allowances["extraction"].cost, 1)
        self.assertEqual(budget.active_seconds, 10)
        from proofkey.evidence.processing_contracts import ProcessingPublicationError
        if boundary == "reserved-before-seal":
            self.assertIsNone(receipt)
            self.assertEqual(reservation.status, "consumed")
            with self.assertRaises(ProcessingPublicationError):
                self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
        else:
            self.assertEqual(reservation.status, "completed")
            self.assertEqual(list((self.catalog.root / "receipts").glob("output-marker-*")), [])
            self.assertEqual(len(list((self.catalog.root / "receipts").glob("output-control-*"))), 1)
            result = self.catalog.publish_processing_output(self.binding, "invoke-1", self.auth)
            self.assertEqual(result.status, "completed")
        self.assertEqual(budget, self.store.checkpoint("C1").budget)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == "--crash-worker":
        crash_worker(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
