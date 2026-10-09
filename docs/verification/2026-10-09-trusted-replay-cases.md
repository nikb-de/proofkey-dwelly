# Trusted synthetic replay cases — J06 evidence

Status: **installed acceptance passed; final full regression, independent whole-change review and archival pending**. This is a bounded trusted Python integration hook. J06 is not yet closed. No general release-verifier, native-service, human-approval or timed-adaptation claim follows.

## Candidate and target

Executable acceptance candidate: `c26d74325dec97d67cb9165ddaaab52549562ed0`, following preparation/configuration implementation through `e4b3b41` and the external example/driver checkpoint `aa9a209`. Later changes to this verification document and the support register are documentation only, outside `runtime/`.

Observed target: CPython 3.12.14, macOS 26.5.2 arm64. A fresh virtual environment outside the checkout installed the existing nineteen pinned runtime/API wheels plus the separately staged setuptools 84.0.0 build backend. All twenty artifact hashes were validated before use; there was no dependency acquisition, network request or provider/model invocation.

The reusable command is:

```text
SOURCE_PYTHON -I -B runtime/scripts/verify_synthetic_provisioning.py
  --commit c26d74325dec97d67cb9165ddaaab52549562ed0
  --wheelhouse ABSOLUTE_EXISTING_WHEELHOUSE
  --dependency-receipt ABSOLUTE_EXISTING_ARTIFACT_RECEIPT
  --output ABSOLUTE_NEW_PRIVATE_DIRECTORY
```

The actual command, absolute private paths, raw stdout/stderr, exit status, durations, source inventories, authority-bearing synthetic state and per-file identities are retained in the private Task 4 receipt bundle. Public documentation intentionally contains no private paths, grant bodies or proof-bearing source bodies. Output directories are exclusive; attempts are never retried in the same state.

Both complete output bundles were also retained in a private workspace evidence directory: 199 files from attempt 1 and 195 from attempt 2, each copied byte-for-byte and checked against its original inventory. Original receipts and paths were not rewritten. Retention manifest SHA-256: `ce82960839a0e2ceeba9e8abf9c54eab4bf9f0576b45954fe29754ec00fc01f0`.

## Build and installed receipt inventory

The driver staged `git archive` of the exact candidate, built wheel and sdist in separate backend processes, checked source/data membership, rebuilt the sdist, and compared every wheel member's semantic bytes. Exact inventories contain 103 wheel members and 114 sdist members. The new Python module ships; the external examples, tests, databases and private evidence do not appear in the wheel. The thirteen existing schema/profile/fixture resources remain exact.

| Artifact | SHA-256 |
| --- | --- |
| Source archive | `f21c1e5ece6ecaaad5628c39539c56d10d260daefe74ec863dc994535a808f87` |
| Wheel | `bd1ec72d6c6d4f3b769a15aa504a8a14f4db70a580a32e2df5cd8f12ec2d0700` |
| Sdist | `3b6a9018d1e1871f73a3abbec5cee6965ae8a0aa7ab7e9c622371583bef5e602` |
| Wheel rebuilt from sdist | `f6bc87a14b219f1ce478102e2727d58a451740e4b6e79b99aa1676f30dc082b1` |
| Existing dependency receipt | `38cc4f39d3b642d669fa90c03d8a2598eaf98def0766a710b3cf551aa3a78f09` |
| Final build/install receipt | `13853cbe6b17eebc5d79699786ae7d8d955906c98d969778529944d6b96755b1` |
| Final installed probe receipt | `7ec226b4946ecb61cd02840e844c0b244a46ec61ec0297d49c9a1c72e0c32cb7` |

The original and rebuilt wheel archive hashes differ; every extracted member is byte-identical. This is semantic reproduction, not a claim of byte-identical ZIP serialization. All eleven recorded build/install/probe commands exited 0, including `pip check`; the installed probe took 20.441 seconds. Existing manifest-exclusion and disabled-byte-compilation warnings remain in raw build stderr. The output is not described as warning-free.

The probe ran with `-I -B`, no source/test `PYTHONPATH`, and no user site. All 59 loaded ProofKey modules resolved inside the new environment. All 1,733 inventoried site-packages files and all external example inputs remained unchanged after positive and negative execution.

## Positive denominator: four fresh positions

| Surface | Independent case | Verified effects | Original claim/route, exports and closure |
| --- | --- | --- | --- |
| Library | Window | Exactly one `reschedule`, slot `J06-S3` | Passed |
| Trusted CLI bootstrap | Window | Exactly one `reschedule`, slot `J06-S3` | Passed |
| Library | Goods | Exactly one refusal registration and one return initiation | Passed |
| Trusted CLI bootstrap | Goods | Exactly one refusal registration and one return initiation | Passed |

Window inputs request 13:00–15:00 UTC on 2026-10-08, with J06-S3/J06-S4 capacity. The first eligible slot is J06-S3. Goods inputs contain `{"j06-widget":2,"j06-cable":1}`, quantity 3, destination `J06-DEPOT-B`; return status is `initiated`. No physical receipt, refund or payment is claimed. Both cases use new case/object/principal/request IDs.

Independent business fingerprints are `307bb5cac9bee953d9ec4695dff8116f6adeea119a3ff578d43072c2bf511554` (window) and `6f02aaa5483748b1bd47bf40aeefdfaabcd8a404ea5474808a2d3169c4290eac` (goods), each checked against its different builtin fingerprint. Full original-request hashes and exact complete-request equality are checked separately.

After actual successful owner shutdown, readback opens only existing SQLite files using URI `mode=ro`, `query_only`, a bounded transaction and pure installed value models. It checks all fresh-case cardinalities; G1 and checkpoint/result bindings; SQL-to-model identity; one actual admission claim and route at `admission_observed`; matching attempts, reservation, artifact, resource, auth, request and business commitments; verified intent/source-effect joins; exact outcomes and no unrelated effects. Source reservations and active pressure are empty, and no active admission lease remains.

The committed run inventory and queued/started/finished host inventory share the actual command and execution identity. Every published ANSWER/REASONING file is rehashed against its export receipt. Owner shutdown has no pending command. Database device/inode/size/hash and readback immutability are recorded privately.

Stored claim/route logical journal-hash links are checked. SQLite file hashes are not logical snapshot hashes. Independent recomputation of the final source snapshot is **unverified** because its original source context was not retained by this example. No reopened provider or reconstructed in-memory call history is used as evidence.

## Negative denominator: seven fresh positions

| Negative | Observed denial and retained state |
| --- | --- |
| Wrong transport proof | Denied result, owner closed, zero source effects. Legitimate audit/storage retained: one prepared claim, one unbound attempt, one settled admission entry, zero route and case rows. |
| Wrong explicit release | `invalid_input`; no runtime database created. |
| Omitted custom release | Unchanged builtin default selection yields `invalid_input`; no runtime database created. |
| Expired synthetic review | Exact `AdmissionCompositionFailure(scope)` before runtime database creation. |
| Mismatched review artifact | Exact `AdmissionCompositionFailure(scope)` before runtime database creation. |
| Drifted staged fixture | Exact `SyntheticPreparationFailureV1(identity_changed)`; separate private preparation only, no runtime database. |
| Alias parent | `invalid_target`; target directory remains empty, no database or child allocation. |

The staged-fixture corruption uses its own fresh negative preparation, never the positive installed package. Existing denied claims are preserved rather than reset. Focused source tests retain the broader malformed-input, timing, descriptor, occupied-state, control and pin-denial coverage; those are distinct from these seven installed observations.

## Attempts, regression and completion gates

The acceptance-first check failed at the missing external preparation seam. First committed installed attempt `aa9a209` built/installed successfully and executed all four cases with authorized results and owner closure, but **0/4 passed the complete checker**: its SQL claim join incorrectly expected a top-level wire `case_id`, which is nested under `request`. All seven negative positions passed. That attempt, raw results and databases remain retained; its build receipt hash is `b5f63cf32cb7d4524de7dc9487379dcdfb42a19a8144efd46a4bbe25c8295bca`. The checker was corrected without production changes, then a fresh committed `c26d743` build and all eleven positions passed. Across both installed attempts the retained acceptance denominator is 8 positive attempts (4 complete-check passes) and 14 negative attempts (14 passes); only the final candidate's 4/4 and 7/7 establish current acceptance.

Task 1–3 focused regression result: **268 tests passed in 227.834 seconds**, exit 0, with no failures, errors or skips. The ten-file group covers preparation, trusted CLI, existing CLI/API parity and boundaries, host/admission, route foundation and release manifest. Raw log SHA-256: `e8cdf7461322ec640b44f56cc28e17df0dba571f3cc6bf4deda915f2e3752104`. Existing diagnostic JSON remains in the log. Source/tests/resources were unchanged during this group; only the external checker changed from `aa9a209` to `c26d743`. No full-suite count is inferred from the historical 1,696-test baseline.

Frozen full regression: **pending controller receipt**. Independent whole-change review: **pending**. Strict final OpenSpec validation and child archival: **pending**. J06 remains open until these gates complete. J14, general release verification, registered recover/reply/stop, native integrations, media, real review, timed adaptation, migration, other platforms and event readiness remain open or excluded.
