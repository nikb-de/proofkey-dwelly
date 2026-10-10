# Project documents

Start with the [compact architecture](architecture.md), the [platform operations guide](platform-operations.md), and the [platform API contract](../contracts/platform-v1/README.md). The historical detailed design reference is retained in Git history.

- [Model CLI and Docker guide](../tools/dwelly_model/README.md)
- [Current release verification](model-release-verification.md)
- [Team data intake: 10–20 eval cases and 10–20 real examples](model-team-intake.md)
- [Public development data and provenance](../data/dwelly-public-cases/README.md)
- [Historical deterministic pilot verification](pilot-verification.md)
- [Case-by-case reference review](verification/dwelly-reference-review-2026-10-10.md)

The two architecture documents use fixed PNG previews under `diagrams/stable/` so the viewer's fonts cannot clip the labels. Each preview links to a zoomable SVG and editable Mermaid source. Older files directly under `diagrams/` remain historical. The full design describes a target runtime beyond the standalone package shipped here. Passing offline tests does not establish live model quality, operational integration or submission readiness.

## Team-authored scenarios and catalog

- [Decision-episode authoring kit](dataset-drafts/2026-10-10-decision-episodes/README.md)
- [Narrative cases 051–100](../data/synthetic-cases-051-100/README.md)
- [Negative branches 001–050](../data/negative-branches-001-050/README.md)
- [GitHub-backed case catalog](../case-state-widget/GITHUB.md)

The current team widget sources are preserved in `case-state-widget/cases/`; legacy fixture IDs remain distinct from namespaced team analysis cases. Labels remain unreviewed development material.
