"""Exact saved synthetic extraction evidence; no provider entry or authority grant."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from proofkey.contracts import (AssertionsOutput, AuthorityObservation, BudgetLedger,
    EvidenceAssertion, InvocationRequest, ProcessingReceipt, ProcessorIdentity, RoleAllowance,
    TranscriptOutput, UnknownLocator)
from proofkey.evidence.catalog import EvidenceCatalog
from proofkey.evidence.processing_contracts import (ProcessingCatalogBindings,
    ProcessingPublicationError, SavedOriginalScope)
from proofkey.identity import fingerprint
from proofkey.journal import CaseStore
from proofkey.profiles import load_profile
from support import (DEADLINE, NOW, FakeClock, make_auth, make_binding,
    make_checkpoint, make_fixture_campaign, make_request)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")


class PlanningEvidenceCatalogTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name).resolve()
        self.store = CaseStore(self.folder / "journal.sqlite")
        self.addCleanup(self.store.close)
        self.auth, self.clock = make_auth(), FakeClock()
        self.original = make_request(narrative="  Box damaged.\n")
        self.binding = make_binding(self.original)
        self.store.admit(self.binding, self.original, make_checkpoint(binding=self.binding,
            phase="window_gate", next_gate="reschedule", budget=BudgetLedger(case_id="C1",
                deadline=DEADLINE, role_allowances={r: RoleAllowance(max_invocations=20,
                    max_cost=20, usage_allowances={"tokens": 200})
                    for r in ("extraction", "transcription", "planning")})))
        self.revoked = set()
        self.saved_denied_records = set()
        self.profile = load_profile("flat-v1")
        self.catalog = self.make_catalog()
        self.observations = (AuthorityObservation(authority="delivery", fact="delivery.status",
            object_id="O1", value="scheduled", revision="v1", observed_at=NOW,
            evidence_ref="source-status"),)

    def access(self, auth, record, scope, purpose):
        return (auth == self.auth and record.case_id == "C1"
            and scope["allowed_actors"] == ("U1",) and scope.get("scope_id") not in self.revoked
            and not (scope.get("scope_id") == "saved-scope"
                and record.artifact_id in self.saved_denied_records))

    def scope(self, binding, original, auth, purpose):
        if (binding != self.binding or original != self.original or auth != self.auth
                or "saved-scope" in self.revoked or self.clock.now() >= DEADLINE):
            return None
        raw = dict(allowed_actors=["U1"], case_id="C1", object_id="O1",
            binding_hash=fingerprint(binding.model_dump(mode="json")),
            original_request_hash=fingerprint(original.model_dump(mode="json")), scope_id="saved-scope",
            policy_id="local-policy", authorization_reference="local-proof",
            provenance="synthetic_host_registration", expires_at=DEADLINE.isoformat())
        return SavedOriginalScope(encoded(binding.model_dump(mode="json")), raw["original_request_hash"],
            "saved-scope", encoded(raw), "local-policy", "synthetic_host_registration", "local-proof", DEADLINE)

    def make_catalog(self, **limits):
        def original(binding):
            if self.store.find_request(binding.case_id, binding.request_id, binding.request_revision,
                    binding.consent_revision, binding.fingerprint) != binding:
                raise ValueError("Exact saved original required")
            return self.store.original_request(binding.case_id, binding.generation)
        bindings = ProcessingCatalogBindings(original, lambda b: self.store.checkpoint(b.case_id),
            self.store.invocation, self.scope, profile_lookup=lambda b, o: self.profile, **limits)
        return EvidenceCatalog(self.folder / "catalog", self.clock, allowed_input_roots=[self.folder],
            access_resolver=self.access, processing_bindings=bindings)

    def reserve(self, records, invocation_id="extract-1", role="extraction"):
        grant = make_fixture_campaign(role=role, input_hashes=[r.original_hash for r in records],
            campaign_id="campaign-" + invocation_id)
        self.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id="C1", generation=self.binding.generation, role=role,
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash, input_hashes=grant.input_hashes,
            provider=grant.provider, model=grant.model, endpoint=grant.endpoint, prompt_hash="2" * 64,
            version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
        self.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id=invocation_id,
            requested_usage={"tokens": 2}, worst_case_cost=1), NOW)
        self.catalog.seal_invocation_inputs(self.binding, invocation_id,
            tuple(r.artifact_id for r in records), self.auth)
        return identity

    def save(self, identity, output, invocation_id="extract-1", **changes):
        raw = dict(invocation_id=invocation_id, role=identity.role, provider=identity.provider,
            requested_model=identity.model, prompt_hash=identity.prompt_hash, version="v1",
            input_hashes=identity.input_hashes, mode="synthetic", status="completed", latency_seconds=0,
            usage={"tokens": 1}, processed_at=NOW, output=output,
            output_hashes=[hashlib.sha256(output.model_dump_json().encode()).hexdigest()])
        receipt = ProcessingReceipt.model_validate({**raw, **changes})
        self.store.record_processing(invocation_id, receipt)
        return receipt

    def extraction(self, records=None, invocation_id="extract-1", claims=("Damaged",)):
        records = records or (self.catalog.register_saved_narrative(self.binding, self.auth),)
        identity = self.reserve(records, invocation_id)
        assertions = [EvidenceAssertion(artifact_id=records[i % len(records)].artifact_id,
            content_hash=records[i % len(records)].original_hash,
            lineage_hash=records[i % len(records)].lineage_hash,
            locator=UnknownLocator(reason="not_measured"), uncertainty="conflicting",
            processing_receipt_id=invocation_id, claim=claim) for i, claim in enumerate(claims)]
        receipt = self.save(identity, AssertionsOutput(kind="assertions", assertions=assertions), invocation_id)
        return tuple(records), receipt

    def register_evidence(self, ids=("extract-1",), checkpoint=None, observations=None):
        return self.catalog.register_planning_evidence_snapshot(
            checkpoint or self.store.checkpoint("C1"),
            self.observations if observations is None else observations, ids, self.auth)

    def files(self):
        return {str(p.relative_to(self.catalog.root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.catalog.root.rglob("*") if p.is_file()}

    def test_actual_saved_extraction_is_present_in_separate_canonical_namespace(self):
        # Break: unavailable/legacy snapshot or hash-only evidence drops actual claims/lineage.
        records, receipt = self.extraction(claims=("Damaged", "Intact"))
        checkpoint = self.store.checkpoint("C1")
        failure = None
        try:
            record = self.register_evidence()
        except ProcessingPublicationError as exc:
            failure = exc.code
        self.assertIsNone(failure, "Completed saved extraction must produce usable V2 input")
        payload = self.catalog.read_original(record.artifact_id, self.auth)
        envelope = json.loads(payload)
        self.assertEqual(set(envelope), {"version", "checkpoint", "authority_observations", "extraction_publications"})
        self.assertEqual(envelope["version"], "planning-evidence-input-v2")
        self.assertEqual(envelope["checkpoint"], checkpoint.model_dump(mode="json"))
        self.assertEqual(envelope["authority_observations"], [self.observations[0].model_dump(mode="json")])
        publication = envelope["extraction_publications"][0]
        self.assertEqual([a["claim"] for a in publication["assertion_bytes"]], ["Damaged", "Intact"])
        self.assertEqual([a["uncertainty"] for a in publication["assertion_bytes"]], ["conflicting"] * 2)
        self.assertEqual(publication["assertion_bytes"][0]["locator"], {"kind": "unknown", "reason": "not_measured"})
        self.assertEqual(publication["receipt_hash"], fingerprint(receipt.model_dump(mode="json")))
        self.assertEqual(publication["input_record_bytes"], [records[0].model_dump(mode="json")])
        self.assertEqual(publication["marker_hash"], hashlib.sha256(encoded(publication["marker_bytes"])).hexdigest())
        self.assertIsNone(publication["transcript_record_bytes"])
        self.assertIsNone(publication["proposal_receipt_ref"])
        self.assertEqual(record.source, "saved-planning-evidence-v2")
        self.assertEqual(record.parent_hashes, [records[0].original_hash])
        self.assertEqual(record.original_hash, hashlib.sha256(payload).hexdigest())
        self.assertEqual(payload, encoded(envelope))

    def test_tightened_aggregate_assertion_limit_denies_before_envelope_bytes(self):
        # Break: enforcing only per-publication caps allows the V2 aggregate to exceed host limits.
        self.catalog = self.make_catalog(max_output_items=2)
        self.extraction(claims=("A", "B"))
        self.extraction(invocation_id="extract-2", claims=("C", "D"))
        self.catalog.publish_processing_output(self.binding, "extract-1", self.auth)
        self.catalog.publish_processing_output(self.binding, "extract-2", self.auth)
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence(("extract-1", "extract-2"))
        self.assertEqual(denied.exception.code, "output_invalid")
        self.assertEqual(self.files(), before)

    def test_mixed_empty_and_nonempty_extractions_preserve_both_actual_publications(self):
        # Break: an unsolicited per-publication restriction drops useful exact aggregate evidence.
        empty_records, _ = self.extraction(claims=())
        path = self.folder / "rich.txt"
        path.write_bytes(b"Damage reported")
        rich = self.catalog.register(path, "C1", "synthetic-text",
            {"allowed_actors": ["U1"], "scope_id": "rich-parent"})
        self.extraction((rich,), "extract-2")
        failure = None
        try:
            record = self.register_evidence(("extract-1", "extract-2"))
        except ProcessingPublicationError as exc:
            failure = exc.code
        self.assertIsNone(failure, "At least one assertion is required across the complete envelope")
        payload = json.loads(self.catalog.read_original(record.artifact_id, self.auth))
        publications = payload["extraction_publications"]
        self.assertEqual([p["invocation_id"] for p in publications], ["extract-1", "extract-2"])
        self.assertEqual([len(p["assertion_bytes"]) for p in publications], [0, 1])
        self.assertEqual([p["input_record_bytes"][0]["artifact_id"] for p in publications],
            [empty_records[0].artifact_id, rich.artifact_id])
        self.assertEqual(record.parent_hashes, [empty_records[0].original_hash, rich.original_hash])
        for publication in publications:
            self.assertEqual(publication["marker_hash"], hashlib.sha256(encoded(publication["marker_bytes"])).hexdigest())
        before = self.files()
        self.revoked.add("rich-parent")
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence(("extract-1", "extract-2"))
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(self.files(), before)

    def test_all_empty_completed_extractions_remain_unavailable_without_v2_bytes(self):
        # Break: a nonempty publication tuple is mistaken for nonempty assertion evidence.
        self.extraction(claims=())
        self.extraction(invocation_id="extract-2", claims=())
        for identifier in ("extract-1", "extract-2"):
            self.catalog.publish_processing_output(self.binding, identifier, self.auth)
        before, budget = self.files(), self.store.checkpoint("C1").budget
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence(("extract-1", "extract-2"))
        self.assertEqual(denied.exception.code, "input_unavailable")
        self.assertEqual(self.files(), before)
        self.assertEqual(self.store.checkpoint("C1").budget, budget)

    def test_multiple_inputs_keep_equal_hash_logical_records_and_first_occurrence_order(self):
        # Break: collecting parents by content hash conflates independently scoped records.
        path = self.folder / "same.txt"
        path.write_bytes(b"Same bytes")
        first = self.catalog.register(path, "C1", "synthetic-text", {"allowed_actors": ["U1"], "scope_id": "parent-a"})
        second = self.catalog.register(path, "C1", "synthetic-text", {"allowed_actors": ["U1"], "scope_id": "parent-b"})
        narrative = self.catalog.register_saved_narrative(self.binding, self.auth)
        # Durable reservation hashes must be distinct within one invocation; equal hashes
        # remain distinct logical records across separate actual publications.
        self.extraction((second, narrative), claims=("Second", "Narrative"))
        self.extraction((first,), "extract-2", claims=("Conflicting",))
        record = self.register_evidence(("extract-2", "extract-1"))
        envelope = json.loads(self.catalog.read_original(record.artifact_id, self.auth))
        publications = envelope["extraction_publications"]
        self.assertEqual([p["invocation_id"] for p in publications], ["extract-2", "extract-1"])
        self.assertEqual([r["artifact_id"] for r in publications[1]["input_record_bytes"]],
            [second.artifact_id, narrative.artifact_id])
        metadata = json.loads((self.catalog.root / "records" / (record.artifact_id + ".json")).read_bytes())
        self.assertEqual([r["artifact_id"] for r in metadata["processing"]["parents"]],
            [first.artifact_id, second.artifact_id, narrative.artifact_id])
        self.assertEqual(record.parent_hashes, [first.original_hash, second.original_hash, narrative.original_hash])
        self.revoked.add("parent-b")
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence(("extract-2", "extract-1"))
        self.assertEqual(denied.exception.code, "scope_denied")

    def test_exact_repeat_and_reopen_leave_private_inventory_mtime_and_debt_unchanged(self):
        # Break: re-registering evidence regenerates timestamps/files or reserves another attempt.
        self.extraction()
        record = self.register_evidence()
        before, budget = self.files(), self.store.checkpoint("C1").budget
        self.clock.advance(1)
        self.assertEqual(self.register_evidence(), record)
        self.catalog = self.make_catalog()
        self.assertEqual(self.register_evidence(), record)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.store.checkpoint("C1").budget, budget)
        self.assertEqual(len(self.store.processing_attempts(self.binding)), 1)

    def test_source_observations_and_legacy_v1_bytes_remain_exact(self):
        # Break: assertions are merged into source observations or legacy serialization changes.
        self.extraction()
        checkpoint = self.store.checkpoint("C1")
        before = encoded([o.model_dump(mode="json") for o in self.observations])
        legacy = self.catalog.register_planning_snapshot(checkpoint, self.observations, self.auth)
        expected = encoded({"checkpoint": checkpoint.model_dump(mode="json"),
            "observations": [o.model_dump(mode="json") for o in self.observations]})
        self.assertEqual(self.catalog.read_original(legacy.artifact_id, self.auth), expected)
        self.register_evidence()
        self.assertEqual(encoded([o.model_dump(mode="json") for o in self.observations]), before)
        self.assertEqual(self.catalog.register_planning_snapshot(checkpoint, self.observations, self.auth), legacy)
        self.assertEqual(self.catalog.read_original(legacy.artifact_id, self.auth), expected)

    def test_immutable_companion_rejects_mutable_aliases_and_returns_detached_models(self):
        # Break: caller mutations alter the exact registered input after its hash was checked.
        from dataclasses import FrozenInstanceError, replace
        from proofkey.evidence.processing_contracts import PlanningEvidenceInputV2
        self.extraction()
        record = self.register_evidence()
        companion = PlanningEvidenceInputV2.from_bytes(self.catalog.read_original(record.artifact_id, self.auth))
        with self.assertRaises(FrozenInstanceError):
            companion.envelope_hash = "0" * 64
        for change in ({"checkpoint_bytes": bytearray(companion.checkpoint_bytes)},
                {"observation_bytes": list(companion.observation_bytes)},
                {"extraction_publication_bytes": list(companion.extraction_publication_bytes)},
                {"envelope_bytes": bytearray(companion.envelope_bytes)}, {"envelope_hash": "0" * 64}):
            with self.subTest(change=next(iter(change))), self.assertRaises(ValueError):
                replace(companion, **change)
        observation = companion.observations()[0]
        object.__setattr__(observation, "value", "forged")
        publication = companion.extraction_publications()[0]
        assertion = publication.assertions()[0]
        object.__setattr__(assertion, "claim", "forged")
        detached_record = publication.input_records()[0]
        object.__setattr__(detached_record, "parent_hashes", ["0" * 64])
        object.__setattr__(companion.checkpoint().budget, "role_allowances", {})
        self.assertEqual(companion.observations()[0].value, "scheduled")
        self.assertEqual(companion.extraction_publications()[0].assertions()[0].claim, "Damaged")
        self.assertEqual(companion.extraction_publications()[0].input_records()[0].parent_hashes, [])
        self.assertIn("extraction", companion.checkpoint().budget.role_allowances)

    def test_strict_decoder_denies_noncanonical_extra_missing_and_bad_marker_joins(self):
        # Break: weak/defaulting decoding accepts substituted controls or ambiguous JSON.
        from copy import deepcopy
        from proofkey.evidence.processing_contracts import PlanningEvidenceInputV2
        self.extraction()
        record = self.register_evidence()
        payload = self.catalog.read_original(record.artifact_id, self.auth)
        value = json.loads(payload)
        invalid = [payload + b" ", b"\xff", b'{"version":1,"version":2}', b'{"x":NaN}', b'{"x":1e999}']
        for name in value:
            candidate = deepcopy(value)
            del candidate[name]
            invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        candidate["extra"] = None
        invalid.append(encoded(candidate))
        for field, replacement in (("marker_hash", "0" * 64), ("status", "failed"),
                ("mode", "actual"), ("assertion_refs", ["private-assertion-" + "0" * 64]),
                ("transcript_record_bytes", value["extraction_publications"][0]["input_record_bytes"][0])):
            candidate = deepcopy(value)
            candidate["extraction_publications"][0][field] = replacement
            invalid.append(encoded(candidate))
        for field in value["extraction_publications"][0]:
            candidate = deepcopy(value)
            del candidate["extraction_publications"][0][field]
            invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        candidate["extraction_publications"][0]["extra"] = None
        invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        candidate["authority_observations"][0]["extra"] = None
        invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        candidate["checkpoint"]["extra"] = None
        invalid.append(encoded(candidate))
        for field, replacement in (("content_hash", "0" * 64), ("lineage_hash", "0" * 64),
                ("processing_receipt_id", "foreign-invocation"), ("claim", "A" * 65537)):
            candidate = deepcopy(value)
            publication = candidate["extraction_publications"][0]
            publication["assertion_bytes"][0][field] = replacement
            publication["marker_bytes"]["assertions"] = publication["assertion_bytes"]
            publication["marker_hash"] = hashlib.sha256(encoded(publication["marker_bytes"])).hexdigest()
            invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        nested = "too_deep"
        for _ in range(17):
            nested = [nested]
        candidate["authority_observations"][0]["value"] = nested
        invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        candidate["authority_observations"] *= 65
        invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        candidate["extraction_publications"] *= 17
        invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        candidate["extraction_publications"] = []
        invalid.append(encoded(candidate))
        candidate = deepcopy(value)
        publication = candidate["extraction_publications"][0]
        publication["assertion_bytes"] = []
        publication["assertion_refs"] = []
        publication["marker_bytes"]["assertions"] = []
        publication["marker_bytes"]["assertion_refs"] = []
        publication["marker_hash"] = hashlib.sha256(encoded(publication["marker_bytes"])).hexdigest()
        invalid.append(encoded(candidate))
        invalid.append(b" " * (8 * 1024 * 1024 + 1))
        for bad in invalid:
            with self.subTest(payload=bad[:100]), self.assertRaises(ValueError):
                PlanningEvidenceInputV2.from_bytes(bad)

    def test_empty_unknown_duplicate_and_unfinished_ids_never_create_v2_input(self):
        # Break: absent evidence becomes a usable charged-but-unused planning input.
        self.extraction(claims=())
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        self.reserve((record,), "unfinished")
        budget = self.store.checkpoint("C1").budget
        for ids, code in (((), "identity_mismatch"), (("unknown",), "identity_mismatch"),
                (("extract-1", "extract-1"), "identity_mismatch"), (("unfinished",), "not_complete"),
                (("extract-1",), "input_unavailable"), (["extract-1"], "identity_mismatch")):
            with self.subTest(ids=ids), self.assertRaises(ProcessingPublicationError) as denied:
                self.register_evidence(ids)
            self.assertEqual(denied.exception.code, code)
        self.assertEqual(self.store.checkpoint("C1").budget, budget)
        self.assertFalse(any(json.loads(p.read_bytes()).get("record", {}).get("source") == "saved-planning-evidence-v2"
            for p in (self.catalog.root / "records").glob("*.json")))

    def test_failed_unknown_replay_actual_receipts_remain_unusable_and_consumed(self):
        # Break: non-synthetic or incomplete extraction can masquerade as completed planning evidence.
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        for index, (mode, status) in enumerate((("synthetic", "failed"), ("synthetic", "outcome_unknown"),
                ("recorded_replay", "completed"), ("actual", "completed"))):
            invocation_id = "bad-" + str(index)
            identity = self.reserve((record,), invocation_id)
            output = AssertionsOutput(kind="assertions", assertions=[EvidenceAssertion(artifact_id=record.artifact_id,
                content_hash=record.original_hash, lineage_hash=record.lineage_hash,
                locator=UnknownLocator(reason="not_measured"), uncertainty="uncertain",
                processing_receipt_id=invocation_id, claim="Damaged")])
            self.save(identity, output, invocation_id, mode=mode, status=status)
            budget = self.store.checkpoint("C1").budget
            with self.subTest(mode=mode, status=status), self.assertRaises(ProcessingPublicationError) as denied:
                self.register_evidence((invocation_id,))
            self.assertEqual(denied.exception.code, "not_complete")
            self.assertEqual(self.store.checkpoint("C1").budget, budget)

    def hook_final_record(self, callback):
        original_store = self.catalog._store
        def forward(path, payload):
            result = original_store(path, payload)
            if path.parent.name == "records" and json.loads(payload)["record"]["source"] == "saved-planning-evidence-v2":
                callback()
            return result
        self.catalog._store = forward

    def test_stop_after_real_final_record_write_denies_return_and_preserves_debt(self):
        # Break: checking only the checkpoint before final I/O returns a stopped obsolete input.
        self.extraction()
        budget = self.store.checkpoint("C1").budget
        self.hook_final_record(lambda: self.store.set_stop("C1", "G1"))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "identity_mismatch")
        self.assertEqual(self.store.checkpoint("C1").budget, budget)
        self.assertTrue(self.store.checkpoint("C1").stop.requested)
        self.assertTrue(any(json.loads(p.read_bytes())["record"]["source"] == "saved-planning-evidence-v2"
            for p in (self.catalog.root / "records").glob("*.json")))

    def test_expiry_after_real_final_record_write_denies_repeat_without_repair(self):
        # Break: scope checks before final I/O are reused after the exact expiry boundary.
        self.extraction()
        budget = self.store.checkpoint("C1").budget
        self.hook_final_record(lambda: self.clock.advance((DEADLINE - NOW).total_seconds()))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "scope_denied")
        files = self.files()
        with self.assertRaises(ProcessingPublicationError):
            self.register_evidence()
        self.assertEqual(self.files(), files)
        self.assertEqual(self.store.checkpoint("C1").budget, budget)

    def test_parent_scope_denial_after_real_final_write_denies_v2_read_and_return(self):
        # Break: generic ACL alone allows the V2 derivative despite current saved-scope denial.
        path = self.folder / "parent.txt"
        path.write_bytes(b"Damaged box")
        parent = self.catalog.register(path, "C1", "synthetic-text", {"allowed_actors": ["U1"], "scope_id": "parent"})
        records, _ = self.extraction((parent,))
        self.hook_final_record(lambda: self.saved_denied_records.add(records[0].artifact_id))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(self.catalog.get(records[0].artifact_id, self.auth), records[0])
        from proofkey.evidence.catalog import EvidenceAccessDenied
        for path in (self.catalog.root / "records").glob("*.json"):
            record = json.loads(path.read_bytes())["record"]
            if record["source"] == "saved-planning-evidence-v2":
                with self.assertRaises(EvidenceAccessDenied):
                    self.catalog.read_original(record["artifact_id"], self.auth)

    def test_corrupt_existing_envelope_is_denied_without_overwrite(self):
        # Break: corrupt partial inputs are silently repaired or returned as usable.
        self.extraction()
        record = self.register_evidence()
        path = self.catalog.root / "objects" / record.original_hash
        path.write_bytes(b"corrupt")
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "publication_conflict")
        self.assertEqual(self.files(), before)

    def test_transcript_to_audio_ancestry_is_preserved_and_currently_authorized(self):
        # Break: extraction of a derived transcript loses or bypasses its real audio parent.
        import wave
        path = self.folder / "audio.wav"
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(100)
            stream.writeframes(b"\0\0" * 100)
        audio = self.catalog.register(path, "C1", "synthetic-audio",
            {"allowed_actors": ["U1"], "scope_id": "audio-parent"})
        identity = self.reserve((audio,), "transcribe-1", "transcription")
        self.save(identity, TranscriptOutput(kind="transcript", text="Damaged box", segments=[]), "transcribe-1")
        transcript = self.catalog.publish_processing_output(self.binding, "transcribe-1", self.auth).transcript_record()
        self.extraction((transcript,))
        record = self.register_evidence()
        self.assertEqual(record.parent_hashes, [transcript.original_hash])
        publication = json.loads(self.catalog.read_original(record.artifact_id, self.auth))["extraction_publications"][0]
        self.assertEqual(publication["input_record_bytes"][0]["parent_hashes"], [audio.original_hash])
        self.saved_denied_records.add(audio.artifact_id)
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(self.files(), before)

    def test_observation_and_publication_shape_caps_reject_without_truncating(self):
        # Break: oversized sequences are silently shortened or admitted as usable inputs.
        self.extraction()
        self.catalog.publish_processing_output(self.binding, "extract-1", self.auth)
        before = self.files()
        for ids, observations in ((("extract-1",), self.observations * 65),
                (tuple("extract-" + str(i) for i in range(17)), self.observations)):
            with self.subTest(ids=ids), self.assertRaises(ProcessingPublicationError) as denied:
                self.register_evidence(ids, observations=observations)
            self.assertEqual(denied.exception.code, "identity_mismatch")
            self.assertEqual(self.files(), before)

    def test_absolute_aggregate_assertion_cap_rejects_257_actual_saved_assertions(self):
        # Break: individually legal outputs bypass the full-envelope 256-assertion limit.
        self.extraction(claims=tuple("A" for _ in range(128)))
        self.extraction(invocation_id="extract-2", claims=tuple("B" for _ in range(129)))
        for identifier in ("extract-1", "extract-2"):
            self.catalog.publish_processing_output(self.binding, identifier, self.auth)
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence(("extract-1", "extract-2"))
        self.assertEqual(denied.exception.code, "output_invalid")
        self.assertEqual(self.files(), before)

    def test_tightened_byte_limit_denies_exact_envelope_without_truncation_or_repair(self):
        # Break: V2 checks only catalog.max_bytes and ignores the tighter processing ceiling.
        self.extraction()
        record = self.register_evidence()
        payload = self.catalog.read_original(record.artifact_id, self.auth)
        self.catalog = self.make_catalog(max_publication_bytes=len(payload) - 1)
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "output_invalid")
        self.assertEqual(self.files(), before)

    def test_changed_current_checkpoint_is_denied_before_new_envelope_bytes(self):
        # Break: host-supplied historical snapshot is accepted as the current pre-debit input.
        self.extraction()
        checkpoint = self.store.checkpoint("C1")
        self.store.set_stop("C1", "G1")
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence(checkpoint=checkpoint)
        self.assertEqual(denied.exception.code, "identity_mismatch")
        self.assertEqual(self.files(), before)

    def test_current_proof_revocation_after_real_final_write_denies_usable_return(self):
        # Break: a completed extraction or finished V2 file substitutes for current proof.
        self.extraction()
        budget = self.store.checkpoint("C1").budget
        self.hook_final_record(lambda: self.revoked.add("saved-scope"))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(self.store.checkpoint("C1").budget, budget)

    def test_changed_actual_marker_after_final_write_denies_without_repair(self):
        # Break: final return trusts the earlier publication companion after actual marker tampering.
        self.extraction()
        self.catalog.publish_processing_output(self.binding, "extract-1", self.auth)
        marker = next((self.catalog.root / "receipts").glob("output-marker-*.json"))
        self.hook_final_record(lambda: marker.write_bytes(b"corrupt"))
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "publication_conflict")
        self.assertEqual(marker.read_bytes(), b"corrupt")
        before = self.files()
        with self.assertRaises(ProcessingPublicationError):
            self.register_evidence()
        self.assertEqual(self.files(), before)

    def test_foreign_binding_and_nonextraction_durable_attempts_deny_before_v2_bytes(self):
        # Break: global invocation lookup mistakes another case/role for exact extraction evidence.
        original = make_request(case_id="C2", object_id="O2", request_id="REQ2")
        binding = make_binding(original)
        self.store.admit(binding, original, make_checkpoint(binding=binding,
            budget=BudgetLedger(case_id="C2", deadline=DEADLINE, role_allowances={"extraction": RoleAllowance(
                max_invocations=2, max_cost=2, usage_allowances={"tokens": 4})})))
        grant = make_fixture_campaign(campaign_id="foreign-campaign", input_hashes=["a" * 64])
        self.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id="C2", generation="G1", role="extraction",
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash, input_hashes=grant.input_hashes,
            provider=grant.provider, model=grant.model, endpoint=grant.endpoint,
            prompt_hash="2" * 64, version="v1", profile_version="v1", process_version="v1", deadline=DEADLINE)
        self.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id="foreign",
            requested_usage={"tokens": 2}, worst_case_cost=1), NOW)
        self.save(identity, AssertionsOutput(kind="assertions", assertions=[]), "foreign")
        record = self.catalog.register_saved_narrative(self.binding, self.auth)
        self.reserve((record,), "not-extraction", "planning")
        before = self.files()
        for identifier in ("foreign", "not-extraction"):
            with self.subTest(identifier=identifier), self.assertRaises(ProcessingPublicationError) as denied:
                self.register_evidence((identifier,))
            self.assertEqual(denied.exception.code, "identity_mismatch")
            self.assertEqual(self.files(), before)

    def test_processing_bindings_none_stays_unavailable(self):
        # Break: V2 invents source/lookup authority when the trusted dependency is absent.
        self.catalog = EvidenceCatalog(self.folder / "catalog-none", self.clock,
            allowed_input_roots=[self.folder], access_resolver=self.access)
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence()
        self.assertEqual(denied.exception.code, "input_unavailable")
        self.assertEqual(self.files(), before)

    def test_distinct_direct_input_limit_accepts_16_and_denies_17_actual_records(self):
        # Break: independent legal publications bypass the aggregate direct-record cap.
        records = []
        for index in range(17):
            path = self.folder / ("input-" + str(index) + ".txt")
            path.write_bytes(("Distinct text " + str(index)).encode())
            records.append(self.catalog.register(path, "C1", "synthetic-text",
                {"allowed_actors": ["U1"], "scope_id": "parent-" + str(index)}))
        self.extraction(tuple(records[:16]))
        record = self.register_evidence()
        self.assertEqual(record.parent_hashes, [r.original_hash for r in records[:16]])
        self.extraction((records[16],), "extract-2")
        self.catalog.publish_processing_output(self.binding, "extract-2", self.auth)
        before = self.files()
        with self.assertRaises(ProcessingPublicationError) as denied:
            self.register_evidence(("extract-1", "extract-2"))
        self.assertEqual(denied.exception.code, "output_invalid")
        self.assertEqual(self.files(), before)

    def test_source_observation_order_and_empty_batch_are_preserved(self):
        # Break: V2 sorts/merges the source batch or manufactures observations for extraction.
        self.extraction()
        other = self.observations[0].model_copy(update={"fact": "delivery.slot", "value": "S1", "evidence_ref": "source-slot"})
        record = self.register_evidence(observations=(other, self.observations[0]))
        payload = json.loads(self.catalog.read_original(record.artifact_id, self.auth))
        self.assertEqual([o["evidence_ref"] for o in payload["authority_observations"]], ["source-slot", "source-status"])
        empty = self.register_evidence(observations=())
        payload = json.loads(self.catalog.read_original(empty.artifact_id, self.auth))
        self.assertEqual(payload["authority_observations"], [])
        self.assertEqual(payload["extraction_publications"][0]["assertion_bytes"][0]["claim"], "Damaged")

    def nested_v2(self, *, publish_outer=False):
        """Two public durable generations with independently registered current scopes."""
        original_a, binding_a = self.original, self.binding
        original_b = make_request(request_revision="v2", narrative="Review derived input.\n")
        binding_b = make_binding(original_b, generation="G2", supersedes_generation="G1")
        registered = {"G1": (binding_a, original_a, "scope-a"), "G2": (binding_b, original_b, "scope-b")}
        self.nested_scope_denials = {"scope-a": set(), "scope-b": set()}
        def original(binding):
            if self.store.find_request(binding.case_id, binding.request_id, binding.request_revision,
                    binding.consent_revision, binding.fingerprint) != binding:
                raise ValueError("Exact public saved original required")
            return self.store.original_request(binding.case_id, binding.generation)
        def scope(binding, saved, auth, purpose):
            item = registered.get(binding.generation)
            if (item is None or (binding, saved) != item[:2] or auth != self.auth
                    or self.clock.now() >= DEADLINE):
                return None
            raw = dict(allowed_actors=["U1"], case_id="C1", object_id="O1",
                binding_hash=fingerprint(binding.model_dump(mode="json")),
                original_request_hash=fingerprint(saved.model_dump(mode="json")), scope_id=item[2],
                policy_id="local-policy", authorization_reference="local-proof",
                provenance="synthetic_host_registration", expires_at=DEADLINE.isoformat())
            return SavedOriginalScope(encoded(binding.model_dump(mode="json")), raw["original_request_hash"],
                raw["scope_id"], encoded(raw), raw["policy_id"], raw["provenance"],
                raw["authorization_reference"], DEADLINE)
        def access(auth, record, saved_scope, purpose):
            return (auth == self.auth and record.case_id == "C1" and saved_scope["allowed_actors"] == ("U1",)
                and record.artifact_id not in self.nested_scope_denials.get(saved_scope.get("scope_id"), set()))
        self.catalog = EvidenceCatalog(self.folder / "catalog", self.clock,
            allowed_input_roots=[self.folder], access_resolver=access,
            processing_bindings=ProcessingCatalogBindings(original, lambda b: self.store.checkpoint(b.case_id),
                self.store.invocation, scope, profile_lookup=lambda b, o: self.profile))
        path = self.folder / "nested-parent.txt"
        path.write_bytes(b"Original damaged box")
        parent = self.catalog.register(path, "C1", "synthetic-text",
            {"allowed_actors": ["U1"], "scope_id": "opaque-parent"})
        self.extraction((parent,), "extract-a")
        record_a = self.register_evidence(("extract-a",))
        self.store.admit(binding_b, original_b, make_checkpoint(binding=binding_b,
            phase="window_gate", next_gate="reschedule", budget=self.store.checkpoint("C1").budget))
        self.binding, self.original = binding_b, original_b
        self.extraction((record_a,), "extract-b")
        publication_b = self.catalog.publish_processing_output(binding_b, "extract-b", self.auth)
        record_b = self.register_evidence(("extract-b",)) if publish_outer else None
        return parent, record_a, record_b, publication_b, registered

    def test_nested_v2_lawful_scopes_keep_exact_parents_and_idempotent_debt(self):
        # Break: denying all cross-binding nested inputs avoids the missing intersection.
        parent, record_a, record_b, publication_b, registered = self.nested_v2(publish_outer=True)
        self.assertEqual(record_a.parent_hashes, [parent.original_hash])
        self.assertEqual(record_b.parent_hashes, [record_a.original_hash])
        self.assertEqual(publication_b.input_records(), (record_a,))
        payload = json.loads(self.catalog.read_original(record_b.artifact_id, self.auth))
        self.assertEqual(payload["checkpoint"]["binding"]["generation"], "G2")
        self.assertEqual(payload["extraction_publications"][0]["input_record_bytes"][0]["artifact_id"], record_a.artifact_id)
        before, checkpoint = self.files(), self.store.checkpoint("C1")
        self.assertEqual(self.register_evidence(("extract-b",)), record_b)
        self.assertEqual(self.catalog.publish_processing_output(self.binding, "extract-b", self.auth), publication_b)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.store.checkpoint("C1"), checkpoint)
        self.assertEqual(checkpoint.budget.role_allowances["extraction"].invocations, 2)
        for generation, (_, original, _) in registered.items():
            self.assertEqual(self.store.original_request("C1", generation), original)
            self.assertIsNone(self.store.saved_result("C1", generation))

    def test_nested_v2_outer_scope_denies_deeper_parent_before_new_envelope_bytes(self):
        # Break: V2A replaces the B scope before checking the actual deeper parent P.
        parent, record_a, _, publication_b, registered = self.nested_v2()
        self.nested_scope_denials["scope-b"].add(parent.artifact_id)
        before, checkpoint = self.files(), self.store.checkpoint("C1")
        saved = self.store.invocation("extract-b")
        self.assertEqual(self.catalog.get(parent.artifact_id, self.auth), parent)
        self.assertEqual(self.catalog.get(record_a.artifact_id, self.auth), record_a)
        for _ in range(2):
            with self.assertRaises(ProcessingPublicationError) as denied:
                self.register_evidence(("extract-b",))
            self.assertEqual(denied.exception.code, "scope_denied")
            with self.assertRaises(ProcessingPublicationError) as denied:
                self.catalog.publish_processing_output(self.binding, "extract-b", self.auth)
            self.assertEqual(denied.exception.code, "scope_denied")
        self.assertEqual(self.files(), before)
        self.assertEqual(self.store.checkpoint("C1"), checkpoint)
        self.assertEqual(self.store.invocation("extract-b"), saved)
        self.assertEqual(saved[1].status, "completed")
        self.assertEqual(publication_b.input_records(), (record_a,))
        for generation, (_, original, _) in registered.items():
            self.assertEqual(self.store.original_request("C1", generation), original)
            self.assertIsNone(self.store.saved_result("C1", generation))

    def test_nested_v2_public_outer_read_keeps_current_scope_on_deeper_parent(self):
        # Break: ordinary V2B reads discard B when they reach the nested V2A record.
        from proofkey.evidence.catalog import EvidenceAccessDenied
        parent, record_a, record_b, _, _ = self.nested_v2(publish_outer=True)
        self.nested_scope_denials["scope-b"].add(parent.artifact_id)
        before, checkpoint = self.files(), self.store.checkpoint("C1")
        self.assertEqual(self.catalog.get(record_a.artifact_id, self.auth), record_a)
        self.assertEqual(self.catalog.read_original(parent.artifact_id, self.auth), b"Original damaged box")
        for _ in range(2):
            with self.assertRaises(EvidenceAccessDenied):
                self.catalog.get(record_b.artifact_id, self.auth)
            with self.assertRaises(EvidenceAccessDenied):
                self.catalog.read_original(record_b.artifact_id, self.auth)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.store.checkpoint("C1"), checkpoint)


if __name__ == "__main__":
    unittest.main()
