"""Offline model-boundary tests; only the HTTPS boundary is substituted."""
import copy
from decimal import Decimal, localcontext
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.dwelly_analysis import catalog, widget
from tools.dwelly_model import providers

try:
    from tools.dwelly_analysis import model
except ImportError:
    model = None


def settings():
    return {"profiles": [{"id": "openai-test", "label": "Synthetic OpenAI",
             "config": {"provider": "openai", "model": "synthetic-requested",
                        "api_key_env": "SYNTHETIC_API_KEY",
                        "input_usd_per_million": 1, "output_usd_per_million": 2}}],
            "budget_per_model_usd": 1, "max_output_tokens": 1024, "timeout_seconds": 5}


def candidate():
    return {"state": "waiting", "waiting_for": ["service"],
            "next_action": {"type": "wait", "target_actor_id": "service", "description": "Wait for a reply."},
            "evidence_event_ids": ["001"], "uncertainty": ["Source roles are unverified."]}


class Response(io.BytesIO):
    def __init__(self, text, *, observed="synthetic-observed", usage=None):
        body = {"id": "synthetic-response", "model": observed, "status": "completed",
                "output": [{"type": "message", "status": "completed", "content": [{"type": "output_text", "text": text}]}]}
        if usage is not None:
            body["usage"] = usage
        super().__init__(json.dumps(body).encode())
        self.status = 200
        self.headers = {"x-request-id": "synthetic-request"}


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(model, "Dedicated step model adapter is missing")
        self.input = widget.project(catalog.get_document("minimal"), 1, "minimal")
        self.profile = settings()["profiles"][0]

    def load(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "profiles.json")
            path.write_text(json.dumps(value), encoding="utf-8")
            return model.load_profiles(path)

    def parse(self, value):
        return model.parse(self.input, {"text": json.dumps(value)})

    def test_profiles_validate_and_roundtrip_without_environment_values(self):
        self.assertEqual(self.load(settings()), settings())
        example = model.load_profiles(Path(__file__).parents[1] / "model-profiles.example.json")
        self.assertEqual({p["config"]["provider"] for p in example["profiles"]}, {"openai", "anthropic", "gemini"})
        self.assertEqual(len(example["profiles"]), 3)

    def test_invalid_profiles_and_duplicate_ids_fail_closed(self):
        invalid = []
        for field, value in [("budget_per_model_usd", 26), ("budget_per_model_usd", "NaN"),
                             ("max_output_tokens", True), ("max_output_tokens", 0),
                             ("timeout_seconds", float("inf")), ("timeout_seconds", 0),
                             ("timeout_seconds", None)]:
            item = settings(); item[field] = value; invalid.append(item)
        for changes in [{"provider": "unknown"}, {"api_key_env": "SECRET-VALUE"},
                        {"api_key": "DO_NOT_EXPOSE"}, {"workspace_id_env": "WORKSPACE"},
                        {"model": "bad\nmodel"}, {"input_usd_per_million": 0}]:
            item = settings(); item["profiles"][0]["config"].update(changes); invalid.append(item)
        item = settings(); item["profiles"].append(copy.deepcopy(item["profiles"][0])); invalid.append(item)
        item = settings(); item["profiles"][0]["id"] = "../secret"; invalid.append(item)
        item = settings(); item["extra"] = "DO_NOT_EXPOSE"; invalid.append(item)
        for item in invalid:
            with self.subTest(item=item), self.assertRaisesRegex(ValueError, "^invalid_model_profiles$"):
                self.load(item)

    def test_profile_file_duplicate_json_keys_oversize_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "profiles.json")
            for raw in ['{"profiles":[],"profiles":[]}', " " * 65537, '{"secret":"DO_NOT_EXPOSE"']:
                path.write_text(raw)
                with self.assertRaisesRegex(ValueError, "^invalid_model_profiles$"):
                    model.load_profiles(path)
            link = Path(directory, "link.json"); link.symlink_to(path)
            with self.assertRaisesRegex(ValueError, "^invalid_model_profiles$"):
                model.load_profiles(link)

    def test_profile_file_requires_json_not_a_markdown_fence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "profiles.json")
            path.write_text("```json\n" + json.dumps(settings()) + "\n```")
            with self.assertRaisesRegex(ValueError, "^invalid_model_profiles$"):
                model.load_profiles(path)

    def test_availability_is_safe_for_missing_blank_and_invalid_credentials(self):
        configuration = settings()
        for env, expected in [({}, "missing_api_key"), ({"SYNTHETIC_API_KEY": " "}, "missing_api_key"),
                              ({"SYNTHETIC_API_KEY": "private\nvalue"}, "invalid_api_key")]:
            with self.subTest(expected=expected), patch.dict(os.environ, env, clear=True):
                rows = model.public_profiles(configuration)
            self.assertEqual(rows, [{"id": "openai-test", "label": "Synthetic OpenAI", "provider": "openai",
                                     "model": "synthetic-requested", "available": False, "reason": expected}])
            self.assertNotIn("private", json.dumps(rows))
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "private-valid"}, clear=True):
            row = model.public_profiles(configuration)[0]
        self.assertTrue(row["available"]); self.assertIsNone(row["reason"])

    def test_anthropic_workspace_availability_is_explicit(self):
        configuration = settings()
        configuration["profiles"][0]["config"].update(provider="anthropic", workspace_id_env="SYNTHETIC_WORKSPACE")
        for env, expected in [({}, "missing_workspace_id"), ({"SYNTHETIC_WORKSPACE": "private-wrong"}, "invalid_workspace_id"),
                              ({"SYNTHETIC_WORKSPACE": "wrkspc_Synthetic123"}, None)]:
            with patch.dict(os.environ, dict(env, SYNTHETIC_API_KEY="synthetic-key"), clear=True):
                row = model.public_profiles(configuration)[0]
            self.assertEqual(row["reason"], expected)
            self.assertEqual(row["available"], expected is None)
            self.assertNotIn("wrkspc_", json.dumps(row))

    def test_prompt_receives_only_projection_and_excludes_author_and_future_sentinels(self):
        source = catalog.get_document("case-002-n4")
        expected = widget.project(source, 3, "case-002-n4")
        source["steps"][2]["state_after"]["agent_state"]["next_action"] = "LABEL_SENTINEL"
        source["steps"][2]["explanation"] = "EXPLANATION_SENTINEL"
        source["steps"][2]["state_after"]["actors"]["recipient"]["responsibility"] = "ROLE_SENTINEL"
        for step in source["steps"][3:]:
            for message in step["state_after"]["messages"]:
                if message["event_id"] == "004": message["body"] = "FUTURE_SENTINEL"
        projected = widget.project(source, 3, "case-002-n4")
        system, prompt = model.prepare(projected)
        self.assertEqual(projected, expected)
        self.assertEqual(json.loads(prompt), {"input": expected})
        self.assertNotIn("SENTINEL", system + prompt)
        self.assertLessEqual(len((system + prompt).encode()), 65536)
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "synthetic-key"}, clear=True):
            with patch.object(providers, "_open", return_value=Response(json.dumps(candidate()))) as boundary:
                model.request(projected, self.profile, 1024, 5)
        payload = json.loads(boundary.call_args.args[0].data)
        self.assertEqual(payload["input"], "Return a JSON object.\n" + prompt)
        self.assertEqual(payload["instructions"], system)
        self.assertNotIn("SENTINEL", json.dumps(payload))

    def test_prompt_bound_counts_utf8_bytes_and_rejects_extra_input_fields(self):
        large = copy.deepcopy(self.input); large["messages"][0]["body"] = "я" * 33000
        large["input_hash"] = widget.canonical_hash({k: v for k, v in large.items() if k != "input_hash"})
        with self.assertRaisesRegex(ValueError, "^model_prompt_too_large$"): model.prepare(large)
        value = dict(self.input, agent_state={"status": "completed"})
        with self.assertRaisesRegex(ValueError, "^invalid_model_input$"): model.prepare(value)

    def test_request_returns_only_allowed_metadata_and_preserves_unknown_usage(self):
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "synthetic-key"}, clear=True):
            with patch.object(providers, "_open", return_value=Response(json.dumps(candidate()))):
                response = model.request(self.input, self.profile, 1024, 5)
        self.assertEqual(set(response), {"text", "provider", "requested_model", "observed_model", "usage", "request_id", "latency_ms"})
        self.assertEqual(response["requested_model"], "synthetic-requested")
        self.assertEqual(response["observed_model"], "synthetic-observed")
        self.assertEqual(response["usage"], {"input_tokens": None, "output_tokens": None})
        receipt = model.receipt(dict(response, raw_response={"private": "DO_NOT_EXPOSE"}), self.profile)
        self.assertNotIn("text", receipt); self.assertNotIn("raw_response", receipt)
        self.assertEqual(receipt["model_profile_id"], "openai-test")
        self.assertNotIn("DO_NOT_EXPOSE", json.dumps(receipt))

    def test_failed_provider_call_is_sanitized_and_not_retried(self):
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "synthetic-key"}, clear=True):
            with patch.object(providers, "_open", side_effect=OSError("DO_NOT_EXPOSE")) as boundary:
                with self.assertRaisesRegex(ValueError, "^network_error$"):
                    model.request(self.input, self.profile, 1024, 5)
        self.assertEqual(boundary.call_count, 1)

    def test_request_redacts_reflected_workspace_in_text_and_receipt(self):
        profile = copy.deepcopy(self.profile)
        profile["config"].update(provider="anthropic", workspace_id_env="SYNTHETIC_WORKSPACE")
        workspace = "wrkspc_SyntheticPrivate123"
        body = {"id": workspace, "model": workspace, "stop_reason": "end_turn",
                "content": [{"type": "text", "text": workspace}], "usage": {"input_tokens": 2, "output_tokens": 1}}
        response = io.BytesIO(json.dumps(body).encode()); response.status = 200; response.headers = {"x-request-id": workspace}
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "synthetic-key", "SYNTHETIC_WORKSPACE": workspace}, clear=True):
            with patch.object(providers, "_open", return_value=response):
                result = model.request(self.input, profile, 1024, 5)
        self.assertNotIn(workspace, json.dumps(result))
        self.assertEqual(result["text"], "[REDACTED]")
        self.assertEqual(result["observed_model"], "[REDACTED]")

    def test_invalid_limits_and_missing_credentials_never_dispatch(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(providers, "_open") as boundary:
            with self.assertRaisesRegex(ValueError, "^missing_api_key$"):
                model.request(self.input, self.profile, 1024, 5)
            for output, timeout in [(True, 5), (65537, 5), (1024, float("nan")), (1024, 601)]:
                with self.assertRaisesRegex(ValueError, "^invalid_model_limits$"):
                    model.request(self.input, self.profile, output, timeout)
        self.assertEqual(boundary.call_count, 0)

    def test_null_timeout_is_rejected_before_provider_dispatch(self):
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "synthetic-key"}, clear=True):
            with patch.object(providers, "_open") as boundary:
                with self.assertRaisesRegex(ValueError, "^invalid_model_limits$"):
                    model.request(self.input, self.profile, 1024, None)
        self.assertEqual(boundary.call_count, 0)

    def test_unknown_provider_identity_in_receipt_fails_closed(self):
        response = {"provider": "gemini", "requested_model": "wrong", "observed_model": None,
                    "usage": {"input_tokens": None, "output_tokens": None}, "request_id": None, "latency_ms": 1}
        with self.assertRaisesRegex(ValueError, "^invalid_model_response$"): model.receipt(response, self.profile)

    def test_invalid_usage_and_latency_never_become_zero_receipts(self):
        base = {"provider": "openai", "requested_model": "synthetic-requested", "observed_model": None,
                "usage": {"input_tokens": None, "output_tokens": None}, "request_id": None, "latency_ms": 1}
        for changes in [{"latency_ms": float("nan")}, {"usage": {"input_tokens": True, "output_tokens": 0}},
                        {"usage": {"input_tokens": -1, "output_tokens": None}}, {"requested_model": "other"}]:
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "^invalid_model_response$"):
                model.receipt(dict(base, **changes), self.profile)

    def test_parse_adds_only_host_owned_fields(self):
        parsed = self.parse(candidate())
        self.assertEqual(parsed, dict(candidate(), schema_version="proofkey-step-candidate-v1", input_hash=self.input["input_hash"],
                                      mode="model", live_calls=1, operational_effects=0, physical_delivery="not_inferred"))

    def test_extra_output_fields_and_unknown_actor_or_evidence_are_rejected(self):
        invalid = [dict(candidate(), operational_effects=1), dict(candidate(), state="author-approved"),
                   dict(candidate(), waiting_for=["unknown"]), dict(candidate(), evidence_event_ids=["future"]),
                   dict(candidate(), evidence_event_ids=[]), dict(candidate(), evidence_event_ids=["001", "001"])]
        item = candidate(); item["next_action"]["target_actor_id"] = "unknown"; invalid.append(item)
        item = candidate(); item["next_action"]["extra"] = "private"; invalid.append(item)
        for item in invalid:
            with self.subTest(item=item), self.assertRaisesRegex(ValueError, "^invalid_model_output$"):
                self.parse(item)

    def test_waiting_and_completed_consistency(self):
        valid = candidate(); valid.update(state="completed", waiting_for=[])
        valid["next_action"] = {"type": "none", "target_actor_id": None, "description": "Goal satisfied in visible evidence."}
        self.assertEqual(self.parse(valid)["state"], "completed")
        unknown = candidate(); unknown.update(state="unknown", waiting_for=[], evidence_event_ids=[])
        unknown["next_action"] = {"type": "operator_review", "target_actor_id": None, "description": "Review insufficient evidence."}
        self.assertEqual(self.parse(unknown)["state"], "unknown")
        invalid = []
        for changes in [{"state": "completed"}, {"waiting_for": []}, {"state": "ready"}]:
            invalid.append(dict(candidate(), **changes))
        item = copy.deepcopy(valid); item["next_action"]["type"] = "propose_forwarding"; invalid.append(item)
        item = copy.deepcopy(unknown); item["next_action"]["type"] = "request_information"; invalid.append(item)
        for item in invalid:
            with self.subTest(item=item), self.assertRaisesRegex(ValueError, "^invalid_model_output$"): self.parse(item)

    def test_ready_actions_require_visible_targets_and_never_wait_or_resend(self):
        for kind in ["request_information", "request_readback", "propose_forwarding", "operator_review"]:
            item = candidate(); item.update(state="ready", waiting_for=[])
            item["next_action"]["type"] = kind
            self.assertEqual(self.parse(item)["next_action"]["type"], kind)
            if kind != "operator_review":
                item["next_action"]["target_actor_id"] = None
                with self.assertRaisesRegex(ValueError, "^invalid_model_output$"): self.parse(item)
        for kind in ["resend", "execute", "send_message"]:
            item = candidate(); item["next_action"]["type"] = kind
            with self.assertRaisesRegex(ValueError, "^invalid_model_output$"): self.parse(item)

    def test_quoted_duplicate_nonfinite_deep_and_oversized_json_rejected(self):
        raw = json.dumps(candidate())
        invalid = [json.dumps(raw), '{"state":"waiting","state":"completed"}', '{"x":NaN}',
                   '[' * 80 + '0' + ']' * 80, " " * 65537, "```json\n" + raw + "\n``` trailing"]
        for text in invalid:
            with self.subTest(text=text[:60]), self.assertRaisesRegex(ValueError, "^invalid_model_output$"):
                model.parse(self.input, {"text": text})
        self.assertEqual(model.parse(self.input, {"text": "```json\n" + raw + "\n```"})["state"], "waiting")

    def test_reservation_uses_utf8_bytes_and_configured_output_limit(self):
        system, prompt = model.prepare(self.input)
        expected = (Decimal(len(system.encode()) + len(prompt.encode()) + 512) + Decimal(1024 * 2)) / Decimal(1000000)
        self.assertEqual(model.reservation(self.input, self.profile, 1024), expected)
        self.assertGreater(expected, 0)
        with self.assertRaisesRegex(ValueError, "^invalid_model_limits$"):
            model.reservation(self.input, self.profile, True)

    def test_unrepresentable_reservation_fails_with_sanitized_code(self):
        profile = copy.deepcopy(self.profile)
        profile["config"]["input_usd_per_million"] = "1e999999999999999999"
        with self.assertRaisesRegex(ValueError, "^invalid_model_profiles$"):
            model.reservation(self.input, profile, 1024)

    def test_reservation_is_upward_and_independent_of_ambient_precision(self):
        profile = copy.deepcopy(self.profile)
        price = "0.123456789012345678901234567890123456789"
        profile["config"]["input_usd_per_million"] = price
        profile["config"]["output_usd_per_million"] = price
        system, prompt = model.prepare(self.input)
        total_tokens = len(system.encode()) + len(prompt.encode()) + 512 + 128
        with localcontext() as context:
            context.prec = 100
            exact = Decimal(total_tokens) * Decimal(price) / Decimal(1000000)
        with localcontext() as context:
            context.prec = 6
            low_precision = model.reservation(self.input, profile, 128)
        with localcontext() as context:
            context.prec = 100
            high_precision = model.reservation(self.input, profile, 128)
        self.assertEqual(low_precision, high_precision)
        self.assertGreaterEqual(low_precision, exact)
        self.assertLessEqual(len(low_precision.as_tuple().digits), 64)


if __name__ == "__main__":
    unittest.main()
