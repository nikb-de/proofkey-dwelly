# Observed-route stop v2: local acceptance, 2026-10-10

Status: the two real-clock trusted-library acceptance cases and the two retained
example invocations passed. Final frozen-source full-suite verification and
independent review are **pending** with the controller. This document does not
claim those gates, OpenSpec archival, or broader J07 integration are complete.

## Candidate and reproducibility

The production candidate is commit `c370fe7ecd5eda15c847e386090a2cb20600fa82`
on `codex/proofkey-runtime`. Task 3 adds only the example, acceptance tests and
this document. The resulting Task 3 commit is recorded in the task report at
`.superpowers/sdd/2026-10-10-observed-route-stop-v2/task-3-report.md`; the exact
tested example and test content hashes are:

```text
6f6e7f584e3476cb2053c45d5852efc811d1b8ffffda2343e0e6d00e972a3d41  runtime/examples/observed_stop_v2.py
aad3586af3c49235355038a0889e677ff41428c0dbd89dc0f57de9094b636bd3  runtime/tests/test_observed_stop_v2_acceptance.py
```

Evidence is retained at
[`outputs/observed-stop-v2-task-3-HKASE0/`](../../outputs/observed-stop-v2-task-3-HKASE0/).
`acceptance-source.sha256` includes the input and qualified interpreter hashes;
`production-source.sha256` records the 86 production inventory files.
`evidence.sha256` hashes the actual logs, public summaries and read-only evidence
collector. No interpreter, dependency or provider was installed or contacted.

All executions used the existing qualified interpreter with this prefix:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B
```

The acceptance suffix was `-m unittest test_observed_stop_v2_acceptance -v`.
The initial `red-1.log` records exit 1, two tests and two `FileNotFoundError`
errors because the example did not exist (0.005s unittest time; 0.09s wall).
After implementation, `green-1.log` records exit 0, two tests passing in 17.640s
(17.71s wall), with no failures, errors, skips or warnings. These are actual
missing-example RED and real-clock GREEN results, not expected outputs.

The example was then invoked separately with suffix
`runtime/examples/observed_stop_v2.py --parent <fresh-private-parent>` and, for
the second invocation, `--pending-wait`. Actual parents were the absolute
`complete-parent` and `pending-parent` paths inside the evidence directory.
The complete invocation exited 0 in 8.97s wall; pending exited 0 in 8.92s.
Their public output is retained as `complete-summary.json` and
`pending-summary.json`; `*-timing.log` retains `/usr/bin/time -p` output.

## Observed behavior

Both examples read only the existing `window-request.json` and
`window-fixture.json`, once each. The pending variant changes only the
in-memory `facts.case.completeness.value` to `missing` before serialization,
preparation and hashing. Neither prepared source is mutated.

Each preparation creates a new v2 release and explicit synthetic review grant
for that artifact hash. Each uses one unpatched `SyntheticReplayClock` and one
`RuntimeFactory` resource; run uses a 120-second context and stop a five-second
context. The clock's UTC value is a synthetic replay epoch advanced by actual
host monotonic time; no clock, engine, or wait-creation mock is used.

| Observation | Complete | Pending wait |
| --- | --- | --- |
| Run status | authorized | authorized |
| Stopped generation | G1 | G1 |
| Original request / claim / route preserved | true / true / true | true / true / true |
| Original business and budget deadlines not extended | true | true |
| Accounted tool calls | 11 → 12 | 11 → 12 |
| Persisted reschedules | 1 → 1 | 0 → 0 |
| Owner closed | true | true |
| Actual pending wait observed and stopped | not applicable | true |
| Wait context and expiry preserved | not applicable | true |

Wait comparison excludes only `WaitRecordV1.lifecycle` and `successor_hash`.
All other fields compare exactly, including the original wait expiry, wait
budget deadline, and origin checkpoint. Missing pending or stopped records
raise an exception. Clarification is not counted as a business reschedule.
Closure occurs in `finally`; command or close exceptions propagate, and
`owner_closed` is set from `resources.closed is True` only after close returns.
The public outputs contain only the exact specified keys, with no credential,
review identity, raw source or private path.

## New retained identities and receipts

`retained-evidence.json` records post-close file hashes and read-only SQLite
observations. Both fresh roots have mode `0700`, device `16777231`; their root
inodes are distinct. The names below are relative to the Task 3 evidence folder.

| Field | Complete | Pending wait |
| --- | --- | --- |
| Root | `complete-parent/case-29dba8b635974cd387140fa79f063a3a` | `pending-parent/case-ae7eb733bee64ec6a74139d31e340988` |
| Root inode | 155216251 | 155216298 |
| Artifact hash | `cebc14b6ba82598e49891621216e927ee267691388235fd450fe30bd7d740c69` | `841b242c521f05e322510b351de3f77aa90ecea5c06aab9effa060c8893b2820` |
| Stored release wire SHA-256 | `b7f4e318c7a184eed2f567a48760b4c3c864e0a65f4e29b7995ed8638f9326a3` | `08c296e97edb45ef4d17308a44e4c5c606d4b68b756b4ae978a79f9498c904ba` |
| Claim wire SHA-256 | `8602d68b9c56520a7a5b1400bec199abd21284338950d5aca55cf9f210bf9e41` | `c28291d02f4e5be00cacaef768440dde9dda5c7dd554b870e73dcaf5171af379` |
| Route wire SHA-256 | `23db8c7e0260f9b3f22413021ed050fd8f47eaa383ac68b72c6a0a9fea65a3d0` | `2f6f542780273bb5badac19ad9e3e643148de9d97f33ccca52700e7d5a5e20a5` |

Each retained root has one claim and one route, both `admission_observed`, and
a stopped G1 checkpoint. The pending root has one `stopped` wait; the complete
root has no wait. Every retained file hash, including registration marker,
SQLite journals, sources, shared-pressure data and claim/route stores, is in
`retained-evidence.json`. Whole-source/journal byte equality across authorized
reads is not claimed: stop performs and accounts for a current source read.

Both releases use `fixed-synthetic-observed-stop-v2`; dependency hash:
`af3bfa849d63f366760f7b02f9f7f1a2a5b8a9f6ab33b87f4f5c06663bb0aea5`.
The embedded 86-entry dependency inventory is identical, sorted and retains
`completeness='unestablished'`. Literal names follow; individual hashes are in
`retained-evidence.json` and `production-source.sha256`.

```text
__init__.py
adapters/__init__.py
adapters/case.py
adapters/delivery.py
adapters/messaging.py
adapters/operator.py
adapters/ownership.py
adapters/returns.py
adapters/scheduling.py
adapters/world.py
admission.py
admission_routes.py
api.py
assessment/__init__.py
assessment/audit.py
assessment/cache.py
assessment/contracts.py
assessment/coverage.py
assessment/drills.py
assessment/driver_contracts.py
assessment/drivers.py
assessment/isolation.py
assessment/labels.py
assessment/ledger.py
assessment/readiness.py
batch.py
batch_files.py
bootstrap.py
budget.py
cli.py
clock.py
contracts.py
engine.py
evidence/__init__.py
evidence/catalog.py
evidence/intake.py
evidence/processing_contracts.py
evidence/redaction.py
execution.py
execution_consumer.py
execution_trace.py
exporter.py
factory/__init__.py
factory/proposal.py
factory/release.py
factory/views.py
gateway.py
host.py
host_admission.py
host_contracts.py
host_files.py
host_writer.py
identity.py
journal.py
ownership.py
ownership_contracts.py
ownership_gateway.py
ownership_store.py
packet_contracts.py
packets.py
planner.py
policy.py
ports.py
process.py
processing.py
processing_orchestration.py
processing_summary.py
profiles.py
providers/__init__.py
providers/anthropic.py
providers/elevenlabs.py
providers/invocations.py
providers/protocols.py
providers/replay.py
providers/unavailable.py
registered_releases.py
release.py
replay.py
retained_state.py
schema.sql
source_retained_state.py
synthetic_provisioning.py
trace.py
verifier.py
wait_contracts.py
waits.py
```

## Limits and remaining gates

This is explicit trusted-library acceptance from this checkout. The small CLI
wrapper invokes that same library flow; it does not establish installed-wheel,
CLI restart, recovery, reply or owner-transfer support. Registered recover and
reply remain denied; the capability requires the original live owner and clock.
No stop guarantee after the original business deadline is introduced.

Validation covers the supported fixed v1.3 profile/process/policy and bounded
local source adapters. It does not establish protection against arbitrary
hostile constructors, arbitrary code or profiles, filesystem/OS compromise,
or general unbounded source inputs. The closed inventory's completeness label
remains unestablished. Synthetic review grants do not prove external human
review or provider participation. No network, live provider, paid operation,
historical root modification, merge, push or publication occurred.

The Task 2 focused result is retained without rerunning unchanged code:
159 tests passed in 468.747s, as recorded in
`.superpowers/sdd/2026-10-10-observed-route-stop-v2/task-2-report.md` and
`outputs/observed-stop-v2-task-2-20261010/green-targeted-final.log`. Its six
recorded source/test hashes were rechecked successfully during Task 3.
This is distinct from the final full suite.

Final frozen-source full-suite verification: **pending**. Independent task and
whole-branch review: **pending**; no approval outcome exists to cite here.
The controller owns those evidence links and the separate OpenSpec stop-leaf
archival after gates pass. Broader J07 integration and unrelated trace work
remain outside this acceptance scope.
