# ProofKey runtime

ProofKey is an offline adaptive logistics contract harness, built for easy integration, fast reviewed adaptation and reliable resolution. Six provider-neutral surfaces share policy gates, an intent journal and postcondition verification. Model proposals do not grant permission to act. Refund and coverage dispositions are record-only; no money is executed.

For a captured receipt and content-free execution trace, follow the [short source quickstart](QUICKSTART.md).

The default executable exposes two registered **synthetic replay** examples. Recorded installed console/module/library/API checks at `5bc38c8` cover these two cases on the target described below. Other commands remain bounded by their separate support contracts; this is not a complete runtime, source-release, live-provider or event-readiness certification.

## Start here

- **Run the existing demo:** use the two source-checkout examples below with already installed dependencies and separate fresh state directories.
- **Use an installed package:** see [Installed target](#installed-target). Package-owned data no longer depends on the source checkout.
- **Connect a system:** first read the [support and evidence map](#support-and-evidence-map). Six interfaces exist; no native logistics connection is established. The default public path accepts two fixed cases, not an arbitrary profile.
- **Understand a result:** read [Read results](#read-results). Acknowledged, verified, pending, physically received and paid are different outcomes. Do not retry an unknown effect with a new key.
- **Work on remaining capabilities:** use the [complete remediation register](../docs/verification/judge-remediation-2026-10-09/README.md), not the historical panel score, to find the next dependency and its exit evidence.

## Support and evidence map

Evidence is specific to its candidate, launch path and cases. Recorded installed results do not qualify later source changes. The [detailed dated matrix](../docs/verification/judge-remediation-2026-10-09/support-matrix.md) retains command conditions and historical source findings; [Read results](#read-results) explains denial, pending and unknown outcomes.

| Path | Evidenced scope | Candidate / evidence | Limits |
| --- | --- | --- | --- |
| Fixed installed replay | Window reschedule and whole-order goods refusal plus return initiation; 8/8 console, module, library and in-process API positions | J13 `5bc38c8`; [installation verification](../docs/verification/2026-10-09-installed-resources.md) | CPython 3.12.14 / macOS arm64, exact artifacts and two fixed synthetic cases |
| Trusted new synthetic cases | New window/goods cases through trusted Python library or explicitly configured CLI; final 4/4 positives and 7/7 negatives | J06 `80e0d6f`; [trusted-case verification](../docs/verification/2026-10-09-trusted-replay-cases.md), including all five attempts: 16/20 positive and 34/35 negative passes | Separate preparation, synthetic review and transport authority; no standalone manifest launcher or API composition selector |
| Source trace quickstart | Two source captures and a bounded, content-free receipt renderer; 1,798-test frozen regression passed and child archived | `7b4c6e2`; [trace verification](../docs/verification/2026-10-10-safe-evidence-trace.md), [source quickstart](QUICKSTART.md) | Source only, not installed acceptance. `unverified_receipt_projection`: dispatch unknown, original readback not observed, current publication files unchecked |
| Other command routing | `inspect-profile`, wrapper `batch`, `recover`, `reply` and `stop` have separate routes and conditions; `transfer` is unavailable | Source inspection at `633ed41`; [command details](../docs/verification/judge-remediation-2026-10-09/support-matrix.md#commands-by-entrypoint), [CLI](src/proofkey/cli.py), [API](src/proofkey/api.py) | Syntax/routing is not a positive workflow receipt. API exposes only commands, batch and profile routes; retained state, authority and time still govern controls |
| Registered v1 controls | `fixed-synthetic-v1` admits business `run` only; profile inspection is separate | J06 `80e0d6f`; [verified scope](../docs/verification/2026-10-09-trusted-replay-cases.md) | Registered recover/reply/stop unavailable; retained or interrupted state does not grant control authority |
| Observed-route stop-v2 | Opt-in same-owner trusted-library stop; completed and pending-wait real-clock acceptance; 1,829-test frozen regression | `4c8fd5a`; [stop-v2 verification](../docs/verification/2026-10-10-observed-stop-v2.md) | Source/synthetic only; original live owner and clock required. No restart/recover/reply, default CLI/API or installed-v2 qualification; broader J07 stays open |
| Six offline interfaces | Case, delivery, scheduling, returns, messaging and operator contracts with simulated adapters | Source inspection at `633ed41`; [contracts](src/proofkey/ports.py), [simulated composition](src/proofkey/adapters/world.py) | Not six live integrations or complete six-port acceptance; no native provider/model or human-onboarding evidence |

Return initiation is not physical receipt or payment; queued handoff is not operator acceptance. The trace reports supplied receipt fields, not independently verified dispatch, original readback or current files. Renderer exit 0 means rendering succeeded, not that a business effect succeeded.

The historical pre-installation-fix baseline was **1,693 tests, all passing**, at `40138e1`, with 246 runtime files unchanged during execution. [Earlier verification](../docs/verification/2026-10-09-registry-commitments.md), J13 installation evidence and J06 trusted-case evidence retain their own candidate-specific regression results.

## Installed target

The J13 installed candidate `5bc38c8` was observed on **CPython 3.12.14 / macOS arm64**, with all nineteen exact runtime/API wheels from `requirements-api.lock` and the separately pinned setuptools 84.0.0 build backend. Ten built-in profiles, two fixed host fixtures and `schema.sql` ship inside that package. Writable journals, inventories and outputs remain outside site-packages.

Use a new virtual environment, an explicitly provisioned trusted wheelhouse, this lock and the reviewed `proofkey_runtime-0.1.0-py3-none-any.whl`. Install the lock with `pip install --no-index --find-links WHEELHOUSE --require-hashes -r requirements-api.lock`, then the project wheel with `pip install --no-index --no-deps WHEEL`. These uppercase arguments name caller-provisioned paths, not network sources. API use needs the entire recorded closure; selecting `api-test` alone does not install the API extra.

From a fresh working directory, clear `PYTHONPATH` and use the environment's `proofkey` executable or `python -m proofkey.cli` with the exact requests below. The installation checks exercised both cases through console, module, trusted library composition and in-process API, with independent persisted-effect/export readback and owner closure. They also checked that installed site-packages remained unchanged. Repository-relative links in this guide describe the source tree; they are not an installed SDK documentation bundle.

No fresh Linux/Windows run, zipped/frozen execution, unfamiliar-engineer study, complete release verifier, native provider connection or distribution-rights clearance is implied. Artifact locations and hashes are in the verification report; no automatic download or public server is needed to run the offline cases.

## Trusted new synthetic cases

The optional [external Python bootstrap](examples/registered_case_bootstrap.py) reads
independent structured requests and source fixtures, then uses the installed
`SyntheticCaseReleaseSpecV1`, `prepare_synthetic_release` and
`configure_registered_cli` APIs. Preparation creates a private artifact, not
execution authority. The application separately supplies a synthetic review
grant and transport resolver before calling the existing library or CLI entrypoint.

Fixture text must contain no actual CR (U+000D), including CRLF or bare-CR line
endings; use LF. The existing admission consumer normalizes actual CR, so
preparation rejects it as `invalid_input` before child allocation. JSON-escaped
`\r` string content is accepted, and accepted bytes are never normalized.

See [the two literal examples and usage](examples/registered-cases/README.md).
Their acceptance requires four fresh installed positions, exact persisted
effects/claim/route/export joins and actual owner closure. Evidence for `80e0d6f` and
remaining gates are in [J06 verification](../docs/verification/2026-10-09-trusted-replay-cases.md).
These examples stay outside site-packages; the default CLI and its two fixed
releases remain unchanged. This is a trusted Python integration hook, not a
standalone configuration-file launcher, native integration or human approval.

## Source-checkout quickstart

Python **>=3.11** is declared in [pyproject.toml](pyproject.toml); only the installed target above has current installation evidence. Other interpreters/platforms remain unqualified. These source examples require the runtime dependencies to be already available to `python3`: pydantic 2.13.5, pillow 12.3.0, pypdf 6.10.0 and their dependencies. They select source explicitly, unlike the clean installed checks.

Start in this checkout's `runtime/` directory. The first line derives your absolute source path before changing directory. `PYTHONPATH` selects that source tree; `PYTHONDONTWRITEBYTECODE` avoids creating bytecode. These are process settings, not application credentials.

Window rescheduling:

```sh
PROOFKEY_SOURCE_DIR="$(pwd -P)/src"
PROOFKEY_DEMO_DIR="$(mktemp -d)"
cd "$PROOFKEY_DEMO_DIR"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PROOFKEY_SOURCE_DIR" python3 -m proofkey.cli run --release host-window-replay-v1 --input - <<'JSON'
{"case_id":"C1","object_id":"O1","principal_id":"U1","request_id":"REQ1","request_revision":"v1","consent_revision":"v1","kind":"reschedule_window","consent_mode":"window","arguments":{"window_start":"2026-10-08T10:00:00+00:00","window_end":"2026-10-08T12:00:00+00:00","inventory":{"item-1":1}},"evidence_ids":[],"narrative":null}
JSON
```

Then, in the same shell, use the already absolute source path and a **different** new directory for goods refusal:

```sh
PROOFKEY_GOODS_DIR="$(mktemp -d)"
cd "$PROOFKEY_GOODS_DIR"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PROOFKEY_SOURCE_DIR" python3 -m proofkey.cli run --release host-goods-replay-v1 --input - <<'JSON'
{"case_id":"C1","object_id":"O1","principal_id":"U1","request_id":"REQ1","request_revision":"v1","consent_revision":"v1","kind":"goods_refusal","consent_mode":"unknown","arguments":{"inventory":{"item-1":1}},"evidence_ids":[],"narrative":null}
JSON
```

Keep both directories: `$PROOFKEY_DEMO_DIR` and `$PROOFKEY_GOODS_DIR`. Each launch creates `.proofkey/{resources,inventories,runs}` under its working directory. Release-specific resources retain world/journal state across invocations; each command has new inventory/output children. Preserve previous results rather than resetting resources to manufacture a fresh case. Launch ancestry must pass no-follow checks, and private children must have safe ownership/permissions.

The 8 October 2026 dates, identities and fingerprints are fixed replay data, not current consent. Changing the JSON does not register a new case. These examples have no narrative or media. [CLI parity source](tests/test_cli_parity.py) and the separate installed checks verify a reschedule in the first case and refusal-registration/return-creation effects in the second. Registration uses [flat-v1.3](profiles/flat-v1.3.json) with [window](fixtures/development/packet-world-v1.json) and [goods](fixtures/development/host-goods-world-v1.json) fixtures; byte-identical installed copies live under `proofkey/resources/`. Other profile files are not automatically CLI registrations.

## Supported commands

The module entrypoint is:

```text
python -m proofkey.cli [--release RELEASE] [--credential-ref REF] COMMAND
```

The same `main` is declared for the installed `proofkey` entrypoint. Launch flags also work after the subcommand. The default release is `host-window-replay-v1`; the default credential registration is synthetic, not native authentication.

| Command | Input |
| --- | --- |
| `run --input FILE` | CanonicalRequest JSON |
| `reply --input FILE` | ScopedReply JSON |
| `batch --input FILE` | JSON list, preserving every ordinal |
| `recover --case-id ID` | Existing scoped case |
| `stop --case-id ID --generation REV` | Existing case and generation |
| `inspect-profile` | Registered release inspection |
| `transfer` | Explicitly unavailable |

`FILE` may be `-` for bounded stdin. Recovery, reply and stop depend on retained state and authority; syntax alone does not promise a positive result. See the [CLI parser](src/proofkey/cli.py) and [trusted bootstrap](src/proofkey/bootstrap.py) for the closed launch contract.

## Read results

The CLI emits one JSON `CliReceiptV1` to stdout. Read the command/result, publication/export and shutdown independently.

| Exit | Meaning |
| --- | --- |
| 0 | Completed, committed coordination; not a guarantee that every business effect succeeded |
| 2 | Denied, unavailable or invalid input |
| 3 | Deadline or started/pending work |
| 4 | Infrastructure, queue, publication, bootstrap or ownership/shutdown error |
| 64 | Invalid usage |

Dispatch acceptance is not verified completion. Return creation is not physical receipt or a refund. Keep partial, unknown and waiting states visible; inspect per-effect authoritative readbacks, actual export hashes and whether the owner closed. Default 120-second total, 10-second publication reserve and 2-second shutdown settings are not evidence of hard I/O cancellation or a timed-drill pass.

## Integrate

Use the public `run_command`, `run_batch` and `read_run_inventory` exports. [Library composition](tests/test_cli_parity.py) demonstrates an explicit clock, resolver, registered profile, original execution context, creator-owned dispatcher, bounded close and public output readback. Exact signatures live in [batch.py](src/proofkey/batch.py) and [batch_files.py](src/proofkey/batch_files.py). These examples are test source, not a production bootstrap.

[API composition](tests/test_api_boundary.py) supplies trusted runtime/auth/profile objects and existing absolute output/inventory parents to `create_app`; [API parity source](tests/test_api_parity.py) compares the two replay cases with library behavior. The [API](src/proofkey/api.py) exposes POST `/v1/commands`, POST `/v1/batch` and GET `/v1/profile`. Its trusted resolver maps one bounded `x-proofkey-proof` header to an opaque transport handle. Header text or localhost alone is not authentication. Lifespan owns creator-thread startup/use/shutdown; `serve_loopback` accepts literal loopback addresses only. Construct the application explicitly; there is no ready global ASGI application. API dependencies are optional and no server is started by this guide.

[AdapterBundle](src/proofkey/ports.py) contains exactly six surfaces:

| Surface | Methods |
| --- | --- |
| case | read_case, read_principal |
| delivery | read_delivery, read_refusal, register_goods_refusal, register_service_refusal |
| scheduling | list_permitted_slots, read_schedule, reschedule |
| returns | read_return_policy, read_return, create_return |
| messaging | read_message, send_clarification, send_status |
| operator | read_receipt, read_resume, read_owner, enqueue_handoff, transfer_owner |

Reads take `ReadRequest` and return `AuthorityReadback`; effects take `EffectIntent` plus optional `deadline` and return `DispatchResult`. `transfer_owner` also accepts optional `AuthContext`. The implementation uses a simulated operational world distinct from the runtime journal. These interfaces and the two quickstart cases do not establish complete six-surface or native-provider coverage. [Media provenance](fixtures/development/media/provenance.json) describes blank PDFs, solid images and a short tone, with `semantic_readiness: false`; byte intake is not actual speech recognition or meaningful multimodal processing.

## Adapt and release

Adaptation requires a source-grounded proposal, changed contract tests, review and a compatible release/migration decision. Incoming content cannot activate a profile or expand permissions. The registry/route foundation now has an opt-in library bridge for the fixed synthetic runtime: `RuntimeFactory.create_registered` plus `RuntimeResources.run_registered`. Trusted bootstrap code supplies the exact registered code/profile/resource binding and an explicitly synthetic review grant; case content cannot supply this authority. The host persists the original request, seals its route/binding before importing case debt, then records observed admission after execution.

First adoption requires a new isolated resource root and fresh dedicated control stores. Marked roots cannot use the legacy factory; reopening requires the original stores and exact binding. Missing stores, pending claims and uncertain cleanup deny entry rather than silently repairing or retrying. Registered recovery/reply/stop, arbitrary profile loading and migration remain unavailable; the unmarked legacy path is unchanged. This bridge is not exposed as a CLI default. The [engineering handoff](../docs/verification/2026-10-09-registered-host-admission.md) records its historical test results; [baseline corrections](../docs/verification/2026-10-09-baseline-corrections.md) and the [timing correction](../docs/verification/2026-10-09-admission-phase-budgets.md) record subsequent scoped verification. Actual human review, authenticated snapshot origin, a multi-resource atomic switch and complete runtime closure are not established.

[Source preparation](src/proofkey/release.py) requires a trusted `SourceReleaseContextV1`. `verify_release_static` means static source readback; actual `verify_release` is unavailable. Source preparation is not clean installation or permission to distribute. The current CLI does not expose release preparation or activation.

## Checks

From `runtime/`, these existing source-level checks can be run in a separately assigned verification with dependencies available:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -m unittest test_cli_parity.CliParityTests.test_real_module_window_and_goods_positive_match_library_and_public_persisted_facts -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -m unittest test_api_parity.ApiParityTests.test_actual_window_and_goods_match_library_journal_source_and_export -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The API check needs the optional API-test dependencies. The whole suite requires a coherent source hold. No command above was run for this documentation slice, and none substitutes for fresh copied-package reproduction.

## Rights and remaining gates

[LICENSE](LICENSE) applies to actually owned new application code; [RIGHTS.md](RIGHTS.md) and [NOTICE](NOTICE) describe the incomplete source/dependency rights evidence. The [eight version pins](requirements.lock), [nineteen historical wheel pins](requirements-api.lock) and [older dependency inventory](DEPENDENCIES.json) have different scopes. Those declaration files alone are not an offline wheelhouse; the exact staged dependency closure and actual bundled-notice inventory are recorded in the [installation verification](../docs/verification/2026-10-09-installed-resources.md), without granting distribution rights.

The observed no-index installation and eight fixed-case execution positions are verified separately above. Source ownership/rights clearance, complete release reproduction, broader installed workflows, a sixty-second video and native playback remain unfinished. Tests remain source-level verification and are deliberately excluded from the runtime distributions. Actual provider/model participation, protected isolation/human custody, activation/migration, four timed drills, whole-branch review and event eligibility require their own evidence. These documents do not authorize publication, submission or paid/live work.
