# Submission packaging audit — 10 October 2026

## Scope and publication authority

Prepared from main `c53fb503ffb2d482f4abb58e9d920f09377a6e9c`. The initial v2 demo from commit `80363a408e57a961b4b6b0fce14be61108195278` is replaced by the user's selected `Right-onTime-FINAL-1080p.mp4`; the old video is removed from the current tree and remains recoverable from Git history.

The owner explicitly authorized making the existing repository public, including its history, after audit. The owner separately confirmed that the organisers permitted publication of the supplied Dwelly cases and derivative data. This is a recorded owner attestation, not an independently inspected licence grant or a claim that Apache-2.0 relicenses third-party content. The team supplied LinkedIn and X post URLs, recorded in SUBMISSION.md; content verification is separate.

## Retained evidence and cleanup

The reviewed cleanup manifest identifies 285 obsolete development plans, archived change worklogs, negotiation notes, duplicate design assets and old renders. They are removed from the current tracked tree, not erased from Git history; local copies are preserved. Runtime source, contracts, live specifications, dataset provenance, source cases, tests, current product assets and provider records remain. Failed model outputs and historical limitations are not replaced or removed to improve reported results.

The secret review inspected 6,517 unique Git blobs, approximately 248.7 MB, across locally available refs. No live credential was identified in submission-branch ancestry. Reported matches in that ancestry were explicit test sentinels and rejection-test DSNs. Two Google-key-shaped strings occurred in saved public-page HTML under local checkpoint refs outside submission ancestry; those refs are not published. This scan is not a guarantee of absence. No mirror or all-ref push is used.

## Reproduction checks

- Fresh CPython 3.12.11 environment created with `uv`; hash-checked PostgreSQL dependencies and Pillow installed.
- Fresh PostgreSQL 17 instance, migrations, HTTP health/capability reads and scripted terms replay passed: `booking_confirmed`, `physical_delivery=not_confirmed`, 21 revisions, zero model calls and zero external effects.
- The isolated retained-record exporter passed eight tests, including preservation of failed/null outputs, source bytes and supplemental artifacts. It does not manufacture official challenge provenance.
- The selected replacement fully decodes: 56.900 seconds, 1920 × 1080, 30 fps, H.264/AAC, SHA-256 `013d08fd40226a52007d28201027fee2993ec0c18f5df77b0ce6cb691b85608e`.
- The earlier merged product tests passed 390 backend/model/analysis tests and 384 subtests; the UI suite passed 100 tests. Those earlier tests are not a new live-model quality assessment.
- A clean archive of the staged submission tree passed **41 tests and 15 subtests**, with PostgreSQL enabled, across the retained-record exporter and product scenario/terms workflow suites. No tests in that run were skipped. This archive excludes all 285 removed files and local-only files.

## Outstanding requirements

No official unseen Reality Test input/result is present in the inspected repository. `ANSWERS/` must not relabel public development examples as official results. The final official case outputs and traces remain required. LinkedIn and X launch URLs are recorded as supplied by the team. The full legacy runtime audit remains incomplete as documented in the retained [publication verification](verification/repository-publication-2026-10-10.md).

## Public access verification

GitHub reports `visibility=public` and `private=false`. An unauthenticated request to the repository returned HTTP 200. The previously published raw video returned HTTP 200; the replacement path must also be checked after publication. This verifies anonymous access, not event submission or acceptance.
