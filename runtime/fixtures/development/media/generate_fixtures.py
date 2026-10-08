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
from pathlib import Path
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import EncodedStreamObject, NameObject


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
    main()
