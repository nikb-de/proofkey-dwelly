# Qualification remediation: discovery and plan input

Date: 2026-10-09. Scope: static investigation of the current checkout, with no test execution, build, installation, provider/network call, Git operation, or change to runtime code. This document is planning input, not an implementation, new qualification receipt, or approval to use a provider.

## Evidence basis and limits

The five completed original assessments read were `outputs/proofkey_runtime_panel_2026-10-09/reviews/{codex,claude,agy,muse,grok.web}.json`, specifically their `raw_review` content. `grok.json` contains a failed CLI transport and no review; it is not a sixth judge. The web review has an Expert mode label without a verifiable served-model ID. The Codex review records a configured selector rather than served-model attestation. Preserve those identity limits in any later aggregate.

Those reviews concern frozen `8e8c9f92c07e9e32e35134962d4b6df6d8648be3` and report the historical 1,619-test run with one failure and sixteen errors. This discovery did not rerun the suite and does not assert that the same failures still exist. A fresh baseline owned by the main remediation task must supersede historical test status. A judge recommendation is a hypothesis/requirement input, not evidence that a capability exists or that its suggested implementation is safe.

Relevant original findings:

| Area | Original findings | Necessary interpretation |
| --- | --- | --- |
| Content processing | Codex F5; Claude F5; Muse F5; Grok web F5 | There are intake/lineage mechanisms, but meaningful processing and actual-model participation are separate missing evidence. Claude's suggested deterministic processors cannot satisfy an actual ASR/model row. |
| Install/release/portability | Codex F4; Claude F6; Muse F6; Grok web declined-to-judge release | A copied source tree or historical wheel hashes do not establish an installable package, current dependency closure, Linux behavior, or distribution rights. |
| Timed drills and evaluation | Codex F8; Claude F7/F9; AGY F2; Muse F7; Grok web R7/R8 and declined areas | Local callback timing, a private directory, synthetic grants, and model review cannot establish complete timed acceptance, protected holdout, independent custody, or actual human approval. |
| Engineer use and evidence | Codex F1/F4; Claude F3/F4; Muse F2/F6; Grok web F1 | Documentation must map exact supported interfaces and outputs; an unfamiliar engineer's successful execution must be separately observed. |

## What is present, and what is still missing

### Bounded processing and multimodal lineage

- `runtime/src/proofkey/providers/protocols.py` defines `Extractor`, `Transcriber`, `EvidencePlanner`, trusted `ProcessingContext`, single-attempt transport requests, exact source/input joins, byte ceilings, and finite timeouts. `anthropic.py` and `elevenlabs.py` parse injected transport responses. They return `mode="synthetic"`; transport-shaped tests are not provider receipts.
- `providers/invocations.py:make_invocation_request` explicitly permits only simulated campaigns; `validate_receipt_identity_and_inputs` rejects injected receipts that pretend to be actual/replay/unavailable. Existing precharge, immutable identity, unknown-outcome, usage and deadline behavior is valuable and should remain the common seam.
- `evidence/catalog.py` and `evidence/processing_contracts.py` retain immutable source/publication/parent joins. Existing tests are designed to exercise saved audio-parent to transcript to separately charged extraction lineage, revoked-parent denial, exact source coordinates and saved-output publication. The fixtures model these mechanics, not semantic correctness; the tests were not executed during this discovery.
- `processing_orchestration.py` provides a prepared V2 planning consumer. `ProcessingRecipe` is not a full automatic multimodal pipeline: its registrations are for planning and require simulated permits. `engine.py:_intake_originals` explicitly reads and validates original bytes and never extracts claims. Its current tests intentionally assert that narrative/original intake does not call the prepared consumer.
- `assessment/readiness.py` deliberately leaves input-class and development-adaptation dimensions incomplete because a `ProcessingReceipt` alone cannot establish either. Actual role rows require actual mode, observed model, request ID, usage, matching role/output and output digest. Preserve that behavior.
- `fixtures/development/media/provenance.json`, README and DEMO describe blank PDFs, solid images and a tone, with semantic readiness false. They are format/lineage controls, not meaningful photo/PDF/audio tasks.

Missing: an explicitly bounded processing route wired to eligible original inputs; meaningful content and independent expectations; per-class receipts that distinguish intake, deterministic processing, synthetic model transport, recorded replay, actual provider processing, failed and unavailable; and an evidence-based readiness audit joining source class, invocation, publication, planner input, business decision and independent effect outcome.

### Reproducible install and Linux portability

- `runtime/pyproject.toml` declares Python >=3.11, setuptools 84.0.0, runtime dependencies and separate `api` / `api-test` extras. `api-test` includes only httpx, so an API test environment must select both extras (or an explicitly defined combined test group).
- `requirements.lock` has eight unhashed version pins. `requirements-api.lock` has nineteen historical wheel hashes for CPython 3.12/macOS arm64, including platform-specific Pillow and pydantic-core wheels, but no setuptools artifact. `DEPENDENCIES.json` is older and still records API dependencies as deferred. These have different scopes; none is a verified current Linux wheelhouse.
- `journal.py` reads sibling `schema.sql`. `host.py` resolves `_ROOT = Path(__file__).resolve().parents[2]`, then reads `profiles/flat-v1.3.json` and two fixtures outside `src`. The current pyproject exposes package discovery without an explicit resource strategy. This is an identifiable packaging risk, not a built-wheel failure observed here.
- `host_files.py`, `batch_files.py`, `host_admission.py`, and `release.py` rely on POSIX descriptors, no-follow opens, mode/ownership/link checks and directory fsync. `release.py` imports `fcntl`. Existing macOS observations do not qualify Linux, and nothing here qualifies Windows.
- `release.py` supports exact allowlisted source preparation and static copied-byte verification. `verify_release` raises `ReleaseVerificationUnavailable`; `test_release_manifest.py` explicitly protects the distinction. README/RIGHTS/NOTICE disclose absent ownership/notice joins and absent clean reproduction.

Missing: a declared installed-resource layout, package-data coverage, built wheel/sdist inspection, dependency/build/artifact/license joins for a named target platform, fresh isolated installed-entrypoint execution with source checkout unavailable, and a Linux receipt from actual Linux execution.

### Drills, holdout and custody

- `assessment/drills.py` measures a host callback with UTC and monotonic time, includes setup/export, retains every position and explicitly records rehearsal mode. For non-pilot runs it always retains `complete_declared_exercise_evidence_missing`; all runs retain outcomes/human-provider/isolation/regression gaps. It must not be relabeled a full acceptance harness by deleting these gates.
- `assessment/drivers.py` supplies frozen registered driver descriptors, bounded input/event capture, before/after source snapshots and a separate declarative grader. Its `EventSink` explicitly is not a hostile-code sandbox and does not forcibly cancel in-progress I/O.
- `assessment/ledger.py`, `coverage.py`, `labels.py`, `cache.py`, and `audit.py` support retained denominators, grouping, independent reference versions, cache invalidation and control sensitivity. These mechanisms do not establish calibrated accuracy.
- `assessment/isolation.py` deliberately tests synthetic same-UID access and emits `rehearsal` or `failed`, with enforced probes false. A claimed custodian string cannot upgrade it. `test_isolation_probes.py` covers that boundary.
- `acceptance.md` declares A as one unfamiliar profile/process adaptation, B as seven positive cases, C as four fault cases, D as twelve unsafe cases. Each whole exercise has one 600-second wall target, including setup, queues, human waits, provider latency and final export. B/C/D freeze the execution candidate; A freezes its baseline and separately retains its resulting reviewed release. The official 30-minute batch is a separate workload.

Missing: exact versioned workloads and independent effect expectations, a public-runtime driver for each exercise, mechanically joined receipts and output audits, a real timed run, actual reviewer actions for A, and separately enforced isolation plus an independent human custodian for protected assessment. A familiar locally authored packet remains rehearsal even when run in a new temporary directory.

### Engineer documentation, demo and observability

- README documents two fixed replay cases, supported command syntax, six port interfaces, exit codes and the fixed registered bridge's limits. DEMO has a bounded two-position recorder/readback recipe that preserves failures and distinguishes process exit from business success.
- `processing_summary.py` provides detached status/debt without content or permission claims. Host command inventories, final manifests, export hashes and driver events already provide useful evidence seams. This is enough for a local observability view; a hosted telemetry service is unnecessary for the first remediation.
- There is no fresh installed-package/independent-engineer receipt established by this investigation. Existing documentation describes source-checkout execution and many important remaining gates.

Missing: one copyable onboarding route whose resources actually ship, a precise command/mode/support matrix, a compact explanation of how to diagnose denial/pending/unknown outcomes, and an executed two-case receipt for the new candidate. A demo video is presentation evidence; it cannot replace machine-readable execution and independent effect readback.

## Smallest implementation slices after a green baseline

These slices are ordered plan input. Each behavioral slice needs an OpenSpec delta and Superpowers plan/tests under the owning task. Do not silently broaden the original process or grant surface.

### Q1. Describe and package the supported offline runtime

Scope: one declared Python/platform target and the existing two fixed synthetic replays. Fix resource layout before claiming fresh installation.

Files/seams: `runtime/pyproject.toml`; `runtime/src/proofkey/host.py:ProfileRegistry.builtin`; `runtime/src/proofkey/journal.py` schema load; a proposed `runtime/src/proofkey/resources/` containing only the selected reviewed schema/profile/fixture bytes, or an explicit resource-root parameter. Prefer a single deliberate resource strategy rather than wheel paths that depend on repository layout. Preserve exact original profile/fixture content hashes and no-follow/private operational-store checks. Review how installed read-only resources are validated without relaxing writable-state protections.

Tests: proposed `runtime/tests/test_installed_resources.py` for included resources and missing/tampered resource denial; existing `test_cli_parity.py`, `test_api_parity.py`, `test_api_boundary.py`, `test_host_admission.py`, `test_release_manifest.py`. A wheel/sdist content check and installed console/module run must execute outside the checkout with `PYTHONPATH` cleared. Merely mocking `__file__` is not clean-install evidence.

Output: current target-specific dependency manifest and build artifact hashes, plus README environment support labels. Preserve the historical dependency inventory as historical; add a current scoped inventory rather than editing old observations into new facts. Select both API extras for API parity. Rights and NOTICE joins require the actual selected distributions/artifacts; do not manufacture missing owner grants.

### Q2. Add one deterministic content-observation route, labeled narrowly

Scope: first support UTF-8 free text/supplied transcript and text-bearing PDF with bounded extraction of source text and exact source coordinates. A local decoder can report what bytes/text were observed; it cannot infer consent or business authority. Name the operation according to its actual work. Add image OCR or audio ASR only when a declared local processor/dependency exists and is in scope; dimensions, hashes, a tone, and generated canned transcripts are insufficient.

Files/seams: proposed `runtime/src/proofkey/providers/deterministic.py`; `providers/protocols.py`; `providers/invocations.py` only if the current synthetic-only receipt validator requires an explicitly separate deterministic path; `evidence/intake.py`, `evidence/catalog.py`, `evidence/processing_contracts.py`. Do not permit callers to self-label injected responses actual. If deterministic work gets its own contract, retain mode/processor version/config/input/output/parent hashes without inventing a model ID or provider request ID.

Tests: proposed `runtime/tests/test_deterministic_processing.py`; existing `test_processing_protocols.py`, `test_processing_catalog_lineage.py`, `test_readiness_ledger.py`. Use meaningful authored text and multi-page text-PDF controls, malformed/truncated/encrypted/no-text cases, source-coordinate boundaries, aggregate byte/page/text ceilings, revoked source access and exact parent joins. Include adversarial text that asks to change permissions and show that it remains content. Expected observations must be independent of the processor's generated output.

Output: per-class `deterministic_processed` or precise unavailable/failed receipt. Actual-model and ASR readiness rows remain incomplete. This slice improves local usefulness and provenance, not unrestricted natural-language understanding.

### Q3. Connect one bounded observation-to-plan-to-gate path

Scope: one non-structured case class first, through existing saved publications and prepared planning, then the existing deterministic action gates. Do not make `_intake_originals` silently execute every configured role or treat an extraction assertion as customer authority. Define the exact phase transition, eligibility, one invocation selection, stop/revocation checks and replay behavior in the spec first.

Files/seams: `engine.py:_intake_originals` / its explicit successor; `processing_orchestration.py`; `evidence/processing_contracts.py:PlanningEvidenceInputV2`; `planner.py:BoundedPlanner`; existing `gateway.py` authority checks. There is a real integration gap here, not merely a missing processor class.

Tests: `test_engine_processing.py`, `test_processing_prepared_consumer.py`, `test_processing_parent_scope.py`, `test_processing_consumers.py`, `test_processing_catalog_lineage.py`. Existing tests explicitly require no consumer call during current intake; replace only the intended behavior tests under a new declared contract, retaining denials and zero-call cases. Add ambiguous/conflicting text, current access revoked before/after processing, stop during callback, stale prepared input, exact replay with zero new processing, original budget/deadline retention and zero forbidden effect. Structural/no-text route retains zero planner calls.

Output: an end-to-end offline synthetic/deterministic receipt with source-to-decision joins and independent postconditions. Do not upgrade actual provider readiness or label generic semantic capability from these controls.

### Q4. Build reusable execution capture and independent evaluation for rehearsal

Scope: first run an untimed public-runtime workload with complete capture, then time the same declared workload. Extend `assessment/drivers.py` / `drills.py` and use existing ledger/reference/audit types; avoid a second disconnected ad-hoc scoring framework.

Files/seams: `assessment/driver_contracts.py`, `drivers.py`, `drills.py`, `ledger.py`, `labels.py`, `coverage.py`, `cache.py`, `audit.py`; proposed versioned manifest under `runtime/fixtures/development/qualification/` and an explicit `runtime/scripts/record_qualification.py` entrypoint. Store runtime inputs separately from evaluator reference bytes. Parent task's registered control, process-adaptation and recovery slices are dependencies for the corresponding A/C positions.

Tests: `test_runtime_drivers.py`, `test_runtime_driver_contracts.py`, `test_eval_coverage_and_receipts.py`, `test_label_reference_versions.py`, `test_isolation_probes.py`; proposed `test_qualification_capture.py`. Verify missing driver/launch/setup/export errors, interruption, deadline crossing, partial output, captured overflow, incorrect source snapshot, absent logs and stale labels all remain in denominator and never become success. Use known good/bad/deny-all/ambiguous controls, repeat grading of fixed outputs, and version/hash invalidation. Keep execution variability separate from grader repeatability.

Output: per-position raw inputs, output/error bytes, timestamps, manifests and effect traces; an independently computed report with capture status, outcome status and qualification gaps as separate fields. A B-shaped rehearsal has seven positions even when some media/actual-model rows remain unavailable. It cannot be called a completed B pass. Preserve A=1, B=7, C=4, D=12 and the independent R01–R15 obligation matrix; do not add a hidden case to a frozen timed batch.

### Q5. Publish local engineer-facing status and a verifiable demo recipe

Scope: docs plus a bounded content-free local receipt summary, after the implemented support surfaces stabilize.

Files/seams: `runtime/README.md`, `runtime/DEMO.md`; proposed `runtime/docs/INTEGRATION.md` and `runtime/docs/QUALIFICATION.md`; `processing_summary.py`; `host_contracts.py`, `batch_files.py`, `exporter.py`; proposed summary renderer consuming only validated public receipt types. Do not add raw prompts/media/credentials or opaque private store paths to public logs. Do not deploy a hosted collector.

Include a matrix by interface and mode: supported command, required trust/bootstrap, persisted state, auth source, output shape, exit/status meaning and explicit unavailable conditions. Show one installed two-case path plus an independent readback checklist. Explain separately queued handoff, verified operational effect, physical return receipt, pending/unknown effect and completed shutdown. Link each claim to the exact candidate/environment/receipt instead of copying historical numbers.

Tests: existing `test_cli_parity.py`, `test_api_parity.py`, `test_processing_summary.py`, `test_runtime_drivers.py`; narrow renderer tests for malformed/missing receipts, redaction/content exclusion and preserved failures. Docs-only changes do not need tests that mirror prose, but all runnable examples must be exercised in the intended environment before being marked verified.

Output: complete local result bundle and concise README support status. An actual unfamiliar engineer can later follow it and provide their own measured receipt; a second model reading the docs is not that usability evidence. Video capture/playback can follow only after the demo exists and retains its own presentation-review status.

## Build and evaluation protocol

1. **Baseline gate.** Main task resolves the known contract/dependency/inventory problems and captures a fresh complete suite on a frozen candidate. Record interpreter, platform, selected extras/dependencies and source hashes; do not describe a selected historical rerun as a full baseline. Do not repin an implementation solely to hide mismatches.
2. **Package/resource gate.** Implement Q1 with tests. Build from exact allowed source and declared build inputs. Inspect wheel/sdist resource inventory; install into a new empty environment from the exact target's local verified artifacts with index/network disabled when those artifacts exist. Clear checkout `PYTHONPATH` and run installed console and module entrypoints from a fresh unrelated directory. Record subprocess output, installer report and installed distribution metadata. A missing wheelhouse is unavailable, not an invitation to silently access a network index.
3. **Portability gate.** Execute the identical package, resource/no-follow/security, CLI/API and runtime checks on an available Linux host/container with declared architecture, Python and filesystem. Container recipe creation is offline implementation; pulling images or packages is a separate external step. If no Linux execution environment is available, keep Linux unverified. Do not relax POSIX protections merely to create a green portability label; Windows support is a separate design task.
4. **Processing gate.** Implement Q2 then Q3. Freeze meaningful per-class inputs and independent expected observations/effects before evaluating. Retain status, actual processor identity, bytes/hash/coordinates and all parent/authority joins. Keep structured-only zero-planner and unavailable-media controls. Run focused tests and then the complete suite after each behavior integration, using new candidate inventory where required.
5. **Rehearsal evaluation gate.** Implement Q4. Freeze case family/split, expectation/rubric/label/lineage hashes, candidate and environment. Run untimed good/bad/missing/ambiguous controls and independent failure drivers before timing. Preserve every declared case and attempt, including setup error, timeout, no output, denial, partial/unknown business outcome and export failure. Retrying creates a new attempt, never a replacement row.
6. **Measured drills.** Only after dependencies and semantics are ready, run A/B/C/D with their exact stated boundaries. Capture UTC plus host monotonic time around the complete exercise, including setup, waiting and export. A includes source-grounded proposal, changed process/acknowledgement semantics, regression, actual human review and resulting release. C requires a genuinely fresh process against preserved state and independent world readback. Preserve original keys/deadlines/debt and unknown effects. Run R01–R15 separately rather than hiding them inside timed denominators.
7. **Claims and closure.** Q5 reports only completed gates. Update OpenSpec living specs through the owning change's archive after implementation/review; do not archive an unexecuted discovery as a completed qualification. Preserve pending actual-model, rights, custody, human review and Linux gates explicitly. Complete source/package tests are engineering evidence, not production readiness or event eligibility.

## Work that needs external facts or explicit additional authority

| Gate | Can be prepared offline now | What cannot be manufactured |
| --- | --- | --- |
| Actual model/ASR/provider processing | Interfaces, parsing, fixture controls, cost/usage caps, disabled-by-default route and receipt schema | Real endpoint/model credentials/entitlement, an authorized campaign and budget, transport execution, native response/model/request IDs and billed usage. A synthetic transport response cannot attest any of these. |
| Local semantic processor | Implement a selected processor against already available dependencies and meaningful authorized inputs | Installation/download of a new model, codec or dependency without scope/authority; semantic performance or speech recognition from text copied into an audio fixture. |
| Package install and Linux | Package layout, lock-generation design, offline build/install scripts, Linux CI/container recipe | Actual fresh installation or Linux execution when toolchain/artifacts/environment are missing; network downloads/image pulls; target-specific artifact/license observations invented from macOS hashes. |
| Rights and public release | Exact proposed allowlist, provenance table, missing-evidence report, local private package | Copyright/contributor/employer grants, third-party license/notice joins absent from actual artifacts, authority to publish or submit. |
| Human review and onboarding | Unsent reviewer pack, explicit accept/change/ambiguous fields, documented procedure | Reviewer identity, availability, disposition or signoff supplied by an agent; a real engineer's independent execution; five available human team members. |
| Protected holdout | Rehearsal set, frozen split/group hashes, denial/leak probe code and public/private data interfaces | Distinct enforced identities, denied mounts/endpoints/credentials/inherited handles, human custodian not tuning from hidden cases, or hiddenness from a directory name/permissions under the same UID. |
| Event/native compatibility | Questions and contract/permission discovery checklist | Organizer rules/eligibility, native API authority, conditional-write/readback semantics or acceptance not actually supplied/tested. |

For protected assessment, retain the existing same-UID negative control and require separately observed denial/leak results in the actual sandbox plus a human custody record. The coding agent must not open withheld case content to prepare its own claimed holdout. If that separation is unavailable, all such runs stay rehearsal/validation. Any case family exposed to tuning or feedback becomes validation, requiring a new genuinely withheld family for later assessment.

## Recommended ordering and cut line

Green baseline → Q1 package/resource closure → Q2 useful deterministic observations → Q3 one bounded integrated content path → untimed independent controls/Q4 → Q5 executed documentation/demo → actual provider/human/custody/Linux gates when their prerequisites are supplied → full declared timed qualification.

Q1 and doc preparation can proceed independently of the processing design once source ownership is clear. Timed A depends on the parent task's changed-process/release capability; timed C depends on its registered recovery/control work. Do not describe either as solved by this qualification slice. Hosted observability, additional backends, voice calling and a polished video are lower priority than an installed working route and complete evidence. Cutting them does not remove mandatory actual-processing or custody gaps from the final status.
