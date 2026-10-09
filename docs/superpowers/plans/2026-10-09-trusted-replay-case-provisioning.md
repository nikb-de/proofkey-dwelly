# Trusted Replay Case Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an integrating engineer prepare and run a genuinely new structured synthetic delivery case through the installed library and trusted CLI bootstrap without editing installed code.

**Architecture:** Add one fixed-family preparation module, then an optional existing admission composition on trusted CLI configuration. Preparation produces an inspectable private artifact but no authority; external synthetic review and transport authority remain separate. Reuse existing registered execution, state ownership and outcome verification without changing their protocol.

**Tech Stack:** Python 3.12.14 on observed macOS arm64; existing Pydantic/standard library, unittest, setuptools 84.0.0 and the existing locked offline wheelhouse. No new dependency.

**Spec:** `openspec/changes/trusted-replay-case-provisioning/design.md` (written design approved after commit `2e4ace3` on 2026-10-09); executable requirements in the same change's `specs/trusted-replay-case-provisioning/spec.md`; tasks in its `tasks.md`. The user approved this implementation plan after commit `657b668`; implementation outcomes still require verification.

## Global Constraints

- Work only in `/Users/nbk/.codex/worktrees/proofkey-runtime/Pitch project`; preserve the original checkout and existing `outputs/`.
- The profile is the packaged, pinned `flat-v1.3` profile; process versions remain v1.
- No profile path, module path, factory selection or implementation byte override in the input.
- The helper never constructs a review grant, transport handle, database, admission attempt, claim, route or effect.
- Use one immutable byte snapshot for source validation, hash, private fixture file and source declaration.
- Both helpers require the exact `SyntheticReplayClock`; configuration requires the original clock object and a fresh bounded context, not an expired preparation context.
- Unknown top-level/scope/fact-envelope fields are rejected. Raw fixture maximum: 1 MiB; maximum container depth: 64 with root at depth 1. Existing encoded declaration limits remain unchanged.
- Never overwrite or adopt existing children, follow aliases, derive paths from request identifiers, or create runtime state beneath site-packages.
- Every new directory is private, owned by the current user and mode 0700; staged files are single-link regular files with mode 0600. All temporary descriptors close on success and failure.
- Prepared artifacts are not authority. Existing source ACL, full original request, admission claim/route, debt, deadline, effect verification and owner-close checks remain mandatory.
- Do not edit `host.py`, `host_admission.py`, `registered_releases.py`, `engine.py`, `gateway.py`, `journal.py`, `process.py`, profiles, fixed fixtures or executable pin allowlists. Stop for design revision if those changes prove necessary.
- No native services, money, provider/model/ASR calls, narrative/media processing, generic plugins, manifest launcher, registered recovery/reply/stop enablement, process/ack changes or migration.
- Run two new cases through library and trusted CLI bootstrap: four fresh-state positive positions, not four renamed builtin demonstrations.
- No merge, push, publication or dependency acquisition. One frozen full regression run after focused tests; every failure and attempt remains recorded.

## Review Focus

1. Raw fixture fits 1 MiB but embedding it exceeds the existing 1 MiB source declaration limit: reject before allocation (Task 1).
2. Caller mutates a nested request after constructing the spec or replaces a parent between I/O operations: detach input and reject changed identities, without adopting replacement state (Tasks 1–2).
3. Review takes longer than preparation's control window, or grant expires after configuration: distinct bounded contexts, same clock, launch-time grant recheck (Task 3).
4. A CLI bootstrap omits custom `--release`, or combines an unrelated host registry and valid-looking composition: fail without implicit remapping (Task 3).
5. A successful-looking receipt lacks persisted effects, original claims/routes or successful close: independent installed readback must fail the position (Task 4).

## File map and ownership

| File | Responsibility |
| --- | --- |
| `runtime/src/proofkey/synthetic_provisioning.py` (new) | Closed spec, bounded input snapshot, private preparation, prepared summary and trusted CLI configuration helper |
| `runtime/src/proofkey/bootstrap.py` | Optional exact admission composition; no change to default semantics |
| `runtime/src/proofkey/cli.py` | Forward existing trusted composition to dispatcher |
| `runtime/tests/support_synthetic_provisioning.py` (new) | Independently authored synthetic data and local test timing helpers; never imported by production or installed examples |
| `runtime/tests/test_synthetic_provisioning.py` (new) | Input, filesystem, preparation and declaration tests |
| `runtime/tests/test_synthetic_provisioning_cli.py` (new) | Trusted configuration, timing, selection and registered launch tests |
| `runtime/tests/test_synthetic_provisioning_acceptance.py` (review fix extension) | Permanent narrow regressions for acceptance denial-state and exceptional-shutdown retention |
| `runtime/scripts/verify_synthetic_provisioning.py` (new) | Reusable offline build/install driver; keep run output private and separate |
| `runtime/examples/registered_case_bootstrap.py` (new) | External trusted Python bootstrap using installed public interfaces, not a new product CLI |
| `runtime/examples/registered-cases/` (new) | Two request/fixture pairs and factual usage notes; no real personal data |
| `docs/verification/2026-10-09-trusted-replay-cases.md` (new) | Exact acceptance evidence and unresolved boundaries |

Source-test interpreter: `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python`. Every source-test command below runs from the worktree root with `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests`. Do not use that `PYTHONPATH` for installed verification. Store RED/GREEN logs, diffs, reviews and progress in this plan's private SDD workspace; use new uniquely named output directories for installations and runtime evidence.

---

### Task 1: Bounded detached input and private preparation primitives

**Files:** Create `synthetic_provisioning.py`, `support_synthetic_provisioning.py` and `test_synthetic_provisioning.py` under the paths above. No other production file changes.

**Interfaces:** Produce `SyntheticCaseReleaseSpecV1(host_release_id, registered_release_id, resource_id, request, fixture_bytes)`, `SyntheticPreparationFailureV1(code, *, retained_root=None)` and internal `_validate_input(spec, clock, execution)` / `_allocate_private(parent, clock, execution)` primitives. The latter owns descriptor lifetime through a context manager. Later tasks consume these private helpers; they are not a public extension API.

- [ ] **Step 1 — add deterministic independent test data.** Use this complete data recipe in the test-only support module. Its SHA is computed independently rather than calling the product fingerprint builder. Every call returns new mutable values.

```python
from datetime import timedelta
from hashlib import sha256
import json
from proofkey.contracts import CanonicalRequest
from proofkey.execution import ExecutionContext

def cj(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()

def context(clock, seconds=5):
    return ExecutionContext.capture(clock.now() + timedelta(seconds=seconds), clock)

def case_data(kind="reschedule_window"):
    window = kind == "reschedule_window"
    suffix = "WINDOW" if window else "GOODS"
    ids = dict(case_id="J06-CASE-" + suffix, object_id="J06-ORDER-" + suffix,
               principal_id="J06-USER-" + suffix, request_id="J06-REQ-" + suffix)
    inventory = {"j06-widget": 2, "j06-cable": 1}
    arguments = {"inventory": inventory}
    if window:
        arguments.update(window_start="2026-10-08T13:00:00+00:00",
                         window_end="2026-10-08T15:00:00+00:00")
    body = dict(**ids, request_revision="v1", consent_revision="v1", kind=kind,
                consent_mode="window" if window else "unknown",
                arguments=arguments, evidence_ids=[], narrative=None)
    business = sha256(cj({key: body[key] for key in
                        ("kind", "consent_mode", "arguments")})).hexdigest()
    values = {
        "case.binding": ids, "case.request_revision": "v1",
        "case.authorization": "verified", "case.generation": "G1",
        "case.question_revision": "v1", "case.result_revision": "v1",
        "case.completeness": "complete", "customer.consent": "granted",
        "customer.consent_revision": "v1", "customer.consent_mode": body["consent_mode"],
        "customer.request_fingerprint": business,
        "delivery.status": "scheduled" if window else "delivered",
        "delivery.risk": "safe", "delivery.stage": "eligible",
        "scheduling.capacity": ["J06-S3", "J06-S4"], "scheduling.slot": "J06-S0",
        "scheduling.slot_details": {
            "J06-S3": {"start": "2026-10-08T13:00:00+00:00", "end": "2026-10-08T14:00:00+00:00"},
            "J06-S4": {"start": "2026-10-08T14:00:00+00:00", "end": "2026-10-08T15:00:00+00:00"}},
        "policy.version": "v1", "ownership.state_revision": "v1",
        "ownership.state": "accepted", "ownership.epoch": 0,
        "ownership.owner": ids["principal_id"], "goods.inventory": inventory,
        "goods.quantity": 3, "goods.refusal": "none", "service.refusal": "none",
        "returns.destination": "J06-DEPOT-B", "returns.status": "none",
        "messaging.permission": "granted", "messaging.recipient": ids["principal_id"],
        "operator.packet_hash": "b" * 64, "operator.packet_revision": "v1",
        "operator.recipient": "J06-OPERATOR"}
    facts = {key: dict(value=value, revision="v1", case_id=ids["case_id"],
                      object_id=ids["object_id"], evidence_ref="synthetic-j06:" + key)
             for key, value in values.items()}
    fixture = dict(version="synthetic-provider-v1", as_of="2026-10-08T10:00:00+00:00",
                   scopes=[dict(case_id=ids["case_id"], object_id=ids["object_id"],
                                principal_id=ids["principal_id"],
                                readers={ids["principal_id"]: "j06-synthetic-proof"})], facts=facts)
    return CanonicalRequest.model_validate(body), fixture
```

- [ ] **Step 2 — RED: exact input and finite envelope.** Add tests for subclass/wrong spec and request types, detached nested arguments, unsupported kind, nonempty narrative/evidence IDs, empty/oversized/nonbytes fixtures, invalid UTF-8, duplicate keys at every envelope level, NaN/Infinity/overflow-to-infinity, depth 64/65, braces/escaped quotes inside strings, missing/extra envelope keys, multiple scopes, wrong outer IDs, wrong binding and wrong business hash. Assert private parent inventory is unchanged on every preallocation failure.

```python
def test_duplicate_fixture_key_fails_before_allocation(self):
    request, fixture = case_data()
    raw = cj(fixture).replace(b'"version":', b'"version":"bad","version":', 1)
    spec = SyntheticCaseReleaseSpecV1("J06-H", "J06-L", "J06-R", request, raw)
    before = tuple(self.parent.iterdir())
    with self.assertRaises(SyntheticPreparationFailureV1) as caught:
        _validate_input(spec, self.clock, context(self.clock))
    self.assertEqual(caught.exception.code, "invalid_input")
    self.assertIsNone(caught.exception.retained_root)
    self.assertEqual(tuple(self.parent.iterdir()), before)
```

Run `-B -m unittest discover -s runtime/tests -p test_synthetic_provisioning.py -v`; retain the expected missing-module/API failure before implementation.

- [ ] **Step 3 — implement finite snapshot validation.** Use a frozen/slots spec, exact type guards and existing ID rules. At spec construction detach its exact `CanonicalRequest` through the existing `parse_command` bound, then revalidate at preparation rather than retaining caller-owned nested containers. Reject any narrative or evidence IDs. Require exact clock and use existing `control_context(execution, clock)` at each bounded phase; map its timeout without capturing a new context. Validate fixture nesting with a nonrecursive quote/escape-aware scan before strict JSON decoding; after decoding iteratively reject nonfinite float values. Apply the exact finite envelope rules in the approved design. Use this encoding recipe for all declarations:

```python
def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")

source_json = _canonical({"kind": "route-source-declaration-v1", "mode": "synthetic",
    "source_id": "fixed-world-fixture",
    "documents": [{"source_id": "fixed-world-fixture", "text": fixture_bytes.decode("utf-8")}]})
if len(source_json) > 1048576:
    raise SyntheticPreparationFailureV1("invalid_input")
```

Build/check static declaration bytes and installed implementation snapshots before allocation as well. Raw input below the ceiling whose encoded declaration is too large must fail before creating a child. Add that exact regression with a large quote/backslash-containing fact value.

- [ ] **Step 4 — RED/GREEN private allocation.** Add tests for relative/dotdot paths, root/home/CWD/package parents, symlink ancestors, nonprivate mode/wrong ownership, fixed UUID collision, replacement parent at an I/O barrier, injected write failure and timeout. Instrument real descriptor opens/closes in a scoped test, not a process-wide descriptor count. Preserve outside sentinel bytes and any preexisting child.

Use `_PathPins` to hold/recheck full ancestry and `host_files._write/_read` for bounded descriptor-relative staging. Do **not** call `_PathPins.child`, which adopts an existing child. The exclusive creation core is:

```python
parent_pins.check()
parent_fd = parent_pins.entries[-1][0]
name = "case-" + uuid4().hex
os.mkdir(name, mode=0o700, dir_fd=parent_fd)
retained_root = parent_pins.path / name
parent_pins.check()
```

Hold/check the new root and each fixed child with no-follow descriptors; record full ancestry identities for later revalidation. Allocate `data`, `resources`, `control`, `inventories`, `outputs` exclusively. Require current uid/private mode and explicit single-link/0600 file checks after staging. Return recorded paths/identities, never descriptors. Close every held descriptor in `finally`, including `BaseException` exits; ordinary failures carry only a bounded code plus the optional private retained root. `str(error)` is the code, never a path or raw underlying exception. Do not delete partial children.

- [ ] **Step 5 — verify and commit.** Run the focused file to GREEN; reread the diff against the approved finite envelope and filesystem contract. Record exact RED/GREEN commands/counts and commit only Task 1 files. Fresh task review must approve spec compliance and quality before Task 2.

### Task 2: Assemble the existing fixed synthetic release without authority

**Files:** Extend `synthetic_provisioning.py` and `test_synthetic_provisioning.py` only.

**Interfaces:** Produce `prepare_synthetic_release(spec, *, parent, clock, execution) -> PreparedSyntheticReleaseV1`. Prepared fields used by later tasks are `host_release`, `registry`, `binding`, `root`, `control_parent`, `inventory_parent`, `output_parent`, plus private recorded path identities and original clock reference. `summary()` exposes only `host_release_id`, `registered_release_id`, `resource_id`, `profile_version`, `process_version`, `business_fingerprint`, `artifact_hash`, `status="prepared_synthetic_unapproved"`.

- [ ] **Step 1 — RED: prepared output is data, not execution.** For both test cases, prepare a release and independently check exact fixture bytes/hash, private modes, registry commitment, fixed implementation path/hash list and honest declarations. Patch runtime/world/store constructors to raise if preparation touches them; forbid any review-grant constructor call. Assert no SQLite/lock/claim/route/effect exists. Assert summary/repr/errors do not contain the synthetic proof or source body. Mutate an original input after spec construction and prove the prepared request commitment is detached.

```python
prepared = prepare_synthetic_release(spec, parent=self.parent,
    clock=self.clock, execution=context(self.clock))
self.assertEqual(prepared.host_release.fixture_path.read_bytes(), raw)
self.assertEqual(prepared.host_release.fixture_hash, sha256(raw).hexdigest())
self.assertEqual(prepared.registry.commitments(),
    (("J06-L", prepared.binding.artifact_hash),))
self.assertEqual(prepared.summary()["status"], "prepared_synthetic_unapproved")
self.assertFalse(list(prepared.root.rglob("*.sqlite")))
self.assertNotIn("j06-synthetic-proof", repr(prepared))
```

Run the focused tests and retain failure because the public preparation API is absent.

- [ ] **Step 2 — implement staged release construction.** Read the packaged fixed profile through the existing pinned release/read semantics; preserve its raw bytes. Canonicalize its validated model for the registered profile declaration. Read precisely `FIXED_IMPLEMENTATION_PATHS` from the installed package using bounded no-follow single-link reads; preserve ordering and immutable byte snapshots. Build declarations and the `ReleaseArtifactV1` before allocating: that constructor checks each 1 MiB blob and the 8 MiB aggregate lower bound without requiring a resource path/inode. Check encoded-envelope size conservatively using the bounded planned path and maximum allowed integer-identity widths. Resource path/device/inode and final registry bytes are finalized only after allocation, through existing constructors; any later I/O/identity failure retains the private partial root. Never change registered-release limits or invent a usable preallocation resource identity.

The construction uses these existing constructors, not test imports:

```python
implementations = tuple(ReleaseBlobV1(name, data) for name, data in snapshots)
dependency_json = _canonical({"kind": "route-closure-declaration-v1",
    "mode": "synthetic_declaration", "completeness": "unestablished",
    "entries": [{"name": item.name, "sha256": item.sha256, "role": "code"}
                for item in implementations]})
factory = KnownFactoryV1("fixed-synthetic-v1",
    tuple((item.name, item.sha256) for item in implementations),
    sha256(dependency_json).hexdigest(), "offline_synthetic")
resource = ResourceSetV1(spec.resource_id, str(resource_path), resource_device,
    resource_inode, "journal.sqlite", "world.sqlite", account_ids, "claimed_case_id")
artifact = ReleaseArtifactV1(spec.registered_release_id, factory.factory_id,
    resource.resource_id, profile_json, policy_json, source_json, proposal_json,
    tests_json, regression_json, migration_json, agent_json, dependency_json, implementations)
registry = ReleaseRegistryV1(artifacts=(artifact,), factories=(factory,), resources=(resource,))
binding = HostExecutableBindingV1(spec.host_release_id, spec.registered_release_id,
    registry.resolve(spec.registered_release_id).artifact_hash, factory.factory_id,
    factory.implementation_pins, factory.dependency_hash)
```

Here `snapshots` is Task 1's bounded ordered tuple; `resource_path/device/inode` come from the held private `resources` child; `account_ids` is the sorted tuple of all non-null profile capability shared-limit accounts. Construct the host release with staged `data/profile.json`, `data/fixture.json`, the raw profile SHA, validated profile/process/policy hashes, exact fixture SHA, request kind and derived business fingerprint. Do not use the registry's canonical profile JSON hash as the raw staged-profile hash.

Declaration values are exact: existing policy mapping; equal baseline/candidate hashes with empty proposal diff; empty test cases; regression execution `unestablished` with SHA of those exact tests bytes and empty case IDs; migration `preserve` with no affected contracts; agent authorship `unestablished`, label `synthetic-provisioning-v1`; dependency completeness `unestablished`. Store source text exactly once from the immutable accepted bytes, not a later path reread.

- [ ] **Step 3 — revalidation/failure tests.** Inject profile/fixture/pin drift before use, replaced root/ancestor, hardlink/symlink/FIFO file substitutions, staging-mode drift and failures at each write boundary. Require no usable prepared result on failure, all descriptors closed, no automatic cleanup and outside files intact. Independently decode registered source/profile bytes and compare to staged bytes/validated canonical profile. Prove two preparations have distinct resource identities/artifact hashes even for identical business input.
- [ ] **Step 4 — GREEN, review and commit.** Run `test_synthetic_provisioning.py`, `test_host.py`, `test_host_admission.py`, `test_release_route_foundation.py`, `test_factory_registration.py`, `test_installed_resources.py`; retain per-file results. Commit Task 2 files and obtain a fresh task review before CLI integration. No full-suite duplication yet.

### Task 3: Trusted configuration and existing CLI forwarding

**Files:** Extend `synthetic_provisioning.py`; modify `bootstrap.py`, `cli.py`; create `test_synthetic_provisioning_cli.py`.

**Interfaces:** Produce `configure_registered_cli(prepared, *, approvals, review_id, auth_resolver, clock, execution, host_limits, interface_limits, total_seconds, publication_reserve_seconds, shutdown_seconds) -> CliConfiguration`. Add optional `admission_composition: LocalAdmissionCompositionV1 | None = None` after existing public defaults. Default callers keep their current behavior and permitted factory/clock interfaces.

- [ ] **Step 1 — RED exact composition and unchanged defaults.** Tests must show the current configuration rejects the new field and the current CLI cannot forward it. Cover exact/nonexact prepared, composition, factory and clock; single matching host/registered selection; bad duration limits; unchanged default CLI. Use a focused constructor spy for the forwarding unit test, then actual registered execution for both kinds without replacing runtime results.
- [ ] **Step 2 — implement configuration without new authority.** Revalidate prepared ancestry, data hashes and registry/binding; reject a different clock object. Construct the existing composition and call existing `validate_composition` with the caller's fresh context before returning configuration. The essential composition is:

```python
composition = LocalAdmissionCompositionV1(prepared.registry, prepared.binding,
    approvals, review_id, prepared.control_parent)
validate_composition(prepared.host_release, clock, composition, execution)
configuration = CliConfiguration(factory=RuntimeFactory(), auth_resolver=auth_resolver,
    profile_registry=ProfileRegistry((prepared.host_release,)), clock=clock,
    host_limits=host_limits, interface_limits=interface_limits,
    output_parent=prepared.output_parent, inventory_parent=prepared.inventory_parent,
    total_seconds=total_seconds, publication_reserve_seconds=publication_reserve_seconds,
    shutdown_seconds=shutdown_seconds, admission_composition=composition)
```

In non-None `CliConfiguration.__post_init__`, require exact existing composition/factory/clock, reconstitute its existing validated typed fields, require exactly one host registry entry and one matching registered commitment, and resolve `binding.host_release_id` to the matching host release/commitments. Use existing `ProfileRegistry` representation in this module; do not add a new host protocol. Do not resolve time-sensitive authority there without an execution context; the helper and runtime provide those checks. In `cli.main` change only dispatcher construction:

```python
dispatcher = HostDispatcher(configuration.factory, configuration.auth_resolver,
    configuration.profile_registry, clock, inventory_root, configuration.host_limits,
    release_id=args.release, admission_composition=configuration.admission_composition)
```

- [ ] **Step 3 — lifecycle and denial regression matrix.** Use exact `SyntheticReplayClock` with scoped deterministic patches to its `now`, `monotonic` and `wait` methods, following existing host-admission tests; never substitute runtime outputs. Test: review delay beyond preparation context with new configuration context succeeds; expired configuration context fails; future/expired/wrong-artifact/unknown review fails; grant expires after successful configuration and launch fails; wrong proof creates no business effect; omitted/custom-wrong release is rejected; source/pin/root mutation fails; registered recover/reply/stop/transfer retain their existing denial/unavailable behavior. Existing pending/duplicate claims remain unchanged, with no helper reset/rebinding.

```python
with redirect_stdout(output):
    code = main(["run", "--input", str(request_path),
                 "--release", prepared.host_release.release_id,
                 "--credential-ref", "j06-user"], configuration=configuration)
receipt = CliReceiptV1.model_validate_json(output.getvalue())
self.assertEqual(code, 0)
self.assertTrue(receipt.shutdown.owner_closed)
self.assertEqual(receipt.run.command.result.status, "authorized")
```

The test explicitly provisions a `SyntheticReviewGrantV1` with `synthetic_rehearsal` provenance bound to `prepared.binding.artifact_hash` and a separate `AuthResolver` for the fixture principal/proof. Grant creation belongs in test/application code, never in either helper. Public outputs must contain neither proof text, grant data nor fixture declaration bodies. Distinguish preallocation failure from later audited denial; do not demand deletion of legitimate admission records.

- [ ] **Step 4 — GREEN and reviewable commit.** Run new CLI tests plus `test_cli.py`, `test_cli_parity.py`, `test_host.py`, `test_host_admission.py`, `test_api_boundary.py`, `test_api_parity.py`, `test_release_route_foundation.py`, `test_release_manifest.py`. Recheck no parser option, fixed pin or default-release change. Commit only Task 3 files and obtain spec/quality review.

### Task 4: Four installed positions, reusable example and final evidence

**Files:** Create the script/example/data and verification document in the file map; update `runtime/README.md`, `docs/verification/judge-remediation-2026-10-09/{README.md,support-matrix.md}` and OpenSpec task status. Keep raw receipts, SQLite, private paths and proof-bearing sources under a new private output directory, not in public reports.

**Review-driven test extension:** Task 4's independent review found missing reusable denial-state assertions and dropped shutdown evidence after an exceptional library run. Add the narrow acceptance test module named above, retain RED/GREEN, and include it in the frozen full suite. No production-runtime file or authority boundary is expanded.

**Interfaces:** Consume only installed `SyntheticCaseReleaseSpecV1`, the two helpers and existing `HostDispatcher`/`run_command`/`cli.main`. Produce four factual position results plus failure denominators and source/package inventories. The external example is Python integration guidance, not a new product launcher or authority source.

- [ ] **Step 1 — RED positive acceptance before finalizing examples.** Materialize the two literal request/fixture pairs from the independent data recipe as standalone synthetic JSON. The installed example must read those files without importing test support or rewriting a builtin fixture. Check the reschedule business fingerprint differs from builtin `e51bc7df8304c4f88f09e979b60505c20610e2bd13209ac60afd8e9d47a8af34`, and goods from `f1a95a447f2a6726a3459f37790557326b3361a15894a7b4a2baa28451321ce2`. Add acceptance assertions before running; an unmet effect/claim/export must fail rather than silently become a note.
- [ ] **Step 2 — reusable private build/install driver.** Base archive inspection, dependency verification and process receipts on existing `outputs/proofkey-installation-2026-10-09/verify_distribution.py`, but check in a new task-specific driver at `runtime/scripts/verify_synthetic_provisioning.py`. It accepts explicit `--commit`, `--wheelhouse`, `--dependency-receipt`, `--output`; all output must be newly allocated. Do not rerun the old driver's eight builtin positions. Validate all 20 already staged wheel/backend hashes before use. Stage `git archive <commit> runtime` outside checkout; build wheel and sdist with separate backend processes; inspect source/data membership, rebuild from sdist and compare semantic bytes. The new module is automatically included by existing Python-source packaging; examples remain external to site-packages and must not accidentally appear in the wheel.

```python
safe_env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INDEX": "1",
    "PIP_CONFIG_FILE": os.devnull}
for hook in ("build_wheel", "build_sdist"):
    subprocess.run([build_python, "-B", "-c",
        f"from setuptools.build_meta import {hook}; import sys; {hook}(sys.argv[1])",
        str(artifact_dir)], cwd=staged_runtime, env=safe_env, check=True)
subprocess.run([installed_python, "-m", "pip", "install", "--no-index",
    "--find-links", str(wheelhouse), "--require-hashes", "--no-compile",
    "-r", str(staged_runtime / "requirements-api.lock")], cwd=scratch,
    env=safe_env, check=True)
subprocess.run([installed_python, "-m", "pip", "install", "--no-index",
    "--no-deps", "--no-compile", str(candidate_wheel)], cwd=scratch,
    env=safe_env, check=True)
subprocess.run([installed_python, "-m", "pip", "check"], cwd=scratch,
    env=safe_env, check=True)
```

The driver creates build/installed venvs through the already available source interpreter's stdlib `venv`. `build_python`, `installed_python`, `scratch`, `staged_runtime`, `artifact_dir`, `wheelhouse`, `candidate_wheel` are driver-local explicit absolute paths recorded in its private receipt. Preserve every command/stdout/stderr/exit/duration and failure; do not retry into the same state directory.

- [ ] **Step 3 — run four independent installed positions.** Invoke an external probe with `installed_python -I -B` from scratch, no source/test `PYTHONPATH`, and verify every loaded `proofkey` file is within the new environment. Each case × surface receives a fresh private parent and preparation, explicit synthetic review, and separate resolver. Library uses existing dispatcher/run_command; the CLI surface invokes existing `main(argv, configuration=configuration)` with the explicit custom `--release`. Use fresh bounded contexts as in Task 3 and the original launch context through the business operation. Always retain and check the actual shutdown receipt.
- [ ] **Step 4 — independent persisted readback.** After successful owner shutdown, inspect existing databases read-only (SQLite URI `mode=ro`, no provider initialization or mutation) and decode using existing claim/route/value models. Independently verify:
  - journal original request equals the exact supplied request, generation `G1`, checkpoint binding equals receipt binding;
  - one actual admission claim and route at `admission_observed`, matching case/attempt/reservation/release/artifact/original-request commitments;
  - exactly one verified `reschedule` at `J06-S3` (the first permitted slot), or exactly one verified `register_goods_refusal` plus `create_return` with inventory `{"j06-widget":2,"j06-cable":1}`, quantity 3 and destination `J06-DEPOT-B`;
  - return is initiated, not physically received or paid; no unrelated business effect;
  - committed run inventory, queued/started/finished host inventory, joined command identity and actual SHA-256 of every published ANSWER/REASONING file;
  - no pending close, every position retained in denominator, original fixtures and installed site-packages bytes unchanged.

Use `runtime/tests/test_cli_parity.py` for ordinary journal/export semantics and `test_host_admission.py` for claim/route layout. Do not reopen an executed registered root through a builtin/legacy runtime just to inspect it; avoid claiming reconstructed in-memory provider call history after exit. The example bootstrap may output its existing CLI receipt; a separate private evidence channel holds paths and review/source bodies.

- [ ] **Step 5 — installed negative positions.** At minimum retain wrong proof, wrong/omitted release, expired/mismatched review, drifted staged fixture and an unsafe alias parent. Run file-corruption negatives on separate controlled copies, never the positive installed package. Capture expected denial and actual stage-specific state; no unauthorized effect or reset of pending claims is allowed.
- [ ] **Step 6 — focused then frozen full regression.** Run all Task 1–3 focused files first. Freeze a sorted path/SHA inventory of runtime source, test fixtures and dependency lock files, commit the candidate, and run exactly one full `-B -m unittest discover -s runtime/tests -v` with raw logs/exit/duration. Compare inventory and HEAD after the run. Installed evidence must refer to that same executable candidate; documentation-only changes afterward are identified separately. No test-count target is hardcoded from the earlier 1,696-test baseline.
- [ ] **Step 7 — finish review and living documentation.** Record command, candidate/wheel/sdist hashes, target, four positions, every negative, closure and unresolved boundaries in the new verification document. Update only supported J06 rows; keep J14, general release verification, registered controls, native integration, media, real review, timed adaptation and other platforms open. Obtain whole-change independent review, reconcile verified findings, run strict OpenSpec validation, then archive this child only if all acceptance gates pass. Do not merge/push/publish. Do not remove existing outputs or unrelated worktrees.

## Plan self-review and approval record

- Spec coverage: bounded inputs/private lifecycle → Task 1; fixed artifact/no authority → Task 2; explicit composition/timing/denials → Task 3; installed outcomes/immutability/evidence → Task 4.
- All five Review Focus conditions have explicit tests in their owning task.
- Additional limit clarification: encoded source may overflow before raw bytes reach 1 MiB. Reject before allocation using unchanged release limits; this narrows acceptance, not authority or protocol.
- Independent read-only plan review found no Important blocker in the revised plan; checked source contracts and literal fixture data. This is not a runtime verification result.
- Current state: written design and implementation plan approved; task execution begins from `657b668` with a focused 10-test clean baseline.
- Preserved execution method: autonomous subagent-driven development, one implementation task at a time with fresh task reviews and a final whole-change review.
