# Safe evidence trace and quickstart — J23/J24

Status: **complete and archived for this bounded source-only scope**. Implementation, scoped reviews, independent whole-leaf review and frozen regression passed. This is an offline, content-free projection of a supplied receipt, not independent proof of dispatch, readback, publication or business correctness.

## Exact scope

The candidate is `7b4c6e2613d36e99e067793e24b044f9f2805c6b`, based on `71b4cd4d5b16fe5bb5fa41c697f1d829332ec004`. It adds a strict `CliReceiptV1` projector, `python -m proofkey.trace`, and an [outcome-first quickstart](../../runtime/QUICKSTART.md). The existing business CLI output remains unchanged. No collector, provider client, file-path input or state-creating renderer operation is added.

The projection uses local sequential aliases rather than source identifiers. It retains finite statuses, order, durations and denominators, while excluding raw identifiers, paths, hashes, source text, operations, arguments, rationale, postconditions, reference bodies and free-form errors. The four explicit limits on interpretation are always present:

```text
provenance = unverified_receipt_projection
transport_dispatch = unknown
original_readback_observation = not_observed
publication_files_checked = false
```

Admission, host execution, reported result verification, export/publication and shutdown are separate stages. Reported receipt fields cannot establish original readback or actual file presence. The separate local acceptance observer described below inspected retained synthetic state; the renderer did not.

## Bounded interface and hostile input

Input is stdin only, with one read of at most 1,048,577 bytes and a 1,048,576-byte accepted envelope. Structural limits are depth 64, 50,000 nodes, 128 command positions, 256 effects per position, 4,096 effects total and 262,144 output UTF-8 bytes. Over-limit input fails closed rather than truncating. Duplicate JSON keys, nonfinite numbers, wrong models/subclasses, cyclic or forged typed state, invalid alias counters and incoherent denominators are rejected.

The module accepts either no arguments or exactly `--format json|markdown`. Expected input/output errors return exit 2 without exception text. A broken output destination cannot receive fallback JSON; its buffered write/flush is contained and interpreter shutdown does not retry it.

## Executed focused evidence

| Check | Observed result |
| --- | --- |
| Task 1 projector and related contracts after correction | 56 tests, 36.583 seconds, exit 0 |
| Final projector plus stdin adapter | 29 tests, 18.309 seconds, exit 0 |
| Buffered stdout RED | Two real closed-pipe tests failed: actual exit 120 instead of required 2 |
| Buffered stdout GREEN | Both real-process branches pass: exit 2, empty stderr, no working-directory files |
| Portable quickstart: rescheduling | Exit 0, 2.468881333 seconds; exactly one persisted reschedule |
| Portable quickstart: goods refusal | Exit 0, 3.555164666 seconds; exactly one refusal registration and one return initiation |

The fresh guide captures used a qualified existing Python environment, source imports, literal public inputs and new private directories. Both observed original request/binding continuity, committed public inventories, verified intent state, actual export hash matches, no pending command, owner/admission closure and zero planner calls. They are not installed-distribution verification or unfamiliar-human onboarding.

Two portable-capture manifests contain 31 entries each; independent review checked all listed hashes. The earlier capture attempts remain retained. Their observer initially failed on macOS path normalization, then an ordinary read-only SQLite connection created empty coordination sidecars. Corrected inspection uses immutable read-only access only after confirming absent/empty WAL. No business command was rerun to hide those observer failures.

Portable export SHA-256 values:

| Case | ANSWER | REASONING |
| --- | --- | --- |
| Rescheduling | `7d5b7d17acd6073e11195da219ed861472e02c57e40b23e5a3b940d8b1c8cada` | `8460e8d60b91af00e2960302127df739ed0ae2ed6fe5c3d2f9b4c75d0dd42d51` |
| Goods refusal | `6fc4e908242123d9552535d63d784e5f0e4f3f141fd3e151dbe7162ac1fe83aa` | `43a37bef3494e3a62857c4dfaf525cb77a5e4695dbc5fbe2325002c027795b62` |

## Review and full regression

Task 1 independent review found arbitrary numeric aliases/impossible denominator acceptance, then approved the corrected canonical validation. Its no-provider-import wording was explicitly reconciled to permit the required existing `CliReceiptV1` transitive inert definitions, while still forbidding provider-client construction/calls. Task 2 review found buffered output errors escaping at interpreter shutdown, then approved the targeted fix. These are Codex-agent reviews, not a new Claude/Grok/AGY/Muse panel.

The first frozen full-suite attempt at `58dd1fe` was deliberately terminated after the output bug was identified. Its exit -15, 33.779 elapsed seconds and missing final denominator are retained as a controller-cancelled superseded attempt, not a test failure or completed regression result. Its 277-file archived source stayed unchanged.

Independent whole-leaf review approved exact candidate `7b4c6e2` for specification compliance and code quality with no Critical, Important or Minor findings. Review of the supplied complete leaf diff is not a whole-system security audit. No test suite was rerun by the reviewer.

The final full suite ran on `git archive` of `7b4c6e2`: **1,798 tests passed, zero failures/errors/skips**, 1,006.163 test seconds (1,007.464 elapsed seconds), exit 0. All **277 runtime files** matched their copied hashes before and after. The worktree advanced to `64dd1a9` during execution, but could not change the archived candidate. The qualified interpreter/dependencies were reused; third-party environment state was not fully frozen. The inherited macOS temporary directory allowed the actual `/var` alias test to execute without a skip.

The [final receipt](../../outputs/proofkey-safe-trace-full-7b4c6e2/receipt.json), [complete test log](../../outputs/proofkey-safe-trace-full-7b4c6e2/stderr.txt), [stdout](../../outputs/proofkey-safe-trace-full-7b4c6e2/stdout.txt) and [source inventory](../../outputs/proofkey-safe-trace-full-7b4c6e2/source-before.json) are retained. Archive SHA-256: `70119802243ec8c1cf929411d937bebc0fa05272c18addfec54ef198ea604763`. Both before/after inventory files hash to `ea93958ae10e8ebc629c47ed25250d01fa5cc2e44a82998a4addf082adad81ec`; stderr hashes to `f7664fa92a040723f80746cc76073b9ddb621be571142c20e67eb40c6a39b52b`, stdout to `6f0db3c23c92f74304ab26470c33f4be8c227af80f7c11a3e5f88b7011a22477`.

The receipt SHA-256 is `1adbeeebbf53a81ad36b918e3045e50daf6a9899b5a0f9b4ad686daaf83b2685`. Strict change validation passed. The completed child (historical worklog retained in Git history) was archived with all four requirements synced to the [living specification](../../openspec/specs/safe-evidence-trace/spec.md). The archive's date uses the CLI's UTC date, while this report uses the London event date.

## Retained review records

The [retention manifest](../../outputs/proofkey-safe-trace-20261010/retention.json) hashes 25 copied review/plan/helper records and 705 existing evidence files, including both full-suite attempts and portable guide captures. Manifest SHA-256: `6eda782e9c7d65497abfadb03bde02e5af1012e092953bf555746d33cba0c1bf`. The [whole-leaf review](../../outputs/proofkey-safe-trace-20261010/whole-leaf-review.md) and [closure review](../../outputs/proofkey-safe-trace-20261010/closure-review.md) both report C0/I0/M0 within their stated scopes. Closure review checked the actual receipt/log/archive hashes, 277 unchanged source files, all 18 then-added local links, 13/19 register counts and archive/living-spec consistency. Postarchive strict OpenSpec validation passed all 11 items. These retained files are local evidence, not an external publication.

## Remaining boundaries

No production qualification, independent readback from trace output, transport dispatch proof, actual payment/refund, physical receipt, live integration, native provider, Linux/Windows result or human usability evidence is claimed. [J08 support-document review](2026-10-10-public-support-boundaries.md) is separately complete; J21 unfamiliar-engineer validation remains open. J23/J24 are closed only for this narrow implemented path; the parent remediation program and stop-v2 qualification remain open.
