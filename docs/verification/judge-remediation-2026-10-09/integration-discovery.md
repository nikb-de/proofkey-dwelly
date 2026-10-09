# Integration and adaptation remediation: source-backed plan input

Date: 2026-10-09. Scope: Claude F2/F3/F4/F7 in `outputs/proofkey_runtime_panel_2026-10-09/reviews/claude.json` (`extraction.final_text` is the serialized review). This is read-only architecture discovery plus this document, not implementation, a specification amendment, a test run, a new qualification, or a timed-drill result. Source references below describe the checkout inspected at discovery time, not an automatically refreshed view. No provider/network calls, installs, tests, or Git changes were made for this investigation. The synthetic factory implementation-registration proposal was a separate root-owned workstream and is not duplicated here.

**Dated supersession, 9 October 2026:** the private registry coupling identified below is resolved at frozen `40138e1` by public validated commitments and consumer migration (`0e71716`, with zero-byte preflight correction `0122660`). [J22/J32 verification](../2026-10-09-registry-commitments.md) records the 1,693-test stable-source gate, completed leaf archival and remaining performance/authority limits. The [completed r2 assessment](../../../outputs/proofkey_runtime_panel_2026-10-09_r2/reports/ASSESSMENT.md) source-adjudicated all 30 findings without reproducing a new J22/J32 defect. The historical observation and its line references remain below for provenance; this supersession does not establish reusable provisioning, changed-process execution or the other integration proposals.

**Dated J06 supersession, 10 October 2026:** [trusted-case verification](../2026-10-09-trusted-replay-cases.md) at `80e0d6f` establishes bounded new window/goods cases through trusted Python library and explicitly configured CLI, with final 4/4 positive and 7/7 negative installed positions. This supersedes the reusable-provisioning/configured-CLI gap below only within that scope. Default CLI and API do not automatically select registered admission; the API has no registered-composition selector. Registered `fixed-synthetic-v1` controls remain run-only, with recover/reply/stop denied. See the [public evidence map](../../../runtime/README.md#support-and-evidence-map) for separate candidate and launch boundaries. The original findings and source anchors below remain unchanged historical discovery.

## Decision-relevant findings

The findings are substantially valid, but two distinctions matter for the plan:

1. **F2 is a real execution and registration limitation.** Changing profile metadata alone cannot implement the lead acknowledgement/readback-and-process adaptation. Factory validation, provider dispatch, the hard-coded engine phase interpreter, host admission validation and retained-version selection each have an independent restriction.
2. **F3 is narrower than “no trusted registration exists.”** `ProfileRegistry(entries)` already accepts trusted `ApprovedProfileRelease` objects; `ReleaseRegistryV1` already packages independently supplied artifacts/factories/resources. What is missing is a reusable, safely provisioned composition/launch path for an engineer's cases and an executable compatibility contract beyond the fixed bridge. This must not be confused with allowing request JSON to supply trust.
3. **F4/F7 are not proof that core service/refusal, stop, or crash tests are absent.** Existing unit/integration test sources cover these paths, including real child-process exit. The missing evidence is a current reproducible public-entrypoint receipt for the requested scenarios on the exact candidate; the registered route additionally lacks executable control/recovery support.

## What exists now

### Trusted registration and public launch

- `host.py:56-99` defines a detached host release with independently supplied paths and raw/semantic hashes. `ProfileRegistry.__init__` at `102-110` accepts a finite trusted list; it is not restricted to calling `builtin`. `ApprovedProfileRelease.__post_init__`, however, permits only `reschedule_window` and `goods_refusal` (`74-78`). `builtin` supplies exactly two fixtures and fingerprints (`112-124`). Consequently other request kinds fail even if all release inputs are trusted.
- `host.py:533-536` rejects a run whose kind or business fingerprint differs before runtime construction. `host_admission.py:659-660` repeats that restriction before claim preparation. Exact business fingerprint is an additional fixture constraint, not complete request equality or customer permission.
- `registered_releases.py:158-232` has bounded immutable resource, factory and artifact declarations. Its envelope checks source/proposal/tests/regression/migration/agent/dependency declarations (`235-287`), including synthetic policy and explicitly unestablished regression/authorship. `resolve` returns a newly validated detached registered release (`390-395`). The blob format does not activate or import the embedded implementation bytes.
- `host_admission.py:106-133` fixes 16 implementation paths and `fixed-synthetic-v1`; `202-243` requires the synthetic clock, one registry entry, profile v1.3, all process versions v1, exact profile/blob/resource/source commitments and provisioned synthetic review. It also accesses `registry._releases` directly (`210-214`), a private coupling worth replacing with a bounded public commitment projection when this boundary is next changed.
- `RuntimeFactory.create_registered` (`host.py:256-280`) validates, acquires the writer lease, opens the admission owner, then constructs the world/store/gateway/engine on the owner. It passes verified fixture bytes to the world. This is the correct composition boundary to retain.
- CLI parsing supports release selection and the closed command set but no registered-composition source (`cli.py:32-47`). `CliConfiguration` validates a `ProfileRegistry`, factory and synthetic clock (`bootstrap.py:111-124`); `_default_configuration` creates builtins (`146-164`). CLI constructs `HostDispatcher` at `cli.py:190`; the API does so at `api.py:198`. Neither call supplies an admission composition. A flag without trusted provisioning behind these constructors would be cosmetic.

### Registered state and controls

- `RuntimeResources` exposes only `run_registered` (`host.py:249-253`). `HostDispatcher._execute` rejects every registered command other than run (after existing inspect/unavailable branches) at `646-648`; ordinary controls call `engine.recover/reply/stop` at `668-673` only for the nonregistered path.
- The guard is deeper than that branch: `gateway.execution_scope` calls `owner.guard_execution` before entering journal scope (`gateway.py:65-76`). Owner guard requires `active`, the exact execution object and original timing (`host_admission.py:681-700`). Registered `run` creates that capability and clears it in `finally` (`732-754`). Simply removing the host denial will not authorize controls.
- Fresh entry captures public images, rejects existing correlation, and creates a durable prepared claim (`host_admission.py:652-679`). Actual gateway binding reserves and reads back a route, seals it, then permits existing atomic debt import (`705-729`; `gateway.py:964-966`). This ordering must remain unchanged for fresh work.
- `_ClaimStore.write` permits only prepared → binding_sealed → admission_observed and immutable original identity (`host_admission.py:473-495`). `open` checks the marker, control identities and every required existing DB (`554-605`), then denies **any** pending claim (`606`). Fresh prepare also denies pending claims (`662`). Thus a crash after preparation/sealing can block the whole composition, not only that case.
- Existing `claim_for_case` and `route_for_case` (`756-765`) supply lookup seams, but neither is current caller authentication or permission to execute. There is no route-derived control entry capability or interrupted-claim reconciliation state machine yet.
- Existing tests explicitly require registered recovery denial (`test_host_admission.py:294-310`), and observed reopen without replay (`314-330`). Prepared restart, failed seal and failed observation retain debt/block (`516-575`). These are intentional current contracts, not tests to silently invert.

### Genuine process and acknowledgement adaptation

- Factory denies policy changes, permission expansion and authority replacement (`factory/proposal.py:69-85`). It rejects any change to phases, edges, operations, waits, approvals, acknowledgements, readbacks or completion (`86-104`); only added covered prerequisites with new identities can survive that section. The supplemental change is fixed to reviewed v1.3 enqueue_handoff, with synthetic agent material (`116-123`). Candidate process versions other than v1 remain `regression_unavailable` even after claimed passing evidence (`335-338`).
- `ProcessController` validates finite graph structure, stopped/terminal invariants and declared supported contracts (`process.py:74-110,134-195`). It is a useful safety component but not a generic executable process interpreter. `engine.run_one_approved_phase` still chooses behavior by fixed phase names and mappings (`engine.py:615-714`), so a newly added readiness phase needs a real versioned dispatcher implementation.
- Provider execution independently rejects every `intent.process_version != 'v1'` (`adapters/world.py:482-486`). It already simulates typed business rejection (`431-444`) and authoritative outcome reads (`730-760`). A new label or a pre-existing business-rejection fault is not evidence that a changed transport-envelope interpretation has been implemented.
- `verifier.py:12-32,35-71` contains operation-specific facts/stages/postcondition rules. An adaptation should normalize changed provider response envelopes to these domain meanings where possible; it must not weaken the verifier to treat HTTP success as business success.
- `factory/release.py:44-50` still denies actual activation. It requires controlled pending inventory and denies nonempty pending effects (`69-90`), then emits `staged_simulation` (`91-108`). Runtime-compatible synthetic registration and genuine human-reviewed activation are separate milestones. Source-backed synthetic adaptation must not claim a completed drill A requiring actual human review.

### Service, waits, stop and crash evidence

- Engine service-refusal handling and handoff are concrete (`engine.py:543-546,670-702`); provider requires completed service (`adapters/world.py:516-521`); controller requires verified refusal before handoff (`process.py:156-157`). `test_workflows.py:132-154` already asserts verified refusal, queued handoff with **pending** disposition, and handoff rejection without erasing refusal. A queued message is not accepted ownership, refund or internal-case creation.
- Core controls exist: recover preserves original request/checkpoint and reconciles stopped effects read-only (`engine.py:333-361`); reply accepts a scoped wait reply (`363-384`); stop is `386-410`. Current source authentication remains material: `gateway.py:540-554` checks control identity after accounted source reads; reply source ACLs and ownership epoch are checked at `556-575`.
- `test_stop.py:85-118` has a real child-process exit after stop fencing. `test_workflows.py:791-851` exits a child at saved positive phases and recovers in a fresh child, across window, exact-slot, goods and service workflows. These use test support and a controlled `FakeClock`, not the production CLI composition. Other source tests cover entered-original reads and second crashes (`test_workflows.py:522-617`). No current test execution is asserted here.
- CLI restart tests explicitly preserve denial at `test_cli_parity.py:194-223`. `SyntheticReplayClock` starts each instance at the same epoch with a new monotonic anchor (`clock.py:34-46`). This can put a restarted process before prior captured source timestamps; bypassing freshness or resetting saved deadlines would hide the problem rather than solve it.
- Drill C is exactly four declared faults, not all possible phase crashes: journal failure; crash after dispatch mark/before transport; external write before local verification; verified refusal plus unknown return (`acceptance.md:13`). `acceptance.md:7,16,18` requires frozen candidate, complete denominator, real finish time, declared preparation/entrypoint and simulated clarification labels.

## Minimal vertical slices and precise seams

These are proposed separate OpenSpec changes/plan inputs. Freeze inputs and acceptance behavior for each before implementation. Do not put all of them into the factory qualification patch.

### I1 — Reusable trusted synthetic registration and launch

Deliver one independently provisioned non-builtin request/profile/fixture registration through library and CLI, plus explicit denial of mismatched commitments. Keep the first executable profile/process family fixed; this slice need not admit arbitrary process code. Add a bounded trusted launch/configuration seam which carries a previously validated composition; `--release` selects an ID from it. A request body must never select files, factories, approval or clock. Registration can be a separate provisioning step, not a second JSON field inside the business command.

Product seams: `ApprovedProfileRelease` validation and `ProfileRegistry`, `host_admission.validate_composition`, a public immutable registry identity/projection if needed, `CliConfiguration`, `cli.main` dispatcher construction; API construction only if parity is explicitly included in this slice. Continue no-follow, exact hash/profile comparison, ownership and input bounds. Existing two builtins stay reproducible.

Test seams: new focused trusted-registration tests, `test_host_admission.py`, `test_bootstrap_process.py`, `test_cli_parity.py`, `test_host_contracts.py`. Acceptance must exercise a **nonbuiltin** commitment and positive effect, not only all-denied parity. Include wrong source/profile/process/artifact, duplicate registry ID, body-supplied path/import/approval and tampered file denials before source/journal work. Snapshot historical qualifications rather than repinning them.

### I2 — Registered controls for fully observed original routes

Start with `admission_observed` cases only. Construct an owner-held control capability from exact marker/resource/release, claim, route and stored original generation, then dispatch through the original engine methods. Separate the control capability from fresh `prepare_entry`; it must not create another admission attempt/route or consume a new case budget. Current transport proof remains required, and the engine's source ACL checks remain authoritative. Stop binds the requested generation; reply binds the exact wait/question and designated actor. Reconcile original effects under original versions and IDs.

Product seams: `RuntimeResources` registered control methods; `HostDispatcher._execute:646-673`; explicit owner entry variants and guard in `host_admission.py:652-765`; gateway guard in `65-76` and bind path in `849-966`; existing engine control paths only as necessary. Preserve pre-disclosure guard ordering. Do not pass detached claims as callable capabilities.

Test seams: extend `test_host_admission.py` with observed-route recover/reply/stop, foreign generation/release/root/proof denials, swapped runtime aliases, exact debt comparison and unchanged route/claim. Existing core `test_stop.py`, `test_operator_wait_gateway.py`, `test_waits.py` are safety controls. A successful stop followed by recover must never resend; a reply cannot create consent from text. CLI integration follows the trusted I1 launch seam.

I2 does **not** remove pending-claim startup blocking. That needs I3's separate failure-state reasoning.

### I3 — Interrupted registered claims and restart-safe timing

Define a closed recovery classification for prepared/unbound; route reserved plus sealed but not admitted; admitted journal plus incomplete observation; and completed observed admission. Use current public complete snapshots and original claim/route identity to distinguish them. Preserve all original timing/debt/keys, report ambiguous/corrupt joins and block execution. A recoverable admitted-but-unobserved claim may finish only the original bookkeeping after a successful exact join; it must not create a fresh admission or resend an uncertain effect. Prepared/unbound claims may legitimately remain blocked in the first version; a classification receipt is more useful and safer than deleting them.

Product seams: owner `open`, `guard_execution`, explicit recovery entry; `_ClaimStore` transitions/validation if a new terminal bookkeeping state is needed; public `AdmissionRouteStoreV1` get/for_generation/observe APIs; runtime factory selection before ordinary engine entry. Do not mutate existing DDL silently: use a versioned new control store contract or a separately specified compatible migration if wire/state additions require it.

Timing is a distinct prerequisite for child-process proof: specify a trusted persisted replay timeline or an explicitly configured continuation epoch that cannot reverse prior UTC, extend the original saved business deadline or reset elapsed debt. `clock.py:34-46`, `bootstrap.py`, host factory and admission grant validation are seams. Original monotonic anchors from another process cannot simply be treated as a fresh process clock. Expired original work remains expired even if the control operation receives a fresh bounded I/O context.

Test seams: real subprocess termination at prepare, route reserve, seal, journal import, effect-before-observation, and observation commit. Reopen from persisted files with the trusted same registration, not test fixture reconstruction. Assert per-fault pre/post public snapshot hashes, attempts/routes, original identity, effect counts, counters and denial on ambiguous/corrupt states. Existing `test_host_admission.py:516-575` becomes the preserved baseline; change only expectations explicitly covered by the new recovery contract.

### I4 — Service-refusal and retained wait/stop public evidence

Use I1 for a separately frozen service fixture with completed lifecycle, appropriate consent/recipient/packet/source facts and independent request commitment. Do not mutate the existing window/goods fixture at runtime. Record service refusal and queued handoff as separate effects, including handoff rejection/unknown while refusal stays verified. Cover one scoped customer/operator wait reply and stop on retained state through the declared public entrypoint. If run after process restart, require I2/I3; a same-host receipt must say that scope explicitly.

Product seams: primarily registration/fixture composition and receipt tooling, rather than changes to core service semantics. `test_workflows.py:132-154`, `740-747`, `test_operator_wait_gateway.py`, `test_waits.py`, `test_stop.py`, CLI parity and the export/publication contracts give assertions to reuse. Avoid production imports of `tests.support` or `world.mutate`; trusted fixture generation belongs in preparation.

Acceptance artifact: original command, mode, candidate/profile/process/fixture hashes, exact input, source authority assumptions, exit code, retained result/export and per-effect source/journal evidence. “handoff pending” remains pending. Existing synthetic unit paths are not native provider evidence.

### I5 — One real changed-process plus changed-ack/readback execution

Choose one finite delta combining a changed transport-envelope parser with a permitted extra readiness-read phase in one existing workflow. Keep capability permissions, authorities, consent and policy unchanged. Give the candidate new profile/process/adapter identities; provide a selected compatible dispatcher, not a generic evaluation of supplied code or an arbitrary graph-as-code runtime. A new phase must actually perform a source read and enforce its prerequisite before write. The new envelope parser must demonstrably distinguish HTTP success/business rejection and normalize to canonical domain evidence; a missing/eventually absent original read remains unknown rather than success or nonexecution.

Product seams: `factory/proposal.py:69-104,116-153,335-338`; `engine.py:615-714`; `process.py:74-195`; provider `_apply_declared_operation:475-486` and response mapping; `verifier.py` only if canonical evidence needs a genuinely new closed form; executable compatibility check in `host_admission.py:219-224`. Integrate with the root's separate implementation-registration work instead of another pin registry. Replace unconditional v1 acceptance with a finite trusted compatibility declaration whose actual implementation and tests are bound. Preserve rejection for every unimplemented version.

Test seams: `test_adaptation_factory.py`, `test_process.py`, `test_adapters.py`, `test_workflows.py`, `test_host_admission.py`, and a new focused delta test. Require baseline/candidate comparison for changed envelope and readiness facts, actual extra read before write, a real successful changed-profile run, negative response/readback cases, old-version compatibility, unsupported version denial, truthful diff inventory, and independent regression receipt binding. A metadata-only version bump cannot pass.

For unfinished effects, first support **preserve old route**: old registered resource and executable remain selectable by stored release, new cases use the new registration. Do not require in-place migration for this first delta. `stage_release` currently rejects all pending inventory; changing that to permit staged parallel old/new releases needs an explicit retained-version contract, exact inventory and new tests, not removal of the check. Authentic human review and a timed A receipt remain separate final gates.

### I6 — Frozen four-case drill C and adaptation measurement receipts

After the requisite behavior exists, execute the exact four C cases via the declared registered/public entrypoint on one frozen candidate and report complete per-effect outcomes and counters. Journal failure must show zero transport entry; crash-before-transport must preserve the marked original and avoid blind resend; effect-before-verification must reconcile the original; verified refusal/unknown return must retain the verified refusal independently. A timeout or terminal unknown may be the correct safe result but cannot be relabeled completed work.

Drill A requires a separately frozen packet and baseline and includes discovery, proposal, regression, actual human review and clean hashed release in the 600-second denominator (`acceptance.md:7-11`). A prepared tool harness or synthetic review receipt alone cannot satisfy it. Retain measured failures and elapsed times even if the target is missed. Do not modify the archived review packet or rewrite its conclusions.

## Dependency and implementation order

1. Root's green baseline/qualification/environment work is prerequisite to interpreting new regression evidence, but is not evidence that these new slices work.
2. Specify I1 and I5 contracts separately. I1 can finish on the existing executable family; I5's parser/process design can proceed independently until it needs registered execution.
3. Implement I1. I4 service positive evidence can then proceed independently of interrupted-claim recovery if explicitly same-host/nonregistered where applicable.
4. Implement I2 for observed routes and a scoped trusted continuation-clock contract. Then I3 for interrupted registered claims; do not fold unsafe pending recovery into the observed-route control patch.
5. Implement I5 execution/compatibility and retained old-release selection after registration and the root's implementation inventory are stable. Keep old pending work on old resources.
6. Freeze the resulting candidate and run I4 retained-state evidence and I6 measurement. Use current actual receipts to update the report; archive the newly completed OpenSpec deltas into living specs.

These slices share host/admission code. Parallelize source analysis or independent test design; do not give overlapping host/owner edits to simultaneous implementers without ownership/serialization.

## Prior contract restrictions requiring explicit new deltas

| Existing contract | Why implementation cannot silently broaden it |
|---|---|
| `registered-host-admission.md:6-13` limits the bridge to fixed synthetic execution and four paths, preserving engine/schema/ports/fixtures. | I1/I2/I3/I5 exceed this historical patch scope; create new deltas rather than treating it as blanket permission or editing its historical evidence. |
| Same file `74-80` defines run as the sole registered entry, denies controls and has no CLI flag. | I1/I2 must explicitly add the trusted launch/control semantics. |
| Same file `94-103` fixes profile v1.3, process v1 and exact implementation/source commitments. | I1 wider profile compatibility and I5 require finite executable compatibility rules, with current pins still authoritative for old registrations. |
| Same file `130-149` blocks existing correlation/pending claims and forbids automatic retry/deletion/reset/migration. | I3 requires a new classified recovery path, preserving these prohibitions for ambiguous states. |
| `registered-release-routes.md:3-7,48-49,91,105,158` makes B3 declarations/bookkeeping nonactivating, opaque and preserve-only. | Do not turn declaration validation, a stored observed route, synthetic agent fields or opaque code bytes into execution/review authority. |
| `design.md:188-194,233` requires reviewed finite process changes and preservation of unfinished original contracts, with no implicit schema upgrades. | I5 must specify executable version selection and any migration separately. |
| `host-interfaces.md:13,25,27,31` binds fixed demo commitments, verified consumed snapshots, original time bounds and explicit authenticated stop. | New registration may broaden selection but must retain independent source consent, consumed-byte identity, time limits and stop authentication. |
| `acceptance.md:7-18` fixes the measurement denominator and simulation disclosures. | New source tests cannot be represented as completed public timed drills. |

## Unsafe shortcuts to rule out in review

- Removing the registered non-run denial or owner guard without a scoped preserved-route capability.
- Reusing `run_registered` for controls, creating a new generation/attempt, resetting debt/deadlines, or authenticating from the stored proof digest.
- Dropping `pending_claim`, deleting claims/markers/control DBs, or relabeling sealed as observed without the exact public snapshot join.
- Permitting arbitrary profile paths, callback/import strings, factory names, fixture mutations or code bytes from business input.
- Weakening no-follow/alias/owner checks to make Linux or CLI evidence pass; portability requires honest platform qualification.
- Accepting any non-v1 process because metadata/receipt says “passed,” while provider/engine still execute the old fixed semantics.
- Treating a generic existing `business_rejection` fault as proof of a changed response parser, or trusting a new acknowledgement as completed business work.
- Running pending effects under the latest profile, changing original fingerprints/postconditions, or dropping pending inventory rejection without an old-release resolver.
- Fixing restart freshness by ignoring timestamps, renewing consent or granting a new business budget.
- Replacing historical pins/reviews/test outputs with current values or omitting failed cases from new evidence.

## Remaining design decisions, not hidden assumptions

Before implementation, decide the trusted provisioning format and selection boundary (including whether API parity is in I1), the exact new process/response delta, the persisted synthetic-time contract, and which interrupted claim states can safely become usable. Decide actual-review provenance and the intended timing exercise separately. The source does not justify choosing native providers, accepting customer identity from a file, in-place state migration, arbitrary dynamic dispatch or weakening current authority checks.
