# Design

The rendered document must not depend on host Mermaid HTML-label measurements. Each active diagram uses an immutable PNG preview, with linked SVG for zoom and Mermaid source for editing. Existing source text and architecture semantics remain unchanged.

Use the already verified standalone SVGs as the rendering input, retain their source hashes, and rasterize in a browser at 2x resolution. Validate the image resources in a hostile-font HTML fixture at 390px and 1100px viewports. The Codex UI is not accessible to the automation surface; do not claim native viewer verification.

This is a bounded documentation bug fix; no OpenSpec runtime requirements change. The documentation capability records stable previews, editable sources and honest verification. Archive after verifying the assets and document references.
