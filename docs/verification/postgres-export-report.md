# Pinned dataset input export

Implemented `tools.dwelly_service.dataset_export.export_decision_input(store, *, case_id, revision, expected_snapshot_hash, input_id, provenance, as_of)` and a PostgreSQL-only CLI. The callable accepts an existing SQLite `CaseStore` or `PostgresCaseStore`; it always calls `store.get(case_id, revision)` with an explicit nonnegative integer revision and requires the caller's expected snapshot hash. Both stores validate the complete immutable history through their existing `get` contract. Output is a detached dictionary containing only `schema_version`, `visibility`, `input_id`, `source`, `snapshot`, and `provenance`.

Provenance is closed to `source_kind`, `source_id`, and `collected_at`. Its accepted source kinds, nonempty source ID, and RFC3339 collection timestamp follow the canonical v1 schema. Values are preserved; the adapter does not assert that operator-supplied origin claims were independently verified. Event occurrence times must be no later than the timezone-aware `as_of` cutoff.

The CLI reads credentials only from `PROOFKEY_DATABASE_URL`, with optional `PROOFKEY_DATABASE_SCHEMA`. Example with those variables already configured:

```sh
python -m tools.dwelly_service.dataset_export \
  --case-id demo-1 --revision 1 \
  --expected-snapshot-hash 43c0ac8677860df1d6c23e9dac3b82672515b4c8057c250f306a00db8b722cc7 \
  --input-id input-1 --source-kind synthetic --source-id fixture-1 \
  --collected-at 2026-10-10T10:00:00Z --as-of 2026-10-10T11:00:00Z \
  --output /absolute/new/path/input-1.json
```

It does not migrate or create a database. Output uses exclusive creation, mode `0600`, and `O_NOFOLLOW` where available. Existing files/symlinks are rejected. On a write failure it removes the incomplete file only when its device/inode still match the file this call created; a concurrent replacement is retained. Errors do not print the database URL or case contents.

There is deliberately no SQLite CLI opener: creating a new `JobStore` invokes recovery and can mark running benchmark jobs interrupted. SQLite callers must pass their already-owned `CaseStore` to the function. Tests verify that an existing running job remains unchanged and that rejected SQLite CLI arguments do not open or recover its database.

## Verification and TDD

Wrote tests first and observed failure because the adapter did not exist. After the initial implementation, added and reproduced the unsafe SQLite CLI behavior before removing that path; file-privacy/cleanup regressions were added before the corresponding implementation.

- `PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey /tmp/proofkey-postgres-tests-20261010/bin/python -m unittest discover -s tests -p test_dataset_export.py -v`: **11 tests passed**, including live local PostgreSQL/SQLite canonical byte parity and a real PostgreSQL CLI export/retry.
- With the same environment/interpreter, `-m unittest discover -s tools/dwelly_service/tests -v`: **84 tests passed**, including local PostgreSQL and HTTP regressions. Tests use isolated schemas and temporary local SQLite stores.
- A bare repository-root `unittest discover` found zero tests; the explicit discovery commands above are the relevant receipts, not a claim that every repository test suite ran.

The parity fixture exports revision 1 after revision 2 already exists. It preserves `source={case_id: demo-1, revision: 1, snapshot_hash: 43c0ac8677860df1d6c23e9dac3b82672515b4c8057c250f306a00db8b722cc7}` and provenance `{source_kind: synthetic, source_id: fixture-1, collected_at: 2026-10-10T10:00:00Z}`. Independently read back canonical input bytes SHA-256: `843704cec493278030dd62ef716d10a28277b959835483c52786752a76be21a0`; canonical CLI bytes including the final newline: `8ddf645c0b665529b4a0571fb606c1175910a6887af7fe528bd54692695650a2`.

## Limits

This is input extraction, not full train/evaluation integration or human calibration. It creates no labels, criteria, manifests, model runs, or review claims. No existing dataset/manifest/ZIP was modified, and no paid provider was called. It relies on the specified stores' existing full-history validation contract rather than accepting arbitrary unvalidated store implementations. The v1 schema lacks `observed_at`; checking `occurred_at <= as_of` cannot establish when evidence became available and does not prove complete temporal leakage prevention. The result remains a `local_fixture` with pending analysis and no operational effects, even when persisted in PostgreSQL.
