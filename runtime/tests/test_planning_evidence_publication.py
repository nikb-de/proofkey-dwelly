"""Actual saved synthetic V2 publication; no model quality or dispatch authority."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave
from dataclasses import replace
from unittest.mock import patch

from proofkey.contracts import (AssertionsOutput, AuthorityObservation, BudgetLedger,
    EvidenceAssertion, ProcessingReceipt, ProcessorIdentity, ProposalOutput, RoleAllowance,
    TranscriptOutput, UnknownLocator)
from proofkey.evidence.catalog import EvidenceCatalog
from proofkey.evidence.processing_contracts import (PlanningEvidenceInputV2,
    ProcessingCatalogBindings, ProcessingPublicationError, SavedOriginalScope, canonical, digest)
from proofkey.identity import fingerprint
from proofkey.journal import CaseStore, JournalFailure
from proofkey.planner import BoundedPlanner
from proofkey.profiles import load_profile
from proofkey.providers.anthropic import AnthropicClient, ENDPOINT
from proofkey.providers.invocations import InvocationService, output_digest
from proofkey.providers.protocols import TransportResponse
from support import (DEADLINE, NOW, FakeClock, make_auth, make_binding,
    make_checkpoint, make_fixture_campaign, make_request)


PROMPT = "Synthetic saved publication planner"
USAGE = {"input_tokens": 100.0, "output_tokens": 32.0}


class PlanningEvidencePublicationTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            blocker = patch(target, side_effect=AssertionError("No external network authorized"))
            blocker.start()
            self.addCleanup(blocker.stop)
        temporary = tempfile.TemporaryDirectory(prefix="proofkey-v2-publication-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name).resolve()
        self.store = CaseStore(self.folder / "journal.sqlite")
        self.addCleanup(self.store.close)
        self.auth, self.clock = make_auth(), FakeClock()
        self.original = make_request(narrative="Box condition uncertain.\n")
        self.binding = make_binding(self.original)
        budget = BudgetLedger(case_id="C1", deadline=DEADLINE, role_allowances={
            "extraction": RoleAllowance(max_invocations=20, max_cost=20, usage_allowances={"tokens": 200}),
            "transcription": RoleAllowance(max_invocations=20, max_cost=20, usage_allowances={"tokens": 200}),
            "planning": RoleAllowance(max_invocations=20, max_cost=20,
                usage_allowances={"input_tokens": 2000, "output_tokens": 640})})
        self.store.admit(self.binding, self.original, make_checkpoint(binding=self.binding,
            phase="window_gate", next_gate="reschedule", budget=budget))
        self.revoked, self.saved_denied, self.services, self.requests = set(), set(), [], []
        self.profile = load_profile("flat-v1")
        self.catalog = self.make_catalog()
        self.observations = (AuthorityObservation(authority="delivery", fact="delivery.status",
            object_id="O1", value="scheduled", revision="v1", observed_at=NOW,
            evidence_ref="source-status"),)

    def original_lookup(self, binding):
        if self.store.find_request(binding.case_id, binding.request_id, binding.request_revision,
                binding.consent_revision, binding.fingerprint) != binding:
            raise ValueError("Exact saved original required")
        return self.store.original_request(binding.case_id, binding.generation)

    def access(self, auth, record, scope, purpose):
        return (auth == self.auth and record.case_id == "C1" and scope["allowed_actors"] == ("U1",)
            and scope.get("scope_id") not in self.revoked
            and not (scope.get("scope_id") == "saved-scope" and record.artifact_id in self.saved_denied))

    def scope(self, binding, original, auth, purpose):
        if (binding != self.binding or original != self.original or auth != self.auth
                or "saved-scope" in self.revoked or self.clock.now() >= DEADLINE):
            return None
        raw = dict(allowed_actors=["U1"], case_id="C1", object_id="O1",
            binding_hash=fingerprint(binding.model_dump(mode="json")),
            original_request_hash=fingerprint(original.model_dump(mode="json")), scope_id="saved-scope",
            policy_id="local-policy", authorization_reference="synthetic-proof",
            provenance="synthetic_host_registration", expires_at=DEADLINE.isoformat())
        return SavedOriginalScope(canonical(binding.model_dump(mode="json")), raw["original_request_hash"],
            "saved-scope", canonical(raw), "local-policy", "synthetic_host_registration", "synthetic-proof", DEADLINE)

    def make_catalog(self, **limits):
        return EvidenceCatalog(self.folder / "catalog", self.clock, allowed_input_roots=[self.folder],
            access_resolver=self.access, processing_bindings=ProcessingCatalogBindings(self.original_lookup,
                lambda b: self.store.checkpoint(b.case_id), self.store.invocation, self.scope,
                profile_lookup=lambda b, o: self.profile, **limits))

    def service(self, records, identifier, role="planning"):
        usage = USAGE if role == "planning" else {"tokens": 2.0}
        grant = make_fixture_campaign(role=role, input_hashes=[r.original_hash for r in records],
            campaign_id="synthetic-" + identifier, provider="anthropic" if role == "planning" else "injected-provider",
            endpoint=ENDPOINT if role == "planning" else "injected://role", max_usage=usage)
        self.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id="C1", generation="G1", role=role,
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash, input_hashes=grant.input_hashes,
            provider=grant.provider, model=grant.model, endpoint=grant.endpoint,
            prompt_hash=hashlib.sha256(PROMPT.encode()).hexdigest(), version="v1",
            profile_version="v1", process_version="v1", deadline=DEADLINE)
        service = InvocationService("C1", self.store, self.clock, grant, identity,
            worst_case_cost=1.0, invocation_id_factory=lambda: identifier)
        self.services.append(service)
        return service

    def save_output(self, records, identifier, role, output, status="completed"):
        service = self.service(records, identifier, role)
        def invoke():
            request = service.current_request
            self.catalog.seal_invocation_inputs(self.binding, identifier,
                tuple(r.artifact_id for r in records), self.auth)
            return ProcessingReceipt(invocation_id=identifier, role=role, provider=request.identity.provider,
                requested_model=request.identity.model, prompt_hash=request.identity.prompt_hash,
                version="v1", input_hashes=request.identity.input_hashes, mode="synthetic", status=status,
                latency_seconds=0, usage={"tokens": 1}, processed_at=NOW,
                output=output, output_hashes=[] if output is None else [output_digest(output)])
        return service.call(role, service.processor_identity.input_hashes, {"tokens": 2}, invoke)

    def extraction(self, records=None, identifier="extract-1", claim="Damaged"):
        records = records or (self.catalog.register_saved_narrative(self.binding, self.auth),)
        output = AssertionsOutput(kind="assertions", assertions=[] if claim is None else [EvidenceAssertion(
            artifact_id=records[0].artifact_id, content_hash=records[0].original_hash,
            lineage_hash=records[0].lineage_hash, claim=claim, locator=UnknownLocator(reason="not_measured"),
            uncertainty="conflicting", processing_receipt_id=identifier)])
        self.save_output(records, identifier, "extraction", output)
        return self.catalog.publish_processing_output(self.binding, identifier, self.auth)

    def saved_plan(self, identifiers=("extract-1",), *, v1=False):
        checkpoint = self.store.checkpoint("C1")
        record = (self.catalog.register_planning_snapshot(checkpoint, self.observations, self.auth) if v1 else
            self.catalog.register_planning_evidence_snapshot(checkpoint, self.observations, identifiers, self.auth))
        payload = self.catalog.read_original(record.artifact_id, self.auth)
        evidence = None if v1 else PlanningEvidenceInputV2.from_bytes(payload)
        service = self.service((record,), "plan-1")
        output = {"kind": "proposal", "proposal": {"operation": "reschedule", "stage": "commit",
            "arguments": {"slot": "S1"}, "evidence_refs": ["source-status"]}}
        def transport(request):
            self.requests.append(request)
            return TransportResponse(200, canonical({"id": "msg-synthetic", "type": "message",
                "role": "assistant", "model": "synthetic-observed",
                "content": [{"type": "text", "text": json.dumps(output)}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 7, "output_tokens": 3}}))
        client = AnthropicClient(transport, system_prompt=PROMPT, max_tokens=32)
        def invoke():
            self.catalog.seal_invocation_inputs(self.binding, "plan-1", (record.artifact_id,), self.auth)
            context = service.processing_context(self.catalog, self.auth, input_records=(record,))
            return (client.propose(checkpoint, self.observations, context) if v1 else
                client.propose_with_evidence(evidence, context))
        receipt = service.call("planning", [record.original_hash], USAGE, invoke)
        if not v1:
            validator = BoundedPlanner(lambda *a: self.fail("historical validator entered processor"), service,
                allowed_steps={"reschedule": {"commit": {"slot"}}}, usage_ceiling=USAGE)
            self.assertIs(validator.validate_evidence_receipt(receipt, evidence), receipt)
        return record, evidence, receipt

    def state(self):
        return (self.store.checkpoint("C1"), self.store.processing_attempts(self.binding),
            tuple(self.store.campaign_usage(s.campaign.permit_hash) for s in self.services),
            self.store.intents("C1"), len(self.requests))

    def files(self):
        return {str(p.relative_to(self.catalog.root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.catalog.root.rglob("*") if p.is_file()}

    def publish(self):
        return self.catalog.publish_processing_output(self.binding, "plan-1", self.auth)

    def test_actual_saved_v2_client_output_publishes_exact_private_proposal(self):
        # Break: the V1-only format branch denies an otherwise lawful durable V2 output.
        self.extraction()
        record, evidence, receipt = self.saved_plan()
        self.assertNotEqual(self.store.checkpoint("C1"), evidence.checkpoint())
        before = self.state()
        publication, denial = None, None
        try:
            publication = self.publish()
        except ProcessingPublicationError as exc:
            denial = exc.code
        self.assertIsNone(denial, "Lawful actual saved V2 client output must publish")
        self.assertEqual(self.state(), before)
        self.assertEqual(publication.input_records(), (record,))
        self.assertEqual(publication.assertion_refs, ())
        self.assertEqual(publication.assertion_bytes, ())
        self.assertIsNone(publication.transcript_record_bytes)
        self.assertTrue(publication.proposal_receipt_ref.startswith("private-proposal-"))
        proposal = json.loads((self.catalog.root / "receipts" / (publication.proposal_receipt_ref + ".json")).read_bytes())
        seal = self.catalog._processing_path("inputs", self.binding, "plan-1").read_bytes()
        self.assertEqual(proposal, {"receipt": receipt.model_dump(mode="json"), "input_envelope_hash": digest(seal)})
        marker = json.loads(publication.marker_bytes)
        self.assertEqual(marker["input_records"], [record.model_dump(mode="json")])
        self.assertEqual((marker["mode"], marker["status"], marker["assertions"]), ("synthetic", "completed", []))
        self.assertEqual(publication.marker_hash, digest(publication.marker_bytes))
        self.assertEqual(self.catalog.read_original(record.artifact_id, self.auth), evidence.envelope_bytes)

    def test_v1_output_keeps_exact_snapshot_proposal_marker_bytes(self):
        # Break: admitting V2 changes the existing V1 serialization or saved proposal domain.
        record, _, receipt = self.saved_plan(v1=True)
        snapshot = canonical({"checkpoint": json.loads(self.catalog.read_original(record.artifact_id, self.auth))["checkpoint"],
            "observations": [o.model_dump(mode="json") for o in self.observations]})
        self.assertEqual(self.catalog.read_original(record.artifact_id, self.auth), snapshot)
        before = self.state()
        publication = self.publish()
        seal_hash = digest(self.catalog._processing_path("inputs", self.binding, "plan-1").read_bytes())
        receipt_hash = fingerprint(receipt.model_dump(mode="json"))
        proposal_ref = "private-proposal-" + digest(canonical({"domain": "proofkey-saved-proposal-v1",
            "receipt_hash": receipt_hash, "input_envelope_hash": seal_hash}))
        self.assertEqual(publication.proposal_receipt_ref, proposal_ref)
        self.assertEqual((self.catalog.root / "receipts" / (proposal_ref + ".json")).read_bytes(),
            canonical({"receipt": receipt.model_dump(mode="json"), "input_envelope_hash": seal_hash}))
        control = self.catalog._processing_path("output-control", self.binding, "plan-1").read_bytes()
        self.assertEqual(publication.marker_bytes, canonical({"binding": self.binding.model_dump(mode="json"),
            "invocation_id": "plan-1", "receipt_hash": receipt_hash, "output_hashes": receipt.output_hashes,
            "input_records": [record.model_dump(mode="json")], "assertions": [], "assertion_refs": [],
            "transcript_record": None, "proposal_receipt_ref": proposal_ref, "control_hash": digest(control),
            "status": "completed", "mode": "synthetic"}))
        self.assertEqual(self.state(), before)

    def text_record(self, name="parent", payload=b"Same uncertain box.\n"):
        path = self.folder / (name + ".txt")
        path.write_bytes(payload)
        return self.catalog.register(path, "C1", "synthetic-original",
            {"allowed_actors": ["U1"], "scope_id": name})

    def audio_transcript(self):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(100)
            stream.writeframes(b"\0\0" * 100)
        path = self.folder / "audio.wav"
        path.write_bytes(buffer.getvalue())
        audio = self.catalog.register(path, "C1", "synthetic-audio",
            {"allowed_actors": ["U1"], "scope_id": "audio-parent"})
        self.save_output((audio,), "transcribe-1", "transcription",
            TranscriptOutput(kind="transcript", text="Box condition uncertain.", segments=[]))
        transcript = self.catalog.publish_processing_output(self.binding, "transcribe-1", self.auth).transcript_record()
        return audio, transcript

    def test_ordered_equal_content_and_empty_publication_survive_without_new_debt(self):
        # Break: hash deduplication or nonempty filtering drops a real input/publication.
        first, second = self.text_record("first"), self.text_record("second")
        self.assertNotEqual(first.artifact_id, second.artifact_id)
        self.assertEqual(first.original_hash, second.original_hash)
        empty = self.extraction((second,), "extract-empty", None)
        rich = self.extraction((first,), "extract-rich", "Conflicting original condition")
        record, evidence, _ = self.saved_plan(("extract-empty", "extract-rich"))
        before, files = self.state(), self.files()
        publication = self.publish()
        self.assertEqual(self.state(), before)
        self.assertEqual(evidence.extraction_publications(), (empty, rich))
        metadata = json.loads((self.catalog.root / "records" / (record.artifact_id + ".json")).read_bytes())["processing"]
        self.assertEqual(metadata["parents"], [second.model_dump(mode="json"), first.model_dump(mode="json")])
        self.assertEqual(record.parent_hashes, [second.original_hash, first.original_hash])
        self.assertEqual(publication.input_records(), (record,))
        self.assertEqual(rich.assertions()[0].uncertainty, "conflicting")
        self.assertEqual(rich.assertions()[0].locator.kind, "unknown")
        self.assertEqual(evidence.observation_bytes, tuple(canonical(o.model_dump(mode="json")) for o in self.observations))
        for path, saved in files.items():
            self.assertEqual(self.files()[path], saved)

    def test_transcript_audio_ancestry_survives_planning_publication(self):
        # Break: planning publication loses the original audio of its extracted transcript.
        audio, transcript = self.audio_transcript()
        extraction = self.extraction((transcript,))
        record, evidence, _ = self.saved_plan()
        before = self.state()
        self.assertEqual(self.publish().input_records(), (record,))
        self.assertEqual(extraction.input_records(), (transcript,))
        self.assertEqual(transcript.parent_hashes, [audio.original_hash])
        self.assertEqual(record.parent_hashes, [transcript.original_hash])
        self.assertEqual(evidence.extraction_publications(), (extraction,))
        self.assertEqual(self.state(), before)

    def test_repeat_and_reopened_catalog_preserve_all_bytes_mtimes_and_debt(self):
        # Break: repeat/reopen rewrites history or invokes another provider.
        self.extraction()
        self.saved_plan()
        publication = self.publish()
        before, files = self.state(), self.files()
        self.assertEqual(self.publish(), publication)
        self.catalog = self.make_catalog()
        self.assertEqual(self.publish(), publication)
        self.assertEqual(self.files(), files)
        self.assertEqual(self.state(), before)

    def test_stopped_historical_output_is_inspectable_but_new_entry_is_denied(self):
        # Break: historical inspection either erases saved output or grants fresh stopped entry.
        self.extraction()
        self.saved_plan()
        self.store.set_stop("C1", "G1")
        before = self.state()
        self.assertTrue(before[0].stop.requested)
        self.assertIsNotNone(self.publish().proposal_receipt_ref)
        with self.assertRaises(JournalFailure):
            self.services[-1].call("planning", self.services[-1].processor_identity.input_hashes,
                USAGE, lambda: self.fail("stopped provider entered"))
        self.assertEqual(self.state(), before)

    def test_successor_generation_preserves_currently_authorized_original_output(self):
        # Break: publisher mistakes the successor checkpoint for the saved pre-debit checkpoint.
        self.extraction()
        self.saved_plan()
        original = make_request(request_id="REQ2", request_revision="v2", narrative="New window request")
        successor = make_binding(original, generation="G2", supersedes_generation="G1")
        self.store.admit(successor, original, self.store.checkpoint("C1").model_copy(update={"binding": successor}))
        before = self.state()
        self.assertEqual(before[0].binding.generation, "G2")
        self.assertIsNotNone(self.publish().proposal_receipt_ref)
        with self.assertRaises(JournalFailure):
            self.services[-1].call("planning", self.services[-1].processor_identity.input_hashes,
                USAGE, lambda: self.fail("superseded provider entered"))
        self.assertEqual(self.state(), before)

    def marker_hook(self, change):
        old = self.catalog._store
        marker = self.catalog._processing_path("output-marker", self.binding, "plan-1")
        fired = []
        def write_then_change(path, payload):
            result = old(path, payload)
            if path == marker and not fired:
                fired.append(path.read_bytes())
                change()
            return result
        self.catalog._store = write_then_change
        self.addCleanup(setattr, self.catalog, "_store", old)
        return fired

    def deny_current(self, kind, after):
        # Break: a revoked original/direct/ancestor policy or expired lease survives the return fence.
        audio, parent = self.audio_transcript() if kind.startswith("audio") else (None, self.text_record())
        self.extraction((parent,))
        self.saved_plan()
        before, files = self.state(), self.files()
        def change():
            if kind == "direct":
                self.revoked.add("parent")
            elif kind == "audio-acl":
                self.revoked.add("audio-parent")
            elif kind == "audio-saved":
                self.saved_denied.add(audio.artifact_id)
            elif kind == "direct-saved":
                self.saved_denied.add(parent.artifact_id)
            elif kind == "original":
                self.revoked.add("saved-scope")
            elif kind == "expiry":
                self.clock.advance(7200)
            else:
                self.fail("Unknown fault")
        fired = self.marker_hook(change) if after else []
        if not after:
            change()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(self.state(), before)
        if after:
            self.assertEqual(len(fired), 1)
            marker = self.catalog._processing_path("output-marker", self.binding, "plan-1")
            self.assertEqual(marker.read_bytes(), fired[0])
            self.assertTrue(json.loads(fired[0])["proposal_receipt_ref"])
        else:
            self.assertEqual(self.files(), files)

    def test_direct_acl_denied_before_publication(self):
        self.deny_current("direct", False)

    def test_direct_acl_denied_after_actual_marker_write(self):
        self.deny_current("direct", True)

    def test_audio_ancestor_acl_denied_before_publication(self):
        self.deny_current("audio-acl", False)

    def test_audio_ancestor_acl_denied_after_actual_marker_write(self):
        self.deny_current("audio-acl", True)

    def test_audio_ancestor_saved_scope_denied_before_publication(self):
        self.deny_current("audio-saved", False)

    def test_audio_ancestor_saved_scope_denied_after_actual_marker_write(self):
        self.deny_current("audio-saved", True)

    def test_direct_parent_saved_scope_denied_before_publication(self):
        self.deny_current("direct-saved", False)

    def test_direct_parent_saved_scope_denied_after_actual_marker_write(self):
        self.deny_current("direct-saved", True)

    def test_original_scope_denied_before_publication(self):
        self.deny_current("original", False)

    def test_original_scope_denied_after_actual_marker_write(self):
        self.deny_current("original", True)

    def test_saved_scope_expiry_denied_before_publication(self):
        self.deny_current("expiry", False)

    def test_saved_scope_expiry_denied_after_actual_marker_write(self):
        self.deny_current("expiry", True)

    def test_wrong_current_proof_cannot_publish_saved_output(self):
        # Break: durable synthetic receipt replaces current original proof.
        self.extraction()
        self.saved_plan()
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.catalog.publish_processing_output(self.binding, "plan-1", make_auth(proof_reference="wrong-proof"))
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def extraction_fault(self, kind, after):
        # Break: saved envelope's marker hash substitutes for exact current durable extraction.
        self.extraction()
        self.saved_plan()
        before = self.state()
        changed = []
        def change():
            if kind == "receipt":
                receipt = self.store.invocation("extract-1")[1].model_dump(mode="json")
                receipt["latency_seconds"] = 0.125
                self.store._db.execute("UPDATE invocations SET receipt_json=? WHERE invocation_id=?",
                    (json.dumps(receipt), "extract-1"))
            else:
                path = self.catalog._processing_path("output-" + kind, self.binding, "extract-1")
                path.write_bytes(b"corrupt retained extraction " + kind.encode())
            changed.append(self.state())
        fired = self.marker_hook(change) if after else []
        if not after:
            change()
        fault_files = self.files()
        with self.assertRaises(ProcessingPublicationError):
            self.publish()
        actual = self.state()
        # Receipt fault deliberately changes history; publication changes no checkpoint/debt/entries/effects.
        self.assertEqual((actual[0], actual[2:]), (before[0], before[2:]))
        self.assertEqual(actual, changed[0])
        if after:
            self.assertEqual(len(fired), 1)
            self.assertEqual(self.catalog._processing_path("output-marker", self.binding, "plan-1").read_bytes(), fired[0])
        else:
            self.assertEqual(self.files(), fault_files)

    def test_changed_saved_extraction_receipt_denied_before_publication(self):
        self.extraction_fault("receipt", False)

    def test_changed_saved_extraction_receipt_denied_after_actual_marker_write(self):
        self.extraction_fault("receipt", True)

    def test_corrupt_extraction_marker_denied_before_publication(self):
        self.extraction_fault("marker", False)

    def test_corrupt_extraction_marker_denied_after_actual_marker_write(self):
        self.extraction_fault("marker", True)

    def test_corrupt_extraction_control_denied_before_publication(self):
        self.extraction_fault("control", False)

    def test_corrupt_extraction_control_denied_after_actual_marker_write(self):
        self.extraction_fault("control", True)

    def test_final_scope_expiry_during_extraction_reresolution_denies_return(self):
        # Break: publisher checks the scope only before a lengthy final lineage re-resolution.
        self.extraction()
        self.saved_plan()
        before = self.state()
        fired = self.marker_hook(lambda: None)
        old = self.catalog._processing_bindings.invocation_lookup
        def lookup(identifier):
            result = old(identifier)
            if fired and identifier == "extract-1":
                self.clock.advance(7200)
            return result
        with patch.object(self.catalog, "_processing_bindings",
                replace(self.catalog._processing_bindings, invocation_lookup=lookup)):
            with self.assertRaises(ProcessingPublicationError) as denied:
                self.publish()
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(len(fired), 1)
        self.assertEqual(self.state(), before)

    def manual_plan(self, records, status="completed", *, save=True):
        """Public durable malformed/incomplete-input controls cannot enter the strict V2 client."""
        service = self.service(records, "plan-1")
        def invoke():
            request = service.current_request
            self.catalog.seal_invocation_inputs(self.binding, "plan-1",
                tuple(r.artifact_id for r in records), self.auth)
            output = ProposalOutput(kind="proposal", proposal={"operation": "reschedule", "stage": "commit",
                "arguments": {"slot": "S1"}, "evidence_refs": []}) if status == "completed" else None
            return ProcessingReceipt(invocation_id="plan-1", role="planning", provider=request.identity.provider,
                requested_model=request.identity.model, prompt_hash=request.identity.prompt_hash, version="v1",
                input_hashes=request.identity.input_hashes, mode="synthetic", status=status, latency_seconds=0,
                usage={"input_tokens": 7, "output_tokens": 3}, processed_at=NOW, output=output,
                output_hashes=[] if output is None else [output_digest(output)])
        if save:
            return service.call("planning", service.processor_identity.input_hashes, USAGE, invoke)
        self.store.reserve_invocation(service.make_invocation_request("planning",
            service.processor_identity.input_hashes, USAGE), NOW)
        self.catalog.seal_invocation_inputs(self.binding, "plan-1", tuple(r.artifact_id for r in records), self.auth)

    def incomplete_plan(self, status, save=True):
        # Break: noncomplete consumed history becomes a usable proposal.
        self.extraction()
        record = self.catalog.register_planning_evidence_snapshot(self.store.checkpoint("C1"),
            self.observations, ("extract-1",), self.auth)
        self.manual_plan((record,), status, save=save)
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "not_complete")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_failed_planning_receipt_is_not_published(self):
        self.incomplete_plan("failed")

    def test_unknown_planning_receipt_is_not_published(self):
        self.incomplete_plan("outcome_unknown")

    def test_consumed_unsaved_planning_attempt_is_not_published(self):
        self.incomplete_plan("completed", save=False)

    def test_replay_receipt_cannot_replace_actual_saved_planning_pair(self):
        # Break: replay mode is accepted merely because its output hashes match.
        self.extraction()
        self.saved_plan()
        receipt = self.store.invocation("plan-1")[1].model_dump(mode="json")
        receipt["mode"] = "replay"
        self.store._db.execute("UPDATE invocations SET receipt_json=? WHERE invocation_id=?",
            (json.dumps(receipt), "plan-1"))
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "not_complete")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_multiple_reserved_inputs_cannot_alias_single_v2_envelope(self):
        # Break: accepting an extra reservation input weakens the exact one-input V2 contract.
        self.extraction()
        record = self.catalog.register_planning_evidence_snapshot(self.store.checkpoint("C1"),
            self.observations, ("extract-1",), self.auth)
        self.manual_plan((record, self.text_record()))
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "output_invalid")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_ordinary_json_upload_cannot_alias_saved_v2_processing_identity(self):
        # Break: a canonical hash and caller-selected source label create a trusted saved envelope.
        self.extraction()
        record = self.catalog.register_planning_evidence_snapshot(self.store.checkpoint("C1"),
            self.observations, ("extract-1",), self.auth)
        path = self.folder / "alias.json"
        path.write_bytes(self.catalog.read_original(record.artifact_id, self.auth))
        alias = self.catalog.register(path, "C1", "saved-planning-evidence-v2",
            {"allowed_actors": ["U1"], "scope_id": "parent"})
        before = self.store.checkpoint("C1")
        service = self.service((alias,), "plan-1")
        with self.assertRaises(ProcessingPublicationError):
            self.store.reserve_invocation(service.make_invocation_request("planning", [alias.original_hash], USAGE), NOW)
            self.catalog.seal_invocation_inputs(self.binding, "plan-1", (alias.artifact_id,), self.auth)
        after = self.store.checkpoint("C1")
        self.assertEqual(after.budget.planner_calls, before.budget.planner_calls + 1)
        self.assertEqual(self.store.invocation("plan-1")[0].status, "consumed")
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "not_complete")

    def corrupt_planning_file(self, kind):
        # Break: conflicting private bytes are silently repaired, overwritten or returned as usable.
        self.extraction()
        record, _, _ = self.saved_plan()
        if kind in {"proposal", "marker", "control"}:
            publication = self.publish()
            path = (self.catalog.root / "receipts" / (publication.proposal_receipt_ref + ".json") if kind == "proposal"
                else self.catalog._processing_path("output-" + kind, self.binding, "plan-1"))
        elif kind == "inputs":
            path = self.catalog._processing_path("inputs", self.binding, "plan-1")
        elif kind == "bytes":
            path = self.catalog.root / "objects" / record.original_hash
        elif kind == "metadata":
            path = self.catalog.root / "records" / (record.artifact_id + ".json")
        else:
            self.fail("Unknown corruption")
        if kind == "metadata":
            value = json.loads(path.read_bytes())
            value["processing"]["identity"]["extra"] = "forged"
            path.write_bytes(canonical(value))
        else:
            path.write_bytes(b"retained conflicting " + kind.encode())
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError):
            self.publish()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_corrupt_planning_proposal_is_retained_without_repair(self):
        self.corrupt_planning_file("proposal")

    def test_corrupt_planning_marker_is_retained_without_repair(self):
        self.corrupt_planning_file("marker")

    def test_corrupt_planning_control_is_retained_without_repair(self):
        self.corrupt_planning_file("control")

    def test_corrupt_planning_input_seal_is_retained_without_repair(self):
        self.corrupt_planning_file("inputs")

    def test_corrupt_v2_original_bytes_are_retained_without_repair(self):
        self.corrupt_planning_file("bytes")

    def test_extra_v2_control_identity_key_is_denied_without_repair(self):
        self.corrupt_planning_file("metadata")

    def test_changed_input_record_parents_are_denied_without_repair(self):
        # Break: recorded hash-only parent lineage accepts a substituted full input identity.
        first, second = self.text_record("first"), self.text_record("second")
        self.extraction((first,))
        record, _, _ = self.saved_plan()
        path = self.catalog.root / "records" / (record.artifact_id + ".json")
        value = json.loads(path.read_bytes())
        value["processing"]["parents"] = [second.model_dump(mode="json")]
        self.assertEqual(first.original_hash, second.original_hash)
        path.write_bytes(canonical(value))
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError):
            self.publish()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_changed_saved_extraction_status_denies_without_refund(self):
        # Break: a formerly complete extraction's old envelope remains usable after durable failure.
        self.extraction()
        self.saved_plan()
        attempt, receipt = self.store.invocation("extract-1")
        failed = receipt.model_copy(update={"status": "failed", "output": None, "output_hashes": []})
        failed_attempt = attempt.model_copy(update={"status": "failed"})
        self.store._db.execute("UPDATE invocations SET state=?,reservation_json=?,receipt_json=? WHERE invocation_id=?",
            ("failed", failed_attempt.model_dump_json(), failed.model_dump_json(), "extract-1"))
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "not_complete")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_lower_current_publication_ceiling_denies_without_truncation(self):
        # Break: publication truncates a saved envelope to fit a stricter current byte ceiling.
        self.extraction()
        self.saved_plan()
        before, files = self.state(), self.files()
        self.catalog = self.make_catalog(max_publication_bytes=1024)
        with self.assertRaises(ProcessingPublicationError):
            self.publish()
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_source_mime_kind_and_binding_substitutions_deny_saved_v2(self):
        # Break: trusting a source/kind alias or weakened binding instead of the sealed record.
        self.extraction()
        record, _, _ = self.saved_plan()
        path = self.catalog.root / "records" / (record.artifact_id + ".json")
        original_bytes = path.read_bytes()
        before = self.state()
        for name in ("source", "mime", "kind", "binding", "checkpoint-hash", "missing-key", "marker-hash"):
            with self.subTest(fault=name):
                value = json.loads(original_bytes)
                if name == "source":
                    value["record"]["source"] = "saved-planning-snapshot-v1"
                elif name == "mime":
                    value["record"]["mime_type"] = "text/plain"
                elif name == "kind":
                    value["processing"]["identity"]["kind"] = "planning_snapshot_v1"
                elif name == "binding":
                    value["processing"]["binding"]["request_id"] = "foreign-request"
                elif name == "checkpoint-hash":
                    value["processing"]["identity"]["checkpoint_hash"] = "0" * 64
                elif name == "missing-key":
                    del value["processing"]["identity"]["extraction_marker_hashes"]
                else:
                    value["processing"]["identity"]["extraction_marker_hashes"] = ["0" * 64]
                path.write_bytes(canonical(value))
                files = self.files()
                with self.assertRaises(ProcessingPublicationError):
                    self.publish()
                self.assertEqual(self.state(), before)
                self.assertEqual(self.files(), files)
        path.write_bytes(original_bytes)

    def test_unknown_source_canonical_json_is_not_a_saved_planning_input(self):
        # Break: arbitrary JSON with V2-shaped text reaches the proposal publisher as a trusted input.
        self.extraction()
        record = self.catalog.register_planning_evidence_snapshot(self.store.checkpoint("C1"),
            self.observations, ("extract-1",), self.auth)
        path = self.folder / "untrusted.json"
        path.write_bytes(self.catalog.read_original(record.artifact_id, self.auth))
        untrusted = self.catalog.register(path, "C1", "unknown-source", {"allowed_actors": ["U1"], "scope_id": "parent"})
        self.manual_plan((untrusted,))
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "output_invalid")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_changed_extraction_unknown_state_denies_without_refund(self):
        # Break: unknown extraction history retains authority from a former completed marker.
        self.extraction()
        self.saved_plan()
        attempt, receipt = self.store.invocation("extract-1")
        unknown = receipt.model_copy(update={"status": "outcome_unknown", "output": None, "output_hashes": []})
        unknown_attempt = attempt.model_copy(update={"status": "outcome_unknown"})
        self.store._db.execute("UPDATE invocations SET state=?,reservation_json=?,receipt_json=? WHERE invocation_id=?",
            ("outcome_unknown", unknown_attempt.model_dump_json(), unknown.model_dump_json(), "extract-1"))
        before, files = self.state(), self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "not_complete")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.files(), files)

    def test_changed_foreign_extraction_identity_denies_after_actual_marker_write(self):
        # Break: an embedded publication is trusted after its durable identity has become foreign.
        self.extraction()
        self.saved_plan()
        before, files = self.state(), self.files()
        def change():
            attempt, _ = self.store.invocation("extract-1")
            value = attempt.model_dump(mode="json")
            value["identity"]["generation"] = "G2"
            self.store._db.execute("UPDATE invocations SET reservation_json=? WHERE invocation_id=?",
                (json.dumps(value), "extract-1"))
        fired = self.marker_hook(change)
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.publish()
        self.assertEqual(denied.exception.code, "identity_mismatch")
        self.assertEqual(len(fired), 1)
        self.assertEqual(self.store.checkpoint("C1"), before[0])
        self.assertEqual(tuple(self.store.campaign_usage(s.campaign.permit_hash) for s in self.services), before[2])
        self.assertEqual(self.store.intents("C1"), ())
        self.assertEqual(len(self.requests), 1)
        for path, saved in files.items():
            self.assertEqual(self.files()[path], saved)
