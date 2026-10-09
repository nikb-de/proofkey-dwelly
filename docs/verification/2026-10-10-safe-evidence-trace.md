# Safe evidence trace and quickstart — J23/J24

Status: **implementation, scoped reviews and independent whole-leaf review complete; frozen regression pending**. This is an offline, content-free projection of a supplied receipt, not independent proof of dispatch, readback, publication or business correctness.

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

The new full suite runs on `git archive` of `7b4c6e2`, with copied runtime hashes checked before and after. Further worktree changes cannot alter that candidate. The qualified interpreter/dependencies are reused; third-party environment state is not fully frozen. Final result and retained review links will be recorded before this leaf is closed.

## Remaining boundaries

No production qualification, independent readback from trace output, transport dispatch proof, actual payment/refund, physical receipt, live integration, native provider, Linux/Windows result or human usability evidence is claimed. J08 broader support-document review and J21 unfamiliar-engineer validation remain open. J23/J24 can close only for this narrow implemented path after the final review, full regression and OpenSpec archive; the parent remediation program remains open.
