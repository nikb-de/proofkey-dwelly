# Case 001 publication contents

The repository publishes the current clean 40-second presentation, its reference and decoded QA screenshots, and the source records needed to trace the journey. Rejected and superseded captures remain in the local archive; excluding them from publication does not delete or relabel them as successful.

## Published presentation

Paths below are relative to this document.

| Artifact | Current repository path |
| --- | --- |
| Model-assisted film | [mobile-40s-clean-final-20261010/Right-onTime-llm-mobile-40s-clean.mp4](mobile-40s-clean-final-20261010/Right-onTime-llm-mobile-40s-clean.mp4) |
| Scripted film | [mobile-40s-clean-final-20261010/Right-onTime-synthetic-mobile-40s-clean.mp4](mobile-40s-clean-final-20261010/Right-onTime-synthetic-mobile-40s-clean.mp4) |
| Execution and source qualification | [mobile-40s-clean-final-20261010/PROVENANCE.md](mobile-40s-clean-final-20261010/PROVENANCE.md) |
| Technical verification and film hashes | [mobile-40s-clean-final-20261010/VERIFICATION.md](mobile-40s-clean-final-20261010/VERIFICATION.md) |
| Capture geometry, timings and source/asset hashes | [mobile-40s-clean-final-20261010/capture.json](mobile-40s-clean-final-20261010/capture.json) |
| Export properties, hashes and decoded-frame checks | [mobile-40s-clean-final-20261010/exports.json](mobile-40s-clean-final-20261010/exports.json) |

The entire `mobile-40s-clean-final-20261010/` directory is published except the raw WebM recordings. It includes the ten `llm-*-mobile.png` / `synthetic-*-mobile.png` scene references, two desktop references, and the five decoded midpoint frames in each of `llm-frames/` and `synthetic-frames/`. The frames at 4, 12, 20, 28 and 36 seconds support comparison with the five intended scenes. Original WebMs under `llm/` and `synthetic/` are local-only.

## Published source and verification evidence

- [Frozen source case](source.case-001-terms.json).
- [Successful scripted capture report](recordings/synthetic-1791642519120-6cb35564/capture-report.json).
- [Successful model-assisted capture report](recordings/llm-1791642541219-2d58c523/capture-report.json).
- The five original model-job records: [1](recordings/llm-1791642541219-2d58c523/model-1.json), [2](recordings/llm-1791642541219-2d58c523/model-2.json), [3](recordings/llm-1791642541219-2d58c523/model-3.json), [4](recordings/llm-1791642541219-2d58c523/model-4.json), [5](recordings/llm-1791642541219-2d58c523/model-5.json).
- All source code, tests, specifications, archived changes and implementation plans associated with the work.
- The entire [platform verification evidence directory](../../verification/platform-live-e2e-2026-10-10/README.md), including failed provider runs, transport diagnostics and the adjudication of ambiguous expectations. Publication does not turn those failures into passes.
- The existing [clean coordination UI verification](../../verification/coordination-review-ui-2026-10-10/README.md) and its canonical complete run remain published.

## Local-only archive

The following are retained locally and excluded from this publication:

- `mobile-40s-clean-20261010/`: the rejected clean capture with encoder padding at the lower border.
- `mobile-40s-final-20261010/`: the superseded labelled mobile presentation.
- `showcase-final-20261010/` and `showcase-v2-20261010/`: earlier presentation iterations.
- All other files under `recordings/`, including the failed first scripted attempt, rejected 50-second films, raw WebMs, pickup recordings, edit manifests and intermediate screenshots. The two successful capture reports and five model-job records listed above are the exceptions.
- The five earlier coordination UI runs `real-e2e-1791642095454-9a34d04e`, `real-e2e-1791642110673-a6b4de09`, `real-e2e-1791642126730-f2493145`, `real-e2e-1791642145169-37febf74` and `real-e2e-1791642167266-570d71e5` under `docs/verification/coordination-review-ui-2026-10-10/`. Four failed; the last was an earlier resumed run. The canonical complete run is `real-e2e-1791642200227-2331def1`.

The archive contains historical failures and superseded outputs, not additional final deliverables. The capture failure and its unresolved triggering condition remain described in [SHOWCASE.md](SHOWCASE.md); the earlier recording failure remains described in [RECORDINGS.md](RECORDINGS.md).

## Historical paths and integrity

Capture reports and manifests are published unchanged. Their `/Users/nbk/...` paths record where screenshots, exports and raw videos existed on the original machine. Those paths are historical provenance and are not portable commands, public URLs, or evidence that a file is included in the repository. Raw WebMs and other local-only artifacts cannot be opened from a fresh clone.

Use the relative paths above for published films and records. Within `mobile-40s-clean-final-20261010/`, a historical screenshot path maps to the file with the same basename; decoded frames use `llm-frames/second-N.png` or `synthetic-frames/second-N.png`. Do not rewrite the immutable JSON merely to change its historical paths. The source SHA-256 remains `fc1f55e8258346b53f77b5cce03ae6fb7e0b227433daab19894caa4da8d160cf`; model identities, source bindings and film hashes remain as recorded.

To reproduce the read-only presentation, use the repository-relative source/data files and scripts in [SHOWCASE.md](SHOWCASE.md), writing to a new output directory. Recreating the original live model run is a separate paid operation; it is not required to play the presentation or inspect its published receipts.

Technical verification does not establish user aesthetic approval, customer authentication, carrier participation or physical delivery. The films reconstruct a synthetic source case and local sandbox records; the model-assisted film reuses five historical responses.
