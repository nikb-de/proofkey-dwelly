# Local model-to-runtime shadow bridge

This optional standard-library companion reads a **completed service-owned job** and saves an inert association. It does not generate a draft, call a provider, invoke a workflow, create an effect intent, or change the runtime. The service API, draft schemas, and Docker images are unchanged.

## Local command

Use Python 3.11 or newer (3.12 was tested). Run from the repository root, substituting an existing completed job and case:

```sh
python3 -B -m tools.dwelly_bridge \
  --service-state /absolute/path/to/service-state \
  --job-id 0123456789abcdef0123456789abcdef \
  --case-id delivery-logistics-001 \
  --shadow-state /absolute/path/to/private-shadow-state
```

The service state must belong to the current OS user and satisfy the source validator's filesystem checks. Shadow storage must be a separate private directory (existing directories need mode `0700`); it cannot be equal to, inside, or an ancestor of source or protected runtime state. The command creates its private output directory if absent. Do not point it at production or live-provider execution paths to produce a new result: it only reads already completed local artifacts.

The CLI always has no resolver and returns `status: "unmapped"`, `reason: "resolver_absent"`, `target: null`, `authorization: false`, and `effects: []`. This is a successful shadow observation with exit code 0. Rejected imports have exit code 1 and a bounded JSON reason, never raw exception text. Invalid command arguments also produce bounded JSON. The CLI accepts no binding JSON, resolver module, plugin, or authentication input.

## Trusted host composition

The API is `import_shadow(service_root, job_id, case_id, shadow_root, *, resolver=None)` in `tools.dwelly_bridge.bridge`. A host that already owns an open `CaseStore` can create `tools.dwelly_bridge.runtime_binding.RuntimeShadowResolver` with frozen `RuntimeShadowTarget` registrations, a fixed `AuthContext`, a trusted `authorize(target, auth)` callback, and a timezone-aware clock. This optional path requires the runtime's existing dependencies; the CLI has no runtime dependency.

The host must supply the exact source case/snapshot and complete expected runtime binding, checkpoint hash, profile/process/policy versions and allowed callers. It must derive those registrations and authentication from its own trusted context. A conversation label, recipient name, model output, score, or user-supplied mapping does not establish any of these identities. The callback must return literal `True` after the host's own scope check. The included synthetic fixture callback only exercises this contract; it is not production authentication.

Every configured resolver must expose `shadow_protected_roots`, a tuple of existing canonical absolute directory paths. The runtime resolver derives this from the already-open database parent. Missing or malformed protection fails closed before output creation. A successful read-only resolver result becomes `status: "shadow_recorded"` with the complete binding and original check time. It remains `authorization: false` with `effects: []`. Missing mappings return `unmapped`; denied, stale or unavailable mappings return a sanitized nonpersistent rejection without disclosing the target.

## Evidence and persistence

Records contain nine source identifiers/hashes/provenance scalars, a validated target or null, and a deterministic `import_id`. No raw draft, prompt, response, media, token, or credential is copied. The baseline is independently recomputed and identifies the **current verifier implementation**, not the original generator version. Saved live provenance establishes local linkage among the saved request, response and proposal; it is not external provider attestation or a fresh provider invocation.

Identity combines a canonical service-root namespace hash, job/case and the target case/object/principal/request identity (or unmapped). Identical retries return the original complete record and first `checked_at`. Changes to source evidence, checkpoint, revisions, generation, or versions under that identity reject with `idempotency_conflict`; a new checkpoint is not silently treated as another successful import. Store and readback validation reject malformed persisted values. Rejections are not stored.

This association is a point-in-time checkpoint annotation. It does not turn an unsent contact draft into operational planning, policy approval, authenticated business authority, or execution readiness.

## Local verification

```sh
python3 -B -m unittest discover -s tools/dwelly_bridge/tests -p 'test_*.py'
python3 -B -m unittest discover -s tools/dwelly_model/tests -p 'test_*.py'
python3 -B -m unittest discover -s tools/dwelly_cases/tests -p 'test_*.py'
python3 -B -m unittest discover -s tools/dwelly_service/tests -p 'test_*.py'
```

The base tool tests use only the standard library. For the optional runtime checks, activate an environment where the existing runtime project and its dependencies are installed. If needed, install that local project into your chosen virtual environment separately with `python -m pip install -e ./runtime`. This is dependency setup, not a bridge operation. Then run:

```sh
PYTHONPATH=runtime/src:runtime/tests python -B -m unittest \
  tools.dwelly_bridge.tests.test_bridge tools.dwelly_bridge.tests.test_cli
PYTHONPATH=runtime/src python -B -m unittest discover \
  -s runtime/tests -p test_shadow_binding.py
```

The integration test creates a real completed offline `JobStore` experiment and a separate real admitted synthetic `CaseStore`, then imports with the actual runtime resolver. Provider/network/gateway hooks fail if reached, and source/runtime file hashes and runtime row contents are compared before and after. It also tests the public command in a subprocess, denied scope, repeated imports, independent-process concurrency, overlap, symlinks and malformed resolver output. The optional runtime integration is explicitly skipped when the runtime package is unavailable; run the optional runtime commands to include it. Explicit suite paths above matter because namespace package directories are not all traversed by a single `unittest discover -s tools`. Local tests do not establish live-provider participation or operational acceptance.
