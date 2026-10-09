"""Narrow single Messages request over an explicit injected transport, always synthetic.

Schema refreshed 2026-10-09 from https://platform.claude.com/docs/en/api/messages/create.
No SDK, credential discovery, account access, URL fetch, retry or live enablement.
"""
import base64
import hashlib
import json
import time

from pydantic import TypeAdapter
from proofkey.contracts import (AssertionsOutput, EvidenceAssertion, Locator, ProcessingReceipt, ProposalOutput)
from proofkey.evidence.catalog import _validate_locator
from proofkey.providers.invocations import output_digest
from proofkey.providers.protocols import (TransportRequest, exact_context, finite_limits, read_records, strict_json)

ENDPOINT = "https://api.anthropic.com/v1/messages"
USAGE_FIELDS = frozenset({"input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"})


class AnthropicClient:
    def __init__(self, transport, *, system_prompt, max_tokens, max_request_bytes=2 * 1024 * 1024,
                 max_response_bytes=2 * 1024 * 1024):
        if not callable(transport) or not isinstance(system_prompt, str) or not system_prompt:
            raise ValueError("Explicit injected transport and trusted prompt required")
        if type(max_tokens) is not int or not 0 < max_tokens <= 4096:
            raise ValueError("Finite positive output token ceiling required")
        finite_limits(max_request_bytes, max_response_bytes)
        self.transport, self.system_prompt, self.max_tokens = transport, system_prompt, max_tokens
        self.max_request_bytes, self.max_response_bytes = max_request_bytes, max_response_bytes

    def _request(self, content, context, role):
        exact_context(context, role, "anthropic", ENDPOINT)
        if hashlib.sha256(self.system_prompt.encode()).hexdigest() != context.identity.prompt_hash:
            raise ValueError("Trusted prompt bytes differ from reserved hash")
        ceiling = context.reserved_usage.get("output_tokens")
        if ceiling is None or ceiling < 1 or "input_tokens" not in context.reserved_usage:
            raise ValueError("Named input/output token reservations required before transport")
        body = json.dumps({"model": context.identity.model, "max_tokens": min(self.max_tokens, int(ceiling)),
            "system": self.system_prompt, "messages": [{"role": "user", "content": content}]},
            allow_nan=False, separators=(",", ":")).encode()
        if len(body) > self.max_request_bytes:
            raise ValueError("Encoded request byte ceiling exceeded")
        started = time.monotonic()
        response = self.transport(TransportRequest(ENDPOINT, body, "application/json", context.timeout_seconds,
                                                  self.max_response_bytes))
        envelope = strict_json(response, self.max_response_bytes)
        if (envelope.get("type") != "message" or envelope.get("role") != "assistant"
                or envelope.get("stop_reason") != "end_turn" or not isinstance(envelope.get("id"), str)
                or not envelope["id"] or not isinstance(envelope.get("content"), list)
                or len(envelope["content"]) != 1):
            raise ValueError("Provider response is not one complete role output")
        block = envelope["content"][0]
        if (not isinstance(block, dict) or set(block) != {"type", "text"} or block.get("type") != "text"
                or not isinstance(block.get("text"), str)):
            raise ValueError("Tools, hidden content and nontext outputs are unavailable")
        output = strict_json(type(response)(200, block["text"].encode()), self.max_response_bytes)
        usage = envelope.get("usage")
        if not isinstance(usage, dict) or not {"input_tokens", "output_tokens"} <= set(usage) or not set(usage) <= USAGE_FIELDS:
            raise ValueError("Usage includes missing or unapproved units")
        if any(type(value) is not int or value < 0 or key not in context.reserved_usage
               or value > context.reserved_usage[key] for key, value in usage.items()):
            raise ValueError("Observed usage exceeds or differs from reserved units")
        observed = envelope.get("model")
        if observed is not None and (not isinstance(observed, str) or not observed):
            raise ValueError("Malformed observed model identity")
        return output, observed, envelope["id"], {key: float(val) for key, val in usage.items()}, time.monotonic() - started

    def _receipt(self, output, context, observed, request_id, usage, elapsed, coordinates=()):
        return ProcessingReceipt(invocation_id=context.invocation_id, role=context.identity.role, provider="anthropic",
            requested_model=context.identity.model, observed_model=observed, provider_request_id=request_id,
            prompt_hash=context.identity.prompt_hash, version=context.identity.version,
            input_hashes=context.identity.input_hashes, mode="synthetic", status="completed", latency_seconds=elapsed,
            usage=usage, output=output, output_hashes=[output_digest(output)],
            output_refs=[a.artifact_id for a in output.assertions] if isinstance(output, AssertionsOutput) else [],
            available_coordinates=list(coordinates), processed_at=context.catalog.clock.now(),
            reason="Injected transport fixture; no actual provider participation attested")

    def extract(self, records, context):
        exact_context(context, "extraction", "anthropic", ENDPOINT)
        decoded = read_records(records, context, self.max_request_bytes)
        content, sources = [], {}
        for record, payload, intake in decoded:
            sources[record.artifact_id] = (record, intake)
            # Labels come from the catalog-verified source, not its narrative.
            # Keep boundaries in separate API blocks adjacent to exact source
            # bytes so text/image/PDF outputs can name the same registered ID.
            content.append({"type": "text", "text": json.dumps({"boundary": "source_start",
                "artifact_id": record.artifact_id, "original_hash": record.original_hash,
                "mime_type": record.mime_type, "lineage_hash": record.lineage_hash},
                sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)})
            if record.mime_type in {"text/plain", "application/json", "text/x-supplied-transcript"}:
                content.append({"type": "text", "text": payload.decode("utf-8")})
            elif record.mime_type in {"image/jpeg", "image/png", "application/pdf"}:
                content.append({"type": "document" if record.mime_type == "application/pdf" else "image",
                    "source": {"type": "base64", "media_type": record.mime_type,
                               "data": base64.b64encode(payload).decode("ascii")}})
            else:
                raise ValueError("Content requires a different declared role route")
            content.append({"type": "text", "text": json.dumps({"boundary": "source_end",
                "artifact_id": record.artifact_id}, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False)})
        wire, observed, request_id, usage, elapsed = self._request(content, context, "extraction")
        if set(wire) != {"kind", "assertions"} or wire["kind"] != "assertions" or not isinstance(wire["assertions"], list):
            raise ValueError("Strict extraction output required")
        assertions, coordinates = [], []
        for item in wire["assertions"]:
            if not isinstance(item, dict) or set(item) != {"artifact_id", "claim", "locator"}:
                raise ValueError("Assertion cannot supply authority or processing identity")
            if item["artifact_id"] not in sources or not isinstance(item["claim"], str) or not item["claim"].strip():
                raise ValueError("Unknown source or empty assertion")
            record, intake = sources[item["artifact_id"]]
            locator = TypeAdapter(Locator).validate_python(item["locator"])
            if locator.kind != "unknown":
                _validate_locator(locator, intake.available_coordinates)
            assertions.append(EvidenceAssertion(artifact_id=record.artifact_id, claim=item["claim"],
                content_hash=hashlib.sha256(item["claim"].encode()).hexdigest(), lineage_hash=record.lineage_hash,
                locator=locator, uncertainty="unverified", processing_receipt_id=context.invocation_id))
            coordinates.append(locator)
        return self._receipt(AssertionsOutput(kind="assertions", assertions=assertions), context,
                             observed, request_id, usage, elapsed, coordinates)

    def propose(self, checkpoint, observations, context):
        exact_context(context, "planning", "anthropic", ENDPOINT)
        # This is the pre-debit immutable snapshot supplied by the trusted host,
        # not a new read of the mutable journal after the invocation reservation.
        snapshot = json.dumps({"checkpoint": checkpoint.model_dump(mode="json"),
            "observations": [item.model_dump(mode="json") for item in observations]},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        if context.identity.input_hashes != [hashlib.sha256(snapshot).hexdigest()]:
            raise ValueError("Planning snapshot differs from exact reserved bytes")
        decoded = read_records(context.input_records, context, self.max_request_bytes)
        if len(decoded) != 1 or decoded[0][0].mime_type != "application/json" or decoded[0][1] != snapshot:
            raise ValueError("Planning requires an exact registered JSON snapshot")
        wire, observed, request_id, usage, elapsed = self._request(
            [{"type": "text", "text": snapshot.decode("utf-8")}], context, "planning")
        return self._receipt(ProposalOutput.model_validate(wire), context, observed, request_id, usage, elapsed)
