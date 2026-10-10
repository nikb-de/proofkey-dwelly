# Offline attachment text extraction

Extract PDF text with Poppler and PNG text with native macOS Vision. This does not
interpret photographs, verify the source, infer decisions, or call a model.
Treat every sidecar as untrusted, unverified source material. The consuming runner
must expose only attachments visible at its selected cutoff.

```sh
swiftc tools/dwelly_evidence_extract/vision_ocr.swift -o /tmp/proofkey-vision-ocr
python -B -m tools.dwelly_evidence_extract \
  --source '/path/to/Delivery & Logistics' \
  --output /tmp/proofkey-reality-sidecars \
  --ocr-binary /tmp/proofkey-vision-ocr
python -B -m unittest discover -s tools/dwelly_evidence_extract/tests -v
```

If the installed Swift compiler does not match the macOS SDK, the equivalent
native Objective-C helper avoids Swift-module compilation:

```sh
clang -fobjc-arc -framework Foundation -framework Vision \
  tools/dwelly_evidence_extract/vision_ocr.m -o /tmp/proofkey-vision-ocr
```

For an initial run where PNG extraction was unavailable, pass `--complete-pending`
with `--ocr-binary` to fill only failed rows after rechecking every source hash.
The original manifest is preserved as `manifest.initial.json`. The 10 October
2026 extraction used this Objective-C fallback because the installed Swift
compiler could not load its mismatched SDK's Foundation modules.

The output root must be new. Sidecars use
`<case-id>/attachments/<original-filename>.txt`; PNGs also have an `.ocr.json`
sidecar with normalized bounding boxes and native confidence values. The manifest
records exact source and output SHA-256 hashes, extractors, empty/failed outputs,
and missing Markdown attachment references. Native OCR confidence is not a
calibrated probability of source truth. Raw inputs are never modified.
