"""Finite format decoding receipts, separate from semantic extraction and ASR."""
from dataclasses import dataclass
import hashlib
import io
import json
import math
import time
import uuid
import wave
import warnings
import zlib
from proofkey.contracts import (ProcessingReceipt, AssertionsOutput, TranscriptOutput,
                               TranscriptSegment, TextSpan, PageRegion, Region, AudioTime)
from proofkey.identity import fingerprint
from proofkey.evidence.catalog import EvidenceCatalog, EvidenceAccessDenied


@dataclass(frozen=True)
class IntakeLimits:
    max_bytes: int = 8 * 1024 * 1024
    max_pixels: int = 4_000_000
    max_pages: int = 100
    max_audio_seconds: float = 120

    def __post_init__(self):
        for name, ceiling in (("max_bytes", 8 * 1024 * 1024), ("max_pixels", 4_000_000), ("max_pages", 100)):
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= ceiling:
                raise ValueError("Limits must be positive within the finite hard ceiling")
        if (type(self.max_audio_seconds) not in (int, float) or not math.isfinite(self.max_audio_seconds)
                or not 0 < self.max_audio_seconds <= 120):
            raise ValueError("Audio ceiling must be finite and at most 120 seconds")


class DecoderUnavailable(Exception):
    pass


def _reject_constant(value):
    raise ValueError("Nonfinite JSON value")


def _decode(payload, mime, limits):
    empty = AssertionsOutput(kind="assertions", assertions=[])
    semantic = "Actual byte format decoded; semantic extraction/model processing unfinished"
    if mime in ("text/plain", "application/json", "text/x-supplied-transcript"):
        text = payload.decode("utf-8", errors="strict")
        if mime == "application/json":
            json.loads(text, parse_constant=_reject_constant)
        coordinate = TextSpan(kind="text_span", start=0, end=len(text))
        if mime == "text/x-supplied-transcript":
            return TranscriptOutput(kind="transcript", text=text,
                segments=[TranscriptSegment(text=text, locator=coordinate)]), [coordinate], "Supplied transcript decoded as text; not ASR; semantic processing unfinished"
        return empty, [coordinate], semantic
    if mime in ("image/png", "image/jpeg"):
        try:
            from PIL import Image
        except ImportError as exc:
            raise DecoderUnavailable("Image decoder unavailable") from exc
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as image:
                if image.format != {"image/png": "PNG", "image/jpeg": "JPEG"}[mime]:
                    raise ValueError("MIME/content mismatch")
                width, height = image.size
                if width * height > limits.max_pixels:
                    raise ValueError("Pixel ceiling exceeded")
                image.verify()
            with Image.open(io.BytesIO(payload)) as image:
                image.load()
        return empty, [PageRegion(kind="page_region", page=1,
            region=Region(x=0, y=0, width=width, height=height, units="pixels"))], semantic
    if mime == "application/pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DecoderUnavailable("PDF decoder unavailable") from exc
        reader = PdfReader(io.BytesIO(payload), strict=True)
        if reader.is_encrypted:
            raise DecoderUnavailable("Encrypted PDF requires a separate approved decryption route")
        if len(reader.pages) > limits.max_pages:
            raise ValueError("PDF page ceiling exceeded")
        coordinates = []
        total = 0
        for number, page in enumerate(reader.pages, start=1):
            # Decode finite text-bearing streams but never manufacture claims.
            content = page.get("/Contents")
            if content is not None:
                content = content.get_object()
                streams = list(content) if isinstance(content, list) else [content]
                for stream in streams:
                    stream = stream.get_object()
                    raw = stream._data
                    filter_name = stream.get("/Filter")
                    if filter_name is None:
                        decoded = raw
                    elif filter_name == "/FlateDecode" and not stream.get("/DecodeParms"):
                        decoder = zlib.decompressobj()
                        decoded = decoder.decompress(raw, limits.max_bytes - total + 1)
                        if decoder.unconsumed_tail or not decoder.eof:
                            raise ValueError("PDF decoded stream ceiling or malformed compression")
                    else:
                        raise DecoderUnavailable("PDF stream filter requires another reviewed finite decoder")
                    total += len(decoded)
                    if total > limits.max_bytes:
                        raise ValueError("Decoded PDF stream ceiling exceeded")
            coordinates.append(PageRegion(kind="page_region", page=number))
        return empty, coordinates, semantic
    if mime == "audio/wav":
        with wave.open(io.BytesIO(payload), "rb") as audio:
            if audio.getcomptype() != "NONE" or audio.getsampwidth() not in (1, 2, 3, 4) or not 1 <= audio.getnchannels() <= 8:
                raise ValueError("Unsupported WAV encoding")
            duration = audio.getnframes() / audio.getframerate()
            if duration > limits.max_audio_seconds:
                raise ValueError("Audio duration ceiling exceeded")
            frames = audio.readframes(audio.getnframes())
            if len(frames) != audio.getnframes() * audio.getnchannels() * audio.getsampwidth():
                raise ValueError("Truncated WAV frames")
        return empty, [AudioTime(kind="audio_time", start_seconds=0, end_seconds=duration)], "Actual WAV bytes decoded; not ASR; semantic/model processing unfinished"
    if mime == "audio/mpeg":
        raise DecoderUnavailable("MP3 decoder unavailable; bytes not validated; no transcription")
    raise DecoderUnavailable("Unsupported media format")


def inspect_content(record, declared_limits, *, catalog=None, auth=None):
    """Decode trusted local bytes, never open a supplied record's source reference.

    declared_limits is a trusted profile IntakeLimits, not a caller narrative.
    completed describes format decoding only; output has no semantic assertions.
    """
    if not isinstance(catalog, EvidenceCatalog):
        raise EvidenceAccessDenied("A trusted catalog and scoped authorization are required")
    record = catalog.resolve_record(record, auth, purpose="inspect")
    if not isinstance(declared_limits, IntakeLimits):
        raise ValueError("A trusted finite IntakeLimits is required")
    started = time.monotonic()
    output, coordinates, status, mode = None, [], "completed", "deterministic"
    payload = None
    try:
        payload = catalog.read_original(record.artifact_id, auth, purpose="inspect", max_bytes=declared_limits.max_bytes)
        output, coordinates, reason = _decode(payload, record.mime_type, declared_limits)
    except DecoderUnavailable as exc:
        status, mode, reason = "unavailable", "unavailable", str(exc)
    except Exception as exc:
        status, reason = "failed", "Format decoding failed: " + type(exc).__name__
    output_hashes = [hashlib.sha256(output.model_dump_json().encode()).hexdigest()] if output else []
    receipt = ProcessingReceipt(invocation_id="format-" + uuid.uuid4().hex, role="extraction", provider="local-format-parser",
        requested_model="no-model", observed_model=None, prompt_hash=fingerprint({"operation": "decode-format-only"}),
        version="format-v1", input_hashes=[record.original_hash], mode=mode, status=status,
        latency_seconds=time.monotonic() - started, usage={"input_bytes": float(len(payload))} if payload is not None else {},
        output=output, output_hashes=output_hashes, available_coordinates=coordinates,
        processed_at=catalog.clock.now(), reason=reason)
    catalog._store(catalog.root / "receipts" / (receipt.invocation_id + ".json"), receipt.model_dump_json().encode())
    return receipt
