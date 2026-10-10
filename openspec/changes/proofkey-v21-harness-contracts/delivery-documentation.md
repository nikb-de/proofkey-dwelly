# Task15B0 — engineer-facing local documentation

Internal documentation slice of approved Task15. This is not a new product feature, source-release freeze, rights certificate, installation/reproduction receipt or event submission. Root owns specification/plan/commits; the original author writes exactly five new documents, with a different nonauthor reviewing Spec and Quality separately. Concurrent Task13B3 keeps its three source targets; no shared source changes are allowed.

## Exact scope

Create only `runtime/README.md`, `runtime/RIGHTS.md`, `runtime/LICENSE`, `runtime/NOTICE`, `runtime/.gitignore`. Existing source, tests, profiles, fixtures, manifests, dependency declarations, both locks and package metadata stay unchanged. No runtime import, operational demo, test suite, SQL, installation, server, provider/network/spend, publication, private-source copy, Git or cache cleanup by the author. Private task-owned report/check artifacts are allowed. This foundation explains present behavior; actual example execution requires its own assigned verification, not a manufactured receipt.

## README contract

English, engineer-facing and compact. Include purpose and status; prerequisites; the two complete stdin examples below; supported CLI syntax; result interpretation; library/API composition references; six adapter surfaces; adaptation and release boundaries; checks; rights and remaining gates. Use relative links to actual files in this runtime tree. No personal/private environment path, account email, credential value, private attachment or workspace evidence link belongs in public documents.

Purpose: ProofKey is an offline adaptive logistics contract harness. Engineer-first priorities are easy integration, fast adaptation, then reliable resolution. Default executable is two registered synthetic replay examples. Policy/action gates, journal/source and verified postconditions are distinct from model proposals. Refund/coverage dispositions are record-only, not financial execution.

Declare Python>=3.11 versus previously observed CPython3.12.14/macOS-arm64 separately. Require already available runtime dependencies; do not prescribe unapproved online install as clean reproduction. Source-checkout invocation uses an absolute checkout `runtime/src` supplied by the reader, not a hard-coded author path. Explain `PYTHONPATH` and `PYTHONDONTWRITEBYTECODE` as process instructions, not application credential settings. Console entrypoint installation and clean no-index reproduction remain unfinished.

Exact public CLI syntax is `python -m proofkey.cli [--release RELEASE] [--credential-ref REF] COMMAND`; launch flags also work after subcommand. Commands: `run --input FILE`, `reply --input FILE`, `batch --input FILE`, `recover --case-id ID`, `stop --case-id ID --generation REV`, `inspect-profile`, `transfer`. FILE `-` uses stdin. Run accepts CanonicalRequest, reply ScopedReply, batch a JSON list. `transfer` is explicitly unavailable. Do not advertise `--help`, `prepare-release`, arbitrary profile path, native credential, fresh-text, provider/model/deadline or activation flags.

The two complete example JSON bodies are:

```json
{"case_id":"C1","object_id":"O1","principal_id":"U1","request_id":"REQ1","request_revision":"v1","consent_revision":"v1","kind":"reschedule_window","consent_mode":"window","arguments":{"window_start":"2026-10-08T10:00:00+00:00","window_end":"2026-10-08T12:00:00+00:00","inventory":{"item-1":1}},"evidence_ids":[],"narrative":null}
```

```json
{"case_id":"C1","object_id":"O1","principal_id":"U1","request_id":"REQ1","request_revision":"v1","consent_revision":"v1","kind":"goods_refusal","consent_mode":"unknown","arguments":{"inventory":{"item-1":1}},"evidence_ids":[],"narrative":null}
```

First uses `host-window-replay-v1`, second `host-goods-replay-v1`. Use a separately new private `mktemp -d` launch parent for each; default writes `.proofkey/{resources,inventories,runs}` there. Preserve outputs and never reset prior resources to manufacture a fresh result. Archived dates and fixed fingerprints are replay data, not current consent or arbitrary-case support. Examples must be labelled instructions not newly verified evidence. Synthetic/media/readback and unsupported states remain visible.

One JSON CliReceiptV1 is emitted. Exit0 means committed coordination, not every effect succeeding; 2 denial/unavailable/input error, 3 pending/deadline, 4 infrastructure/publication/bootstrap/ownership error, 64 usage. Explain accepted versus verified and return-created versus physically-received; inspect result states, export hashes and shutdown independently. Unknown/partial/waiting must remain visible.

List the exact six `ports.AdapterBundle` surfaces/methods. Library starting point is `tests/test_cli_parity.py`; API composition is `tests/test_api_boundary.py` and parity source `tests/test_api_parity.py`, not a global ASGI application. Document POST `/v1/commands`, POST `/v1/batch`, GET `/v1/profile`, trusted resolver's `x-proofkey-proof` opaque handle, creator/lifespan and literal loopback-only serving. Localhost/header text alone is not authentication. No server command or positive fresh-text/media/ASR claim.

Adaptation proposals/tests/review and actual activation are distinct. New registry/route foundation is still in development and not wired into host admission. No actual human review, authenticated snapshot origin, multi-resource atomic switch or complete runtime closure is established. Source release `prepare_release` requires trusted context; `verify_release_static` is static readback; actual `verify_release` unavailable. Existing source-level checks can be documented as commands not freshly run results; whole-suite execution waits for a coherent hold.

## Rights, license and notices

`RIGHTS.md` is a readable scope/status inventory, not a populated SourceReleaseContextV1 or proof of ownership. Apache-2.0 applies to actually owned new application code per approved intent/pyproject; do not invent a copyright holder, contributor grant, employer ownership, license to raw docs or permission to publish. Private attachments/chats/recordings/archives/organizer/customer/provider sources and protected references stay excluded; redaction, public URL, hash, possession or synthetic-looking filename is not a rights grant. Preserve originals privately.

`LICENSE` is the complete unmodified standard Apache License2.0 including its standard appendix, verified against local installed `opentelemetry_api-1.45.1.dist-info/licenses/LICENSE` SHA256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`. Its bracketed appendix is the standard example, not an invented project holder. This source is only license-text evidence, not redistribution of that package or its attribution.

`NOTICE` names ProofKey and describes the scoped application license, with dependency attribution references. Explicitly incomplete third-party artifact/license/notice joins; do not claim a cleared distributable or alter LICENSE conditions. Record MIT, MIT-CMU, BSD-3-Clause, PSF-2.0, Apache-2.0 and MPL-2.0 as local metadata families, not legal conclusions. Certifi remains separately MPL; httpx's actual notice join unresolved. Setuptools84 build backend is separate from nineteen API wheel pins; ffmpeg fixture generator is not runtime/redistributed.

Explain three different artifacts: `requirements.lock` eight version pins without hashes; `requirements-api.lock` nineteen historical CPython3.12/macOS-arm64 wheel pins excluding setuptools and unselected extras; `DEPENDENCIES.json` older API-deferred metadata, not the current complete closure. No wheelhouse, source ownership, no-index install, packaged tests, sixty-second video/native playback, provider/model participation, protected isolation, actual activation, drills or eligibility follows from these documents. Do not modify stale inventory silently.

`.gitignore` contains only generated/local artifacts: `.proofkey/`, `__pycache__/`, `*.py[cod]`, `.venv/`, `venv/`, `build/`, `dist/`, `*.egg-info/`, `.pytest_cache/`, `ANSWERS/`, `outputs/`. Ignore is neither deletion nor source-release allowlist/rights evidence; never blanket-ignore source/tests/profiles/fixtures or reinterpret pre-existing caches as removed.

## Acceptance and evidence

Before writes, author rechecks five absent targets and selected immutable source/document pins. Retain exact original commands/errors and all five SHA256 values. Perform finite static content/link/signature/JSON/standard-license-byte checks only, with no imports/operational launch. Root reads every new file, verifies current old sources, independently checks embedded exact JSON/links/CLI parser/lock scopes and canonical license equality, then commits exactly five documents. Different nonauthor separately reviews specification fidelity and usability/quality. Runtime behavior, installation/reproduction, rights clearance, media and wholeTask15/16 remain unchecked. Whole OpenSpec change stays active.
