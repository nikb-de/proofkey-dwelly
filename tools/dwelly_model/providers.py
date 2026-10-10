"""Small, non-retrying HTTPS transports for attributable model completions.

Only environment-variable names belong in config. ``_open`` is the network
boundary, replaceable by offline tests; production always refuses redirects.
"""
import json
import http.client
import math
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ProviderError(RuntimeError):
    """Failure with a stable, credential-free code safe for persistence."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open(request, timeout):
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


def _token_count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _identity(value):
    return value if isinstance(value, str) and value.strip() else None


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite number")
    return number


def _reject_constant(value):
    raise ValueError("nonfinite constant")


def _redact(value, secret):
    if isinstance(value, str):
        # Escaped lone surrogates are legal to json.loads but cannot be written
        # to our UTF-8 receipts. Check every decoded string, including keys.
        value.encode("utf-8")
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {_redact(key, secret): _redact(item, secret) for key, item in value.items()}
    return value


def complete(config: dict, system: str, prompt: str, max_output_tokens: int = 2048,
             timeout: float = 45) -> dict:
    """Request one completion and retain actual provider identity and usage.

    Missing usage or model identity remains ``None``; it is never inferred from
    the request. All failures are sanitized and no failed request is retried.
    """
    allowed = {"provider", "model", "api_key_env", "workspace_id_env",
               "input_usd_per_million", "output_usd_per_million"}
    if not isinstance(config, dict) or set(config) - allowed:
        raise ProviderError("invalid_config")
    provider = config.get("provider")
    model = config.get("model")
    env_name = config.get("api_key_env")
    workspace_env = config.get("workspace_id_env")
    if (provider not in ("openai", "anthropic", "gemini")
            or not isinstance(model, str) or not model.strip() or len(model) > 256
            or any(ord(char) < 32 for char in model)
            or not isinstance(env_name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", env_name)
            or ("workspace_id_env" in config
                and (provider != "anthropic" or not isinstance(workspace_env, str)
                     or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", workspace_env)))
            or not isinstance(system, str) or not isinstance(prompt, str)
            or not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool)
            or max_output_tokens <= 0 or not isinstance(timeout, (int, float))
            or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0):
        raise ProviderError("invalid_config")
    secret = os.environ.get(env_name)
    if not secret or not secret.strip():
        raise ProviderError("missing_api_key")
    if "\r" in secret or "\n" in secret:
        raise ProviderError("invalid_api_key")
    workspace_id = None
    if workspace_env is not None:
        workspace_id = os.environ.get(workspace_env)
        if not workspace_id:
            raise ProviderError("missing_workspace_id")
        if not re.fullmatch(r"wrkspc_[A-Za-z0-9]{1,128}", workspace_id):
            raise ProviderError("invalid_workspace_id")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if provider == "openai":
        url = "https://api.openai.com/v1/responses"
        headers["Authorization"] = "Bearer " + secret
        payload = {"model": model, "instructions": system, "input": prompt,
                   "max_output_tokens": max_output_tokens, "store": False,
                   "text": {"format": {"type": "json_object"}}}
    elif provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers.update({"x-api-key": secret, "anthropic-version": "2023-06-01"})
        if workspace_id is not None:
            headers["anthropic-workspace-id"] = workspace_id
        payload = {"model": model, "system": system,
                   "messages": [{"role": "user", "content": prompt}], "max_tokens": max_output_tokens}
    else:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               + urllib.parse.quote(model, safe="") + ":generateContent")
        headers["x-goog-api-key"] = secret
        payload = {"systemInstruction": {"parts": [{"text": system}]},
                   "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                   "generationConfig": {"maxOutputTokens": max_output_tokens,
                                        "responseMimeType": "application/json"}}
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    start = time.monotonic()
    try:
        with _open(request, timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise ProviderError("http_" + str(status) if isinstance(status, int) else "http_error")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            request_id = _identity(response.headers.get("x-request-id") or response.headers.get("request-id"))
    except urllib.error.HTTPError as error:
        code = error.code
        if error.fp is not None:
            error.close()
        raise ProviderError("http_" + str(code) if isinstance(code, int) else "http_error") from None
    except (TimeoutError, socket.timeout):
        raise ProviderError("timeout") from None
    except urllib.error.URLError as error:
        code = "timeout" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "network_error"
        raise ProviderError(code) from None
    except (OSError, ValueError, http.client.HTTPException):
        raise ProviderError("network_error") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProviderError("response_too_large")
    try:
        body = json.loads(raw, object_pairs_hook=_strict_object,
                          parse_constant=_reject_constant, parse_float=_finite_float)
        body = _redact(body, secret)
    except (ValueError, UnicodeError, RecursionError):
        raise ProviderError("invalid_response") from None
    if not isinstance(body, dict):
        raise ProviderError("invalid_response")
    try:
        if provider == "openai":
            if body.get("status") != "completed":
                raise ProviderError("incomplete_response")
            pieces = []
            for item in body.get("output", []):
                if item.get("type") == "message":
                    if item.get("status") not in (None, "completed"):
                        raise ProviderError("incomplete_response")
                    pieces.extend(part["text"] for part in item.get("content", [])
                                  if part.get("type") == "output_text")
            usage = body.get("usage") or {}
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            observed_model = body.get("model")
            response_id = body.get("id")
        elif provider == "anthropic":
            if body.get("stop_reason") not in ("end_turn", "stop_sequence"):
                raise ProviderError("incomplete_response")
            pieces = [part["text"] for part in body.get("content", []) if part.get("type") == "text"]
            usage = body.get("usage") or {}
            input_parts = [usage.get("input_tokens"), usage.get("cache_read_input_tokens", 0),
                           usage.get("cache_creation_input_tokens", 0)]
            input_tokens = (sum(input_parts) if all(_token_count(n) is not None for n in input_parts)
                            else None)
            output_tokens = usage.get("output_tokens")
            observed_model = body.get("model")
            response_id = body.get("id")
        else:
            candidates = body.get("candidates") or []
            if not candidates:
                raise ProviderError("missing_text")
            candidate = candidates[0]
            if candidate.get("finishReason") != "STOP":
                raise ProviderError("incomplete_response")
            pieces = [part["text"] for part in candidate.get("content", {}).get("parts", [])
                      if "text" in part and not part.get("thought", False)]
            usage = body.get("usageMetadata") or {}
            input_tokens = usage.get("promptTokenCount")
            # Thinking tokens are billed output too; preserve unknown usage.
            output_tokens = usage.get("candidatesTokenCount")
            thoughts = usage.get("thoughtsTokenCount", 0)
            if _token_count(output_tokens) is not None and _token_count(thoughts) is not None:
                output_tokens += thoughts
            else:
                output_tokens = None
            observed_model = body.get("modelVersion")
            response_id = body.get("responseId")
        if any(not isinstance(piece, str) for piece in pieces):
            raise ProviderError("invalid_response")
        text = "".join(pieces)
        if not text.strip():
            raise ProviderError("missing_text")
    except (AttributeError, TypeError, KeyError, IndexError):
        raise ProviderError("invalid_response") from None
    return {"text": text, "provider": provider, "requested_model": model,
            "observed_model": _identity(observed_model), "input_tokens": _token_count(input_tokens),
            "output_tokens": _token_count(output_tokens),
            "request_id": _redact(request_id, secret) if request_id else _identity(response_id),
            "latency_ms": round((time.monotonic() - start) * 1000, 3), "raw_response": body}
