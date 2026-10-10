"""Offline transport contracts: doubles replace only the HTTP boundary."""
import io
from http.client import BadStatusLine
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

try:
    from tools.dwelly_model import providers
except ImportError:
    providers = None


class Response(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(body if isinstance(body, bytes) else json.dumps(body).encode())
        self.headers = headers or {}
        self.status = 200


def fixture(provider):
    if provider == "openai":
        return {"id": "resp_123", "model": "gpt-observed", "status": "completed",
                "output": [{"type": "message", "status": "completed", "role": "assistant",
                            "content": [{"type": "output_text", "text": "{\"ok\":true}"}]}],
                "usage": {"input_tokens": 19, "output_tokens": 7}}
    if provider == "anthropic":
        return {"id": "msg_123", "type": "message", "role": "assistant", "model": "claude-observed",
                "stop_reason": "end_turn", "content": [{"type": "text", "text": "{\"ok\":true}"}],
                "usage": {"input_tokens": 19, "output_tokens": 7}}
    return {"responseId": "gem_123", "modelVersion": "gemini-observed",
            "candidates": [{"content": {"role": "model", "parts": [{"text": "{\"ok\":true}"}]},
                            "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 19, "candidatesTokenCount": 7}}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(providers, "provider implementation is missing")
        self.env = patch.dict(os.environ, {"DWELLY_TEST_KEY": "synthetic-secret"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def config(self, provider="openai"):
        return {"provider": provider, "model": "configured-model", "api_key_env": "DWELLY_TEST_KEY",
                "input_usd_per_million": 1, "output_usd_per_million": 2}

    def invoke(self, body, provider="openai", headers=None):
        with patch.object(providers, "_open", return_value=Response(body, headers)) as boundary:
            result = providers.complete(self.config(provider), "system policy", "visible input", 123, 9)
        return result, boundary.call_args

    def test_provider_envelopes_and_attribution(self):
        expected = {
            "openai": ("https://api.openai.com/v1/responses", "gpt-observed", "resp_123"),
            "anthropic": ("https://api.anthropic.com/v1/messages", "claude-observed", "msg_123"),
            "gemini": ("https://generativelanguage.googleapis.com/v1beta/models/configured-model:generateContent", "gemini-observed", "gem_123"),
        }
        for provider, (url, observed, response_id) in expected.items():
            with self.subTest(provider=provider):
                body = fixture(provider)
                result, call = self.invoke(body, provider, {"x-request-id": "http_123"})
                request = call.args[0]
                payload = json.loads(request.data)
                self.assertEqual(request.full_url, url)
                self.assertEqual(request.get_method(), "POST")
                self.assertEqual(call.args[1], 9)
                self.assertNotIn("synthetic-secret", request.full_url)
                self.assertEqual(result["provider"], provider)
                self.assertEqual(result["requested_model"], "configured-model")
                self.assertEqual(result["observed_model"], observed)
                self.assertEqual(result["request_id"], "http_123")
                self.assertEqual(result["input_tokens"], 19)
                self.assertEqual(result["output_tokens"], 7)
                self.assertEqual(result["text"], '{"ok":true}')
                self.assertEqual(result["raw_response"], body)
                self.assertGreaterEqual(result["latency_ms"], 0)
                if provider == "openai":
                    self.assertEqual(payload, {"model": "configured-model", "instructions": "system policy",
                                               "input": "visible input", "max_output_tokens": 123,
                                               "store": False, "text": {"format": {"type": "json_object"}}})
                    self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-secret")
                elif provider == "anthropic":
                    self.assertEqual(payload, {"model": "configured-model", "system": "system policy",
                                               "messages": [{"role": "user", "content": "visible input"}], "max_tokens": 123})
                    self.assertEqual(request.get_header("X-api-key"), "synthetic-secret")
                    self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
                else:
                    self.assertEqual(payload, {"systemInstruction": {"parts": [{"text": "system policy"}]},
                                               "contents": [{"role": "user", "parts": [{"text": "visible input"}]}],
                                               "generationConfig": {"maxOutputTokens": 123,
                                                                    "responseMimeType": "application/json"}})
                    self.assertEqual(request.get_header("X-goog-api-key"), "synthetic-secret")
                without_headers, _ = self.invoke(fixture(provider), provider)
                self.assertEqual(without_headers["request_id"], response_id)

    def test_missing_key_and_bad_config_never_dispatch(self):
        for updates, code in [({"api_key_env": "ABSENT"}, "missing_api_key"),
                              ({"api_key": "secret"}, "invalid_config"),
                              ({"provider": "other"}, "invalid_config"),
                              ({"model": ""}, "invalid_config")]:
            with self.subTest(updates=updates), patch.object(providers, "_open") as boundary:
                with self.assertRaises(providers.ProviderError) as error:
                    providers.complete(dict(self.config(), **updates), "s", "p")
                self.assertEqual(error.exception.code, code)
                boundary.assert_not_called()

    def test_rejects_incomplete_or_empty_outputs(self):
        for provider in ("openai", "anthropic", "gemini"):
            body = fixture(provider)
            if provider == "openai":
                body["status"] = "incomplete"
            elif provider == "anthropic":
                body["stop_reason"] = "max_tokens"
            else:
                body["candidates"][0]["finishReason"] = "MAX_TOKENS"
            with self.subTest(provider=provider), self.assertRaises(providers.ProviderError) as error:
                self.invoke(body, provider)
            self.assertEqual(error.exception.code, "incomplete_response")
        body = fixture("openai")
        body["output"] = []
        with self.assertRaises(providers.ProviderError) as error:
            self.invoke(body)
        self.assertEqual(error.exception.code, "missing_text")

    def test_http_and_network_errors_are_sanitized_and_not_retried(self):
        for failure, code in [(HTTPError("https://example/secret", 429, "synthetic-secret", {}, io.BytesIO(b"synthetic-secret")), "http_429"),
                              (HTTPError("https://example/secret", 302, "synthetic-secret", {}, None), "http_302"),
                              (URLError("synthetic-secret"), "network_error"),
                              (BadStatusLine("synthetic-secret"), "network_error"),
                              (TimeoutError("synthetic-secret"), "timeout")]:
            with self.subTest(code=code), patch.object(providers, "_open", side_effect=failure) as boundary:
                with self.assertRaises(providers.ProviderError) as error:
                    providers.complete(self.config(), "s", "p")
                self.assertEqual(error.exception.code, code)
                self.assertNotIn("synthetic-secret", str(error.exception))
                self.assertEqual(boundary.call_count, 1)

    def test_malformed_and_oversized_response_rejected(self):
        for body, code in [(b"not json", "invalid_response"), (b"[]", "invalid_response"),
                           (b"x" * (2 * 1024 * 1024 + 1), "response_too_large")]:
            with self.subTest(code=code), self.assertRaises(providers.ProviderError) as error:
                self.invoke(body)
            self.assertEqual(error.exception.code, code)

    def test_unknown_usage_remains_unknown(self):
        body = fixture("openai")
        body.pop("usage")
        body.pop("model")
        result, _ = self.invoke(body)
        self.assertIsNone(result["input_tokens"])
        self.assertIsNone(result["output_tokens"])
        self.assertIsNone(result["observed_model"])

    def test_anthropic_cached_tokens_are_not_lost_from_input_usage(self):
        body = fixture("anthropic")
        body["usage"].update(cache_read_input_tokens=11, cache_creation_input_tokens=13)
        result, _ = self.invoke(body, "anthropic")
        self.assertEqual(result["input_tokens"], 43)

    def test_deeply_nested_json_is_sanitized(self):
        with self.assertRaises(providers.ProviderError) as error:
            self.invoke(b"[" * 2000 + b"]" * 2000)
        self.assertEqual(error.exception.code, "invalid_response")

    def test_nonfinite_metadata_and_duplicate_keys_are_rejected(self):
        valid = json.dumps(fixture("openai"))
        invalid_suffixes = [', "metadata": NaN}', ', "metadata": Infinity}',
                            ', "metadata": -Infinity}', ', "metadata": 1e10000}',
                            ', "metadata": {"x": 1, "x": 2}}']
        for suffix in invalid_suffixes:
            with self.subTest(suffix=suffix):
                with self.assertRaises(providers.ProviderError) as error:
                    self.invoke((valid[:-1] + suffix).encode())
                self.assertEqual(error.exception.code, "invalid_response")

    def test_transport_explicitly_disables_redirects(self):
        with patch.object(providers.urllib.request, "build_opener") as builder:
            providers._open("request", 9)
        handler = builder.call_args.args[0]
        self.assertIsNone(handler.redirect_request(None, None, 302, "redirect", {}, "https://evil.example"))
        builder.return_value.open.assert_called_once_with("request", timeout=9)

    def test_lone_surrogates_in_envelope_text_metadata_and_keys_are_rejected(self):
        for provider in ("openai", "anthropic", "gemini"):
            for location in ("text", "metadata", "key"):
                for surrogate in ("\ud800", "\udfff"):
                    with self.subTest(provider=provider, location=location, surrogate=repr(surrogate)):
                        body = fixture(provider)
                        if location == "metadata":
                            body["metadata"] = {"nested": [surrogate]}
                        elif location == "key":
                            body["metadata"] = {surrogate: "value"}
                        elif provider == "openai":
                            body["output"][0]["content"][0]["text"] = surrogate
                        elif provider == "anthropic":
                            body["content"][0]["text"] = surrogate
                        else:
                            body["candidates"][0]["content"]["parts"][0]["text"] = surrogate
                        with self.assertRaises(providers.ProviderError) as error:
                            self.invoke(body, provider)
                        self.assertEqual(error.exception.code, "invalid_response")

    def test_valid_emoji_surrogate_pair_remains_accepted(self):
        emoji = json.loads('"\\ud83d\\ude00"')
        body = fixture("openai")
        body["output"][0]["content"][0]["text"] = emoji
        body["metadata"] = {emoji: [emoji]}
        result, _ = self.invoke(body)
        self.assertEqual(result["text"], emoji)
        json.dumps(result, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
