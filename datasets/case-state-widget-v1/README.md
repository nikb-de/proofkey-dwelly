# Case-state development dataset

Start with [`development/manifest.jsonl`](development/manifest.jsonl). Each line binds one evidence-only input to a separate author reference, exact file hashes, source commit, case family and exclusions. The checked-in package contains **16 snapshots**, not 16 independent cases:

- `case-002`: 6 snapshots including start.
- `case-002-n4`: 8 snapshots including start, same `case-002` family.
- `minimal`: 2 snapshots, a UI fixture rather than a business evaluation.

All records are `development`, `author_labels_unvalidated`, and `eligible_for_training: false`. Keep related snapshots and branches together when allocating future splits. The reference contains the author's answer; never concatenate it into the inference input.

Raw source JSON lives in [`../../case-state-widget/`](../../case-state-widget/). [`manifest.json`](manifest.json) pins the upstream commit and original source hashes. Viewer implementation files were locally hardened; original implementation hashes are provenance, while all three source JSON files remain unchanged and are verified at load time.

To inspect the data, run from the repository root:

```sh
python3 -m tools.dwelly_analysis serve --port 8093
```

Open `http://127.0.0.1:8093`. To regenerate a package into a new directory:

```sh
python3 -m tools.dwelly_analysis export --output /tmp/proofkey-state-dataset-new
```

The exporter refuses to overwrite existing directories. Read the [contract](../../contracts/analysis-v1/README.md) and [workbench guide](../../docs/analysis-workbench.md) before connecting a model runner. This format is not silently converted to frozen intake v1 or the legacy next-contact output format. Human reference review and independent cases are still required before treating this as a training/evaluation benchmark.
