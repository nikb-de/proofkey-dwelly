"""Closed packet source/content validation; no runtime activation."""
import unittest
import copy
import json
from pathlib import Path
from proofkey.identity import fingerprint
from proofkey.profiles import load_profile
from support import NOW
from test_packet_source import content_for, ROOT
try:
    from proofkey import packet_contracts as packets
except ImportError:
    packets = None


class PacketContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(packets, "Closed packet contracts are missing")

    def test_closed_catalog_normalizes_inventory_and_rejects_duplicate_ids(self):
        data = dict(version="packet-catalog-v1", case_id="C1", object_id="O1", complete=True,
                    revision="v1", relevant_set_id="all-case-artifacts", originals=[], extracts=[], restrictions=[])
        catalog = packets.PacketCatalogV1.model_validate(data)
        self.assertEqual(catalog.case_id, "C1")
        with self.assertRaises(ValueError):
            packets.PacketCatalogV1.model_validate({**data, "authorized": True})

    def test_duplicate_json_keys_cannot_be_parsed_as_permission(self):
        catalog = json.loads((ROOT / "fixtures/development/packet-world-v1.json").read_text())["facts"]["operator.packet_catalog"]["value"]
        normal = json.dumps(catalog, separators=(",", ":"))
        self.assertTrue(packets.PacketCatalogV1.model_validate_json(normal).complete)
        with self.assertRaises(ValueError):
            packets.PacketCatalogV1.model_validate_json(normal.replace('"complete":true', '"complete":false,"complete":true'))

    def content(self):
        fixture = json.loads((ROOT / "fixtures/development/packet-world-v1.json").read_text())
        return content_for(fixture, load_profile("flat-v1.3"))

    def test_inventory_sorting_normalizes_utc_and_rejects_duplicate_ids(self):
        catalog = self.content()["catalog"]
        expected = self.content()["access"]["catalog_hash"]
        catalog["originals"][0]["observed_at"] = "2026-10-08T11:00:00+01:00"
        self.assertEqual(fingerprint(packets.PacketCatalogV1.model_validate(catalog).model_dump(mode="json")), expected)
        second = {**catalog["originals"][0], "artifact_id": "A0"}
        catalog["originals"].append(second)
        parsed = packets.PacketCatalogV1.model_validate(catalog)
        self.assertEqual([item.artifact_id for item in parsed.originals], ["A0", "A1"])
        catalog["originals"].append(second)
        with self.assertRaises(ValueError):
            packets.PacketCatalogV1.model_validate(catalog)

    def test_finite_inventory_text_history_and_canonical_content_limits(self):
        data = self.content()
        for field, count in [("originals", 65), ("extracts", 129)]:
            catalog = copy.deepcopy(data["catalog"])
            if field == "originals":
                catalog[field] = [{**catalog[field][0], "artifact_id": "A" + str(i)} for i in range(count)]
            else:
                extract = {"extract_id": "E", "extract_reference": "registry-E", "original_hash": "c" * 64,
                    "content_hash": "f" * 64, "content": "Extract", "processing_receipt_reference": "R1",
                    "assertion": {"artifact_id": "A1", "content_hash": "f" * 64, "lineage_hash": "e" * 64,
                        "locator": {"kind": "unknown", "reason": "processing_unknown"}, "uncertainty": "unverified",
                        "processing_receipt_id": "R1", "claim": "Untrusted evidence"}}
                catalog[field] = [{**extract, "extract_id": "E" + str(i)} for i in range(count)]
            with self.subTest(field=field), self.assertRaises(ValueError):
                packets.PacketCatalogV1.model_validate(catalog)
        for field, record_key, limit in [("history", "action_id", 65), ("generation_stops", "generation", 65)]:
            content = copy.deepcopy(data)
            item = content["history"][0] if field == "history" else {"generation": "G0", "requested_at": NOW.isoformat(), "evidence_ref": "synthetic:stop"}
            content[field] = [{**item, record_key: str(i)} for i in range(limit)]
            with self.subTest(field=field), self.assertRaises(ValueError):
                packets.PacketContentV1.model_validate(content)
        for text in ["x" * 16385, "я" * 8193]:
            with self.assertRaises(ValueError):
                packets.PacketUntrustedRecordV1(record_id="U", description=text, source_refs=["synthetic:unknown"])
        data["unknowns"] = [{"record_id": str(i), "description": "x" * 16000, "source_refs": ["synthetic:unknown"]} for i in range(17)]
        with self.assertRaises(ValueError):
            packets.PacketContentV1.model_validate(data)

    def test_profile_selector_rejects_forged_registered_combinations(self):
        profile = load_profile("flat-v1.3")
        self.assertTrue(packets.packet_enabled(profile))
        cap = profile.capabilities["enqueue_handoff"]
        altered = cap.model_copy(update={"conditional_coverage": cap.conditional_coverage.model_copy(update={
            "covered_fields": [*cap.conditional_coverage.covered_fields, "case.question_revision"]})})
        forged = profile.model_copy(update={"capabilities": {**profile.capabilities, "enqueue_handoff": altered}})
        with self.assertRaises(ValueError):
            packets.packet_enabled(forged)

    def test_flat_nested_profile_preserve_old_graphs_and_unrelated_capabilities(self):
        for variant in ["flat", "nested"]:
            old, new = load_profile(variant + "-v1.2"), load_profile(variant + "-v1.3")
            self.assertEqual(old.processes, new.processes)
            self.assertEqual(old.process_hash, new.process_hash)
            self.assertEqual(old.policy_hash, new.policy_hash)
            self.assertEqual(old.mappings, new.mappings)
            self.assertEqual({k: v for k, v in old.capabilities.items() if k != "enqueue_handoff"},
                             {k: v for k, v in new.capabilities.items() if k != "enqueue_handoff"})
        flat, nested = load_profile("flat-v1.3"), load_profile("nested-v1.3")
        self.assertEqual(flat.capabilities, nested.capabilities)
        self.assertEqual(flat.authorities, nested.authorities)
        self.assertEqual(flat.processes, nested.processes)

    def test_prepared_projection_checks_binding_digest_and_complete_scope(self):
        from proofkey.contracts import OperatorPacket
        data = packets.PacketContentV1.model_validate(self.content())
        source = data.source
        packet = OperatorPacket(packet_id=source.packet_id, case_id="C1", object_id="O1", binding=source.binding,
            packet_hash=source.packet_hash, packet_revision=source.packet_revision, owner=source.owner,
            owner_state=source.owner_state, epoch=source.epoch, state_revision=source.state_revision,
            source_scope=[ref.identity for ref in source.observations], expires_at=data.expires_at, replay_id="synthetic:packet")
        kwargs = dict(packet=packet, content=data, content_hash=fingerprint(data.model_dump(mode="json")), checkpoint_hash="a" * 64)
        self.assertEqual(packets.PreparedPacketV1(**kwargs).packet.packet_id, "P1")
        with self.assertRaises(ValueError):
            packets.PreparedPacketV1(**{**kwargs, "content_hash": "0" * 64})
        incomplete = data.model_copy(update={"catalog": data.catalog.model_copy(update={"complete": False})})
        with self.assertRaises(ValueError):
            packets.PreparedPacketV1(**{**kwargs, "content": incomplete,
                                       "content_hash": fingerprint(incomplete.model_dump(mode="json"))})

    def test_recorded_generation_stop_preserves_explicit_unknown_timestamp(self):
        content = self.content()
        content["generation_stops"] = [{"generation": "G0", "requested_at": None,
            "evidence_ref": "local-record:C1:G0:stop"}]
        try:
            parsed = packets.PacketContentV1.model_validate(content)
        except ValueError as error:
            self.fail("Recorded stop with explicit unknown timestamp was denied: " + str(error))
        self.assertIsNone(parsed.generation_stops[0].requested_at)
        self.assertIsNone(parsed.model_dump(mode="json")["generation_stops"][0]["requested_at"])
        self.assertEqual(parsed.generation_stops[0].evidence_ref, "local-record:C1:G0:stop")

    def test_history_preserves_unknown_dispatch_separately_from_verified_evidence(self):
        content = self.content()
        content["history"][0].update(dispatch_state="unknown", verification_state="verified", unresolved=False,
                                    evidence_refs=["local-record:C1:G0:independent-original-verification"])
        try:
            parsed = packets.PacketContentV1.model_validate(content)
        except ValueError as error:
            self.fail("Verified history with unknown original dispatch receipt was denied: " + str(error))
        self.assertEqual(parsed.history[0].dispatch_state, "unknown")
        self.assertEqual(parsed.history[0].verification_state, "verified")
        self.assertEqual(parsed.history[0].evidence_refs, ["local-record:C1:G0:independent-original-verification"])
