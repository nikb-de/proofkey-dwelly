# Clean presentation verification

- Two videos: exactly40.000 seconds each,1080×1920,30fps,1,200 frames, silent H.264.
- Full decode and all ten encoded-footer checks passed. Midpoint frames at4,12,20,28,36seconds match the expected mobile screens; mean absolute pixel error3.66–5.00 on a0–255channel scale after normalization.
- No Demo, Sandbox, Replay, technical model commentary or evidence controls appear in either presentation. Exact offer terms, historical advice and booking status are preserved.
- UI suite:100passed, no failures or skipped tests. Independent review inspected all ten clean scene/mode combinations and found no blocker.
- All capture requests are read-only; browser errors and non-GET requests are zero. Source bundles have the same hashes as the prior labelled presentation.
- Source and execution qualifications remain in `PROVENANCE.md`. Technical verification is not user aesthetic approval.

| Artifact | SHA-256 |
|---|---|
| Model-assisted | `a9c308f8c74ef510598ea590f9b568951b72bffc9a13076e7e1c460dab405774` |
| Scripted | `506dd9b86b69ab389e8492b8633132d17a6aaa2bcea4283a199832c9a0478323` |

Copies in `/Users/nbk/Downloads/` match these hashes. The earlier failed clean exports remain under `../mobile-40s-clean-20261010/` and must not be used for presentation.
