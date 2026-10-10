# Project documents

Start with the [compact architecture](architecture.md): the shipped model experiment, the proposed integration harness, and the next evidence needed. The [detailed design reference](architecture-reference.md) retains the original ontology, workflows, sources and requirements.

- [Model CLI and Docker guide](../tools/dwelly_model/README.md)
- [Current release verification](model-release-verification.md)
- [Team data intake: 10–20 eval cases and 10–20 real examples](model-team-intake.md)
- [Public development data and provenance](../data/dwelly-public-cases/README.md)
- [Historical deterministic pilot verification](pilot-verification.md)
- [Case-by-case reference review](verification/dwelly-reference-review-2026-10-10.md)

The two architecture documents use fixed PNG previews under `diagrams/stable/` so the viewer's fonts cannot clip the labels. Each preview links to a zoomable SVG and editable Mermaid source. Older files directly under `diagrams/` remain historical. The full design describes a target runtime beyond the standalone package shipped here. Passing offline tests does not establish live model quality, operational integration or submission readiness.
