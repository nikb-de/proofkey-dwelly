# Dataset team handoff v1 — verification receipt

## Delivered

- Source: `datasets/team-handoff-v1/`.
- Archive: `outputs/dataset-handoff/proofkey-training-eval-kit-v1-2026-10-10.zip`.
- Archive bytes: 72,360; 58 files including generated exact-file integrity inventory.
- Archive SHA-256: `28adf59710dd27952ba9021b1d91b884e9084895527cd06db709f91ce26c5f96`.

## Fresh checks

- Original kit and detached archive copy both: 13 validator tests passed.
- Original kit and detached archive copy both: 9 valid development rows, 3 synthetic families, 3 episodes, 0 transitions, 0 reviewed eligible rows.
- Existing backend contract suite: 20 passed.
- All 8 canonical schemas byte-identical to repository originals.
- All 21 relative documentation links resolve within the kit.
- ZIP integrity and all 57 content file SHA-256 entries verified after extraction.
- Fixture implementer independently reproduced all 9 snapshots through real CaseStore create/append in isolated temporary SQLite storage and verified deterministic rebuild bytes.
- Independent final review approved after correcting standalone example links. Dependency-error regression was observed failing, then passed after the import handling correction.

The detached test directory is disposable verification evidence; the ZIP and source kit are the deliverables. No source backend files, user draft datasets, secrets or private conversations were changed or included. No provider calls, training, semantic judging or external publishing occurred. Valid data formatting does not establish correct labels or model quality.
