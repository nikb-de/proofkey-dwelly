"""Single synthetic synchronous WAV ASR request; model and billed usage remain unknown.

Schema refreshed 2026-10-09 from https://elevenlabs.io/docs/api-reference/speech-to-text/convert.
Nullable timings are unknown coordinates; documented -Infinity logprob is not confidence.
"""
import math
import time
from uuid import uuid4

from proofkey.contracts import AudioTime, ProcessingReceipt, TranscriptOutput, TranscriptSegment, UnknownLocator
from proofkey.providers.invocations import output_digest
from proofkey.providers.protocols import (TransportRequest, exact_context, finite_limits, read_records, strict_json)

ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"
RESPONSE_FIELDS = frozenset({"language_code", "language_probability", "text", "words", "channel_index",
    "additional_formats", "transcription_id", "entities", "audio_duration_secs", "edited_transcript"})
WORD_FIELDS = frozenset({"text", "type", "logprob", "start", "end", "speaker_id", "characters", "channel_index"})


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


class ElevenLabsClient:
    def __init__(self, transport, *, max_request_bytes=2 * 1024 * 1024, max_response_bytes=2 * 1024 * 1024):
        if not callable(transport):
            raise ValueError("Explicit injected transport required")
        finite_limits(max_request_bytes, max_response_bytes)
        self.transport, self.max_request_bytes, self.max_response_bytes = transport, max_request_bytes, max_response_bytes

    def transcribe(self, record, context):
        exact_context(context, "transcription", "elevenlabs", ENDPOINT)
        if record.mime_type != "audio/wav":
            raise ValueError("Only the declared local WAV route is available; MP3 decoder is unavailable")
        [(record, payload, intake)] = read_records([record], context, self.max_request_bytes)
        duration = max(locator.end_seconds for locator in intake.available_coordinates if locator.kind == "audio_time")
        if duration <= 0 or duration > 10 or duration > context.reserved_usage.get("audio_seconds", 0):
            raise ValueError("Decoded WAV exceeds pre-reserved duration")
        boundary = "proofkey-" + uuid4().hex
        parts = []
        for key, value in (("model_id", context.identity.model), ("timestamps_granularity", "word"),
                           ("webhook", "false"), ("use_multi_channel", "false"), ("file_format", "other")):
            parts.append(("--" + boundary + '\r\nContent-Disposition: form-data; name="' + key + '"\r\n\r\n' + value + "\r\n").encode())
        parts.append(("--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="input.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n").encode() + payload + b"\r\n")
        body = b"".join(parts) + ("--" + boundary + "--\r\n").encode()
        if len(body) > self.max_request_bytes:
            raise ValueError("Encoded multipart byte ceiling exceeded")
        started = time.monotonic()
        response = self.transport(TransportRequest(ENDPOINT, body, "multipart/form-data; boundary=" + boundary,
            context.timeout_seconds, self.max_response_bytes))
        wire = strict_json(response, self.max_response_bytes, allow_negative_infinity=True)
        if (not {"language_code", "language_probability", "text", "words"} <= set(wire) or not set(wire) <= RESPONSE_FIELDS
                or not isinstance(wire["language_code"], str) or not wire["language_code"]
                or not _number(wire["language_probability"]) or not 0 <= wire["language_probability"] <= 1
                or not isinstance(wire["text"], str) or not wire["text"].strip() or not isinstance(wire["words"], list)
                or wire.get("channel_index") not in (None, 0)):
            raise ValueError("Invalid or unsupported ASR response shape")
        if "audio_duration_secs" in wire and (not _number(wire["audio_duration_secs"]) or not 0 <= wire["audio_duration_secs"] <= duration):
            raise ValueError("Invalid duration metadata")
        segments = []
        for item in wire["words"]:
            if (not isinstance(item, dict) or not {"text", "type", "logprob"} <= set(item) or not set(item) <= WORD_FIELDS
                    or not isinstance(item["text"], str) or item["type"] not in {"word", "spacing", "audio_event"}
                    or type(item["logprob"]) not in (int, float) or math.isnan(item["logprob"]) or item["logprob"] > 0
                    or item.get("channel_index") not in (None, 0)):
                raise ValueError("Invalid ASR word shape")
            start, end = item.get("start"), item.get("end")
            if start is not None and not _number(start) or end is not None and not _number(end):
                raise ValueError("Invalid nonfinite word timing")
            if start is None or end is None:
                locator = UnknownLocator(reason="ASR_word_timing_not_supplied")
            elif not 0 <= start <= end <= duration:
                raise ValueError("ASR coordinates outside original WAV")
            else:
                locator = AudioTime(kind="audio_time", start_seconds=float(start), end_seconds=float(end))
            segments.append(TranscriptSegment(text=item["text"], locator=locator))
        output = TranscriptOutput(kind="transcript", text=wire["text"], segments=segments)
        return ProcessingReceipt(invocation_id=context.invocation_id, role="transcription", provider="elevenlabs",
            requested_model=context.identity.model, observed_model=None, provider_request_id=response.request_id,
            prompt_hash=context.identity.prompt_hash, version=context.identity.version, input_hashes=context.identity.input_hashes,
            mode="synthetic", status="completed", latency_seconds=time.monotonic() - started, usage={}, output=output,
            output_hashes=[output_digest(output)], available_coordinates=[segment.locator for segment in segments],
            processed_at=context.catalog.clock.now(), reason="Injected ASR fixture; native model and billed usage are unknown")
