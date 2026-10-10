# Stable architecture diagrams

The active architecture documents embed PNGs, not live Mermaid. This prevents document-viewer CSS and font metrics from resizing text inside Mermaid's fixed HTML label boxes.

Each diagram has three files: `.mmd` (editable source), `.svg` (standalone vector view), and `.png` (stable 2x-resolution preview). The six sources are unchanged from the preceding compact architecture revision. The underlying SVGs match the previously retained standalone render exactly; PNGs were rasterized again at 2x resolution.

`render-receipt.json` records source and asset hashes, dimensions and browser checks. The original HTML-label clipping class was reproduced by changing the host font size after layout. All six PNGs loaded without horizontal clipping at 390px and 1100px viewport widths under hostile host typography. Large reference diagrams should be opened directly for zoom rather than read as thumbnails.

Native Codex UI inspection was unavailable because that app is excluded from the computer-use surface. This is not a claim that its renderer was directly inspected. No runtime, model, policy or operational integration changed.
