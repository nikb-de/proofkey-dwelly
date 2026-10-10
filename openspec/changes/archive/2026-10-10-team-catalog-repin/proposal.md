# Repin the team catalog after the main merge

Main updated the 002-N4 negative branch without updating the platform's separately pinned source manifest. The merged analysis service correctly rejected that source with `Source hash mismatch`.

Refresh the single changed source hash and pin the complete team snapshot to main commit `c1c8539725a42162b452c8125e747afdf4b16580`. Preserve source JSON, catalog shape, fail-closed integrity validation, legacy fixtures and historical evaluation receipts. This is a data-binding repair, not a policy or schema change.
