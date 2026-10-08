"""Create only tiny public synthetic media; no source documents or private input."""
import hashlib
import io
import json
import math
import struct
import wave
import subprocess
import shutil
import zlib
import sys
from pathlib import Path
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import EncodedStreamObject, NameObject


def _pdf_objects(objects):
    """Serialize hand-built finite synthetic PDF objects without tree flattening."""
    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, content in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{number} 0 obj\n{content}\nendobj\n".encode())
    xref = len(payload)
    payload.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode())
    payload.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(payload)


def _compressed_pdf_route(*, object_stream=False, escaped=False, hybrid=False, previous=False):
    """Real cross-reference/object-stream routes with controlled 8 MiB+1 expansion."""
    payload = bytearray(b"%PDF-1.5\n")
    offsets = [0]
    if object_stream:
        objects = [b"<< /Type /Pages /Kids [2 0 R] /Count 1 >>",
                   b"<< /Type /Page /Parent 1 0 R /MediaBox [0 0 72 72] >>"]
        raw = b"5 0 << /Type /Catalog /Pages 1 0 R >>" + b" " * (8 * 1024 * 1024 + 1)
        encoded = zlib.compress(raw)
        objects.append(f"<< /Type /ObjStm /N 1 /First 4 /Filter /FlateDecode /Length {len(encoded)} >>\nstream\n".encode()
                       + encoded + b"\nendstream")
        root, size = 5, 6
    else:
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                   b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>"]
        root, size = 1, 5
    for number, content in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{number} 0 obj\n".encode() + content + b"\nendobj\n")
    stream_offset = len(payload)
    offsets.append(stream_offset)
    rows = [struct.pack(">BIH", 0, 0, 65535)] + [struct.pack(">BIH", 1, offset, 0) for offset in offsets[1:]]
    if object_stream:
        rows.append(struct.pack(">BIH", 2, 3, 0))
    raw = b"".join(rows) + (b" " * (8 * 1024 * 1024 + 1) if not object_stream else b"")
    encoded = zlib.compress(raw)
    type_name, filter_name = ("/Ty#70e /XR#65f", "/Flate#44ecode") if escaped else ("/Type /XRef", "/FlateDecode")
    payload.extend(f"4 0 obj\n<< {type_name} /Size {size} /Root {root} 0 R /W [1 4 2] /Filter {filter_name} /Length {len(encoded)} >>\nstream\n".encode()
                   + encoded + b"\nendstream\nendobj\n")
    start = stream_offset
    if hybrid or previous:
        start = len(payload)
        payload.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]:
            payload.extend(f"{offset:010d} 00000 n \n".encode())
        route = ("/XRef#53tm" if hybrid else "/Pr#65v") if escaped else ("/XRefStm" if hybrid else "/Prev")
        payload.extend(f"trailer\n<< /Size {size} /Root {root} 0 R {route} {stream_offset} >>\n".encode())
    payload.extend(f"startxref\n{start}\n%%EOF\n".encode())
    return bytes(payload)


def page_tree_fixtures():
    catalog = "<< /Type /Catalog /Pages 2 0 R >>"
    leaf = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>"
    files = {
        "repeated-page.pdf": _pdf_objects([catalog, "<< /Type /Pages /Kids [3 0 R 3 0 R] /Count 2 >>", leaf]),
        "cyclic-pages.pdf": _pdf_objects([catalog, "<< /Type /Pages /Kids [2 0 R] /Count 1 >>"]),
        "oversized-count.pdf": _pdf_objects([catalog, "<< /Type /Pages /Kids [3 0 R] /Count 9223372036854775807 >>", leaf]),
        "two-pages.pdf": _pdf_objects([catalog, "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>", leaf, leaf]),
    }
    files["classic-v15.pdf"] = files["two-pages.pdf"].replace(b"%PDF-1.4", b"%PDF-1.5", 1)
    objects = [catalog]
    for index in range(12):
        child = index + 3
        objects.append(f"<< /Type /Pages /Kids [{child} 0 R {child} 0 R] /Count {2 ** (12-index)} >>")
    objects.append(leaf)
    files["repeated-subtree.pdf"] = _pdf_objects(objects)
    objects = [catalog]
    for index in range(40):
        objects.append(f"<< /Type /Pages /Kids [{index+3} 0 R] /Count 1 >>")
    objects.append(leaf)
    files["deep-pages.pdf"] = _pdf_objects(objects)
    kids = " ".join(f"{index} 0 R" for index in range(3, 104))
    files["too-many-pages.pdf"] = _pdf_objects([catalog, f"<< /Type /Pages /Kids [{kids}] /Count 101 >>", *([leaf] * 101)])
    files.update({"xref-stream-bomb.pdf": _compressed_pdf_route(),
                  "escaped-xref-stream-bomb.pdf": _compressed_pdf_route(escaped=True),
                  "hybrid-xref-stream-bomb.pdf": _compressed_pdf_route(hybrid=True),
                  "escaped-hybrid-xref-stream-bomb.pdf": _compressed_pdf_route(hybrid=True, escaped=True),
                  "previous-xref-stream-bomb.pdf": _compressed_pdf_route(previous=True),
                  "object-stream-bomb.pdf": _compressed_pdf_route(object_stream=True)})
    return files


def write_page_tree_fixtures():
    """Add only page-tree controls without regenerating existing encrypted media."""
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "provenance.json").read_text())
    files = {item["name"]: item for item in manifest["files"]}
    for name, payload in page_tree_fixtures().items():
        (root / name).write_bytes(payload)
        files[name] = {"name": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    manifest["files"] = [files[name] for name in sorted(files)]
    manifest["page_tree_controls"] = "Hand-built public PDFs: repeated references/subtree, cycle, depth 40, oversized Count and 101 pages; two-page valid control"
    manifest["compressed_pdf_controls"] = "Real XRef/ObjStm routes with finite 8 MiB+1 expansion controls, escaped names, hybrid XRefStm and Prev routes"
    (root / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    root = Path(__file__).resolve().parent
    files = {"synthetic.txt": b"SYNTHETIC NAME reports damaged box.\n",
             "synthetic.json": b'{"synthetic":true,"box":"damaged"}\n',
             "supplied.transcript": b"Synthetic supplied transcript: box is damaged.\n",
             "malformed.json": b'{bad json', "malformed.png": b'bad image',
             "malformed.wav": b'bad wave', "malformed.pdf": b'bad pdf',
             "malformed.txt": b'\xff\xfe', "nonfinite.json": b'{"value":NaN}',
             "unsupported.bin": b'SYNTHETIC unsupported bytes',
             # ID3 header alone is not a valid MP3: finite decoder-unavailable control.
             "synthetic.mp3": b'ID3\x04\x00\x00\x00\x00\x00\x00'}
    for extension, fmt in (("png", "PNG"), ("jpg", "JPEG")):
        buffer = io.BytesIO()
        Image.new("RGB", (4, 3), (100, 150, 200)).save(buffer, format=fmt)
        files[f"synthetic.{extension}"] = buffer.getvalue()
    for encrypted in (False, True):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        if encrypted:
            writer.encrypt("synthetic-password")
        buffer = io.BytesIO()
        writer.write(buffer)
        files["encrypted.pdf" if encrypted else "synthetic.pdf"] = buffer.getvalue()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"".join(struct.pack("<h", int(2000 * math.sin(2 * math.pi * 440 * n / 8000))) for n in range(800)))
    files["synthetic.wav"] = buffer.getvalue()
    files["truncated.wav"] = buffer.getvalue()[:50]
    writer = PdfWriter()
    page = writer.add_blank_page(width=72, height=72)
    content = EncodedStreamObject()
    content._data = zlib.compress(b" " * (8 * 1024 * 1024 + 1))
    content[NameObject("/Filter")] = NameObject("/FlateDecode")
    page[NameObject("/Contents")] = writer._add_object(content)
    buffer = io.BytesIO()
    writer.write(buffer)
    files["compressed-bomb.pdf"] = buffer.getvalue()
    writer = PdfWriter()
    for _ in range(2):
        page = writer.add_blank_page(width=72, height=72)
        content = EncodedStreamObject()
        content._data = zlib.compress(b" " * 5_000_000)
        content[NameObject("/Filter")] = NameObject("/FlateDecode")
        page[NameObject("/Contents")] = writer._add_object(content)
    buffer = io.BytesIO()
    writer.write(buffer)
    files["compressed-aggregate.pdf"] = buffer.getvalue()
    files.update(page_tree_fixtures())
    encoder = shutil.which("ffmpeg")
    encoder_version = None
    if encoder:
        encoder_version = subprocess.run([encoder, "-version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
        encoded = subprocess.run([encoder, "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
            "-fflags", "+bitexact", "-map_metadata", "-1", "-codec:a", "libmp3lame", "-write_xing", "0", "-f", "mp3", "pipe:1"],
            input=files["synthetic.wav"], capture_output=True, check=True)
        files["synthetic.mp3"] = encoded.stdout
    manifest = {"source": "generated public synthetic fixtures; no private imports",
                "license": "Apache-2.0", "semantic_readiness": False,
                "notes": "blank PDF; solid images; 0.1-second tone, not speech; MP3 encoded from tone when fixture-only ffmpeg is present",
                "fixture_only_mp3_encoder": encoder_version,
                "files": []}
    for name, payload in sorted(files.items()):
        (root / name).write_bytes(payload)
        manifest["files"].append({"name": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    (root / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["--page-tree-only"]:
        write_page_tree_fixtures()
    else:
        main()
