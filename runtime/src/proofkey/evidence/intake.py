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
    max_pdf_nodes: int = 512
    max_pdf_references: int = 1024
    max_pdf_depth: int = 32

    def __post_init__(self):
        for name, ceiling in (("max_bytes", 8 * 1024 * 1024), ("max_pixels", 4_000_000), ("max_pages", 100),
                              ("max_pdf_nodes", 512), ("max_pdf_references", 1024), ("max_pdf_depth", 32)):
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


def _bounded_pdf_pages(reader, limits):
    """Traverse raw page-tree objects without pypdf's unbounded flatten API.

    Count is checked against visited leaves only; never used to allocate or to
    skip traversal. Repeated references (including cycles) fail before resolve.
    The bounded recursion cannot exceed the trusted depth ceiling of 32.
    """
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject
    seen_references, seen_nodes, pages = set(), set(), []
    nodes = references = 0

    def visit(reference, depth):
        nonlocal nodes, references
        if depth > limits.max_pdf_depth:
            raise ValueError("PDF page-tree depth ceiling exceeded")
        nodes += 1
        if nodes > limits.max_pdf_nodes:
            raise ValueError("PDF page-tree node ceiling exceeded")
        if isinstance(reference, IndirectObject):
            references += 1
            identity = (reference.idnum, reference.generation)
            if references > limits.max_pdf_references or identity in seen_references:
                raise ValueError("PDF repeated reference or reference ceiling exceeded")
            seen_references.add(identity)
            node = reference.get_object()
        else:
            node = reference
        if not isinstance(node, DictionaryObject) or id(node) in seen_nodes:
            raise ValueError("Malformed or repeated PDF page-tree node")
        seen_nodes.add(id(node))
        kind = node.get("/Type")
        if kind == "/Page":
            if "/Kids" in node or len(pages) >= limits.max_pages:
                raise ValueError("Malformed page or PDF page ceiling exceeded")
            pages.append(node)
            return 1
        if kind != "/Pages" or "/Kids" not in node or "/Count" not in node:
            raise ValueError("Malformed PDF page-tree branch")
        kids, count = node.raw_get("/Kids"), node.raw_get("/Count")
        # Do not resolve an indirect Kids container; only the canonical finite
        # array is accepted. References are resolved individually under budget.
        if not isinstance(kids, ArrayObject) or not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("Malformed page-tree children or Count")
        if len(kids) > limits.max_pdf_nodes - nodes:
            raise ValueError("PDF page-tree child node ceiling exceeded")
        actual = 0
        for child in kids:
            actual += visit(child, depth + 1)
        if count != actual:
            raise ValueError("PDF Count does not match bounded observed leaves")
        return actual

    root = reader.trailer["/Root"]
    if not isinstance(root, DictionaryObject) or "/Pages" not in root:
        raise ValueError("PDF catalog has no page tree")
    visit(root.raw_get("/Pages"), 1)
    return pages


def _finite_pdf_reader(payload):
    """pypdf 6.10.0 boundary adapter with zero compressed-object decode budget.

    Only classic xref tables are supported. Dispatch is parsed by the pinned
    PDF parser, including escaped dictionary names; no raw marker scan decides
    whether streams are safe. Hybrid/Prev routes cannot swallow unsupported
    exceptions or fall back to object-stream repair/decompression.
    """
    from pypdf import PdfReader
    from pypdf.generic import DictionaryObject, read_object
    from pypdf._utils import read_non_whitespace
    from importlib.metadata import version, PackageNotFoundError
    try:
        tested_version = version("pypdf")
    except PackageNotFoundError as exc:
        raise DecoderUnavailable("PDF decoder dependency metadata unavailable") from exc
    if tested_version != "6.10.0":
        raise DecoderUnavailable("PDF finite decoder requires reviewed pypdf 6.10.0 private-hook compatibility")

    class ClassicFiniteReader(PdfReader):
        def _compressed_route(self, *args, **kwargs):
            raise DecoderUnavailable("PDF compressed XRef/object-stream and repair routes are unsupported by the finite basic decoder")

        _read_pdf15_xref_stream = _compressed_route
        _get_object_from_stream = _compressed_route
        _rebuild_xref_table = _compressed_route

        def _read_xref_tables_and_trailers(self, stream, startxref, xref_issue_nr):
            if xref_issue_nr:
                raise ValueError("Invalid classic xref pointer")
            self.xref, self.xref_free_entry, self.xref_objStm = {}, {}, {}
            self.trailer = DictionaryObject()
            seen = set()
            while startxref is not None:
                if not isinstance(startxref, int) or startxref < 0 or startxref >= len(payload):
                    raise ValueError("Invalid xref offset")
                if startxref in seen or len(seen) >= 64:
                    raise ValueError("PDF xref chain cycle or section ceiling exceeded")
                seen.add(startxref)
                stream.seek(startxref)
                first = read_non_whitespace(stream)
                if first != b"x":
                    self._compressed_route()
                # The original pinned classic-table parser starts after 'x'.
                self._read_standard_xref_table(stream)
                first = read_non_whitespace(stream)
                if not first:
                    raise ValueError("Missing classic PDF trailer")
                stream.seek(-1, 1)
                trailer = read_object(stream, self)
                if not isinstance(trailer, DictionaryObject):
                    raise ValueError("Invalid classic PDF trailer")
                if "/XRefStm" in trailer:
                    self._compressed_route()
                for key, value in trailer.items():
                    if key not in self.trailer:
                        self.trailer[key] = value
                startxref = trailer.get("/Prev")

    return ClassicFiniteReader(io.BytesIO(payload), strict=True)


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
            reader = _finite_pdf_reader(payload)
        except ImportError as exc:
            raise DecoderUnavailable("PDF decoder unavailable") from exc
        if reader.is_encrypted:
            raise DecoderUnavailable("Encrypted PDF requires a separate approved decryption route")
        pages = _bounded_pdf_pages(reader, limits)
        coordinates = []
        total = 0
        for number, page in enumerate(pages, start=1):
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
        version="format-v2", input_hashes=[record.original_hash], mode=mode, status=status,
        latency_seconds=time.monotonic() - started, usage={"input_bytes": float(len(payload))} if payload is not None else {},
        output=output, output_hashes=output_hashes, available_coordinates=coordinates,
        processed_at=catalog.clock.now(), reason=reason)
    catalog._store(catalog.root / "receipts" / (receipt.invocation_id + ".json"), receipt.model_dump_json().encode())
    return receipt
