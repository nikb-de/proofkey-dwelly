# Task13B4b — registered fresh-case host admission

This is an internal refinement of the approved engineer-first harness, not new
authority for live providers, actual human approval, activation, or payments.
It follows the cooperative writer lease and B3 declaration/route store. The
implementation is a **fixed synthetic executable bridge**, not arbitrary profile
execution. Changed processes/acknowledgements and the 600-second drill stay open.

## Scope and architecture

Only four product/test paths: new `host_admission.py`, changes to `host.py` and
`gateway.py`, and new `test_host_admission.py`. Keep the engine, journal schema,
admission accounting, B3 registry/routes, six ports and fixtures unchanged.

```text
trusted registration + synthetic review grant
                 |
     exact executable/profile/resource check
                 |
writer lease -> durable prepared claim -> engine execution scope
                                           |
                              unbound discovery-read debt
                                           |
                  B3 route reserved -> durable binding seal
                                           |
                        existing atomic journal admission
                                           |
                      ordinary deterministic workflow
                                           |
                  complete journal/source capture + B3 join
                                           |
                           admission_observed claim
```

The first registered factory entry requires a new isolated resource root: no
pre-existing journal/source DB and no foreign registration marker. This avoids
stranding existing fixed-host cases. Old registrations/data are not migrated.
A durable exact registration marker binds resource identity, host release,
registered artifact and control directory identity. The ordinary fixed factory
must deny a marked resource **under the writer lease before opening either DB**.
Registered reopen requires the same marker/configuration. Marker creation is
exclusive/no-follow/0600, synced, bounded and never overwritten or auto-repaired.
Malformed/partial/aliased markers deny. Marker installation failure may leave a
blocked empty root; it never authorizes fallback to the old factory.
On marker-present reopen, **both control DBs must already exist and validate**;
never let the B3 constructor recreate a lost route store or initialize a missing
claim store. First adoption initializes/validates the two control stores before
installing the marker, and initializes runtime DBs afterward. A crash leaving a
marker without complete runtime DBs also denies on reopen; repair is out of
scope. Existing control material on an unmarked first-adoption root must be
validated as exact and empty, not silently discarded. Marker/control identity
checks prevent a changed configured control directory from laundering debt.

## Trusted inputs and public seams

New exact frozen value types in `host_admission.py`:

- `HostExecutableBindingV1`: host release ID, B3 release ID/artifact hash,
  factory ID, sorted implementation pins, dependency hash, fixed factory key.
- `SyntheticReviewGrantV1`: review ID, artifact hash, actor ID, exact scope
  `admit_fixed_local_replay`, provenance `synthetic_rehearsal`, aware issue/expiry.
- `ProvisionedReviewResolverV1`: finite unique grants; rejects actual/activation
  scope. A grant is deliberately provisioned fixture authority, **not evidence of
  an actual reviewer**. It is distinct from request authentication.
- `LocalAdmissionCompositionV1`: one exact B3 registry, executable binding,
  review resolver/ID and existing scoped control directory. One composition owns
  one registered resource; neither request JSON nor declaration blobs choose it.
- `AdmissionClaimV1`: detached canonical full wire record with independently
  checked grammar/hashes and public state/attempt/binding projections.

New `RuntimeFactory.create_registered(release, clock, *, composition, execution)`
constructs the same fixed engine/source only after validation. Existing
`create(release, clock)` and custom trusted factories remain compatible.
`RuntimeResources.run_registered(request, auth, *, execution)` is the sole new
entry. Optional exact composition on `HostDispatcher` chooses this path for
`run`; registered recover/reply/stop deny (preserved-route recovery is future
work). Plain host behavior on unmarked roots stays unchanged. No CLI flag yet.

Gateway gets an optional exact admission owner. It checks the active prepared
entry at `execution_scope` **before** the journal scope/replay lookup; it checks
full original request/auth at the start of `bind_request`, uses the durable
attempt ID, and seals immediately before `admit_from_attempt`. Construct it via
the engine's existing `gateway=` argument. No monkeypatch/callback from input,
subclassed journal, private SQL connection or new transaction shortcut.
The owner rechecks exact store/world/gateway/engine/clock associations as well
as creator/lease/context at entry and seal; replacing an exposed resource field
must not retain the old owner's authority.

## Bridge validation

Reject subclasses/mutable aliases and bound all input sizes. Compare B3
registration against independently provisioned binding and actual fixed host:
artifact/factory/dependency/pin set; implementation bytes at fixed local logical
paths; full profile bytes plus profile/process/policy hashes; source fixture
bytes; all non-null account IDs; root path/device/inode; exact
`journal.sqlite`/`world.sqlite`; fixed synthetic clock/factory; current v1.3
profile and supported v1 process/policy. Missing, extra, unsupported, stale or
unreadable material denies before either runtime database is opened. Dependency
inventory completeness/native closure remains unestablished. Never import/exec
blobs or copy current hashes into historical qualifications.

## Durable claim protocol

Use a separate bounded control claim store, not a B3 schema change. Canonical
records retain full request (all defaults, narrative whitespace and evidence
order), caller/proof digest (never raw proof), resource/artifact/review identity,
preallocated claim/attempt/route IDs, original timing, initial journal/source
image hashes, and state. Immutable original material has its own hash; current
record has a full hash. Sealed states add full actual binding and route
reservation hash; observed state adds final image/observation hashes. Each wire
read revalidates exact keys/types/hashes and state-specific requirements.

Maximum 4096 claims, 262144 bytes/row and 8MiB aggregate; bounded parsing and
schema/data preflight; no unbounded fetchall. New SQLite store uses known exact
meta/claims schema, DELETE journal, FULL synchronous, no migration/repair of
unknown or partial DBs. Own no-follow regular single-link 0600 file and identity
checks. Serialize claim access under the resource lease and existing exclusive
B3 route-store owner; no cross-database atomicity claim. Acquire the B3 owner
before opening claims; close both before releasing the resource lease.

1. Validate original auth/request, review grant, lease and original execution
   context. Outside engine scope capture complete public journal/source images.
   Deny any existing correlation across ALL case/original/request/result/wait/
   intent/transfer/invocation/audit/admission account/attempt/entry rows. Orphan
   records count; `has_case` is insufficient. Reject any pending prepared/sealed
   claim before new entry. Persist `prepared` before `start_admission`.
2. Gateway execution guard requires this creator's active exact entry/context.
   Direct engine use without it denies before replay/disclosure/read debt.
   Preserve ordinary discovery accounting: it remains unbound debt until admit.
3. Compare actual policy binding/checkpoint, original/attempt/profile versions.
   Reserve and read back B3 full route, commit/read back `binding_sealed`, then
   allow the unchanged atomic journal admit/import. Any uncertain seal fails
   closed; no invented generation or binding from request data.
4. After engine leaves execution scope, capture complete public images under
   the lease. Run B3's full admission join and only then persist
   `admission_observed`. If no admission happened, retain prepared/sealed state.
   An exception after admission/effect means uncertainty, **not zero effects**.
5. After restart, any prepared/sealed claim blocks new entry. No auto engine
   retry, claim deletion, debt reset, migration or repair. Exact observed claims
   remain historical bookkeeping, not replay permission. Initial resource
   isolation + marker means no inference from unknown historical host inventory
   is needed; this run's `started` inventory must not self-deny preparation.

Use supplied UTC/monotonic anchors, clip admission control operations to at most
five seconds, never recapture a fresh deadline to hide elapsed time. The engine
keeps the caller's original full execution cap. Cleanup is creator-owned and
available after expiry. Retain failed cleanup handles and deny further work;
never release the outer lease while an inner owner remains live/uncertain.
Expose only finite failure codes, no raw proof/SQL/payload details.

## Acceptance and non-goals

TDD with real local factory/engine/journal/source/route store: positive fresh
reschedule and goods case; exact route+claim+actual binding join; old fixed
unmarked path; declared-vs-actual pin/profile/resource/grant mismatch; existing
and orphan correlation denial before new debt; direct-engine/foreign-thread/
changed-original/expired-context denial; legacy marked-root denial; prepared and
sealed restart blocking with debt preserved; seal failure before import;
observation failure after actual admission; construction/close cleanup ordering.
Use narrow faults at actual persistence boundaries, not mocks of whole engine.
Run new-module discovery then full runtime regression once on the final
candidate. Retain genuine RED failures and all original outputs. Independent
nonauthor spec/quality review is required. Passing these tests is not full Task13,
activation, actual-human review, media/model integration, hostile-writer
exclusion, atomic snapshot custody, production readiness or event submission.
