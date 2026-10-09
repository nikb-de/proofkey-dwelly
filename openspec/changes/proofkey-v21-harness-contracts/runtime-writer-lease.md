# Task13B4a — cooperative runtime writer lease

Internal prerequisite of approved Task13 OptionA; exact NEW runtime/src/proofkey/host_writer.py, MODIFY runtime/src/proofkey/host.py, NEW runtime/tests/test_host_writer.py. Root selects this smaller prerequisite before the four-file admission composition described in private preparation. No claim store, gateway hook, human-review resolver, active release pointer or migration in this slice.

The current built-in RuntimeFactory may create two resource owners over the same databases. Add one retained cooperative lock acquired before SimulatedWorld/CaseStore construction, held by the creator until clean runtime close. This is local coordination, not hostile-writer exclusion, atomic paired snapshots, resource origin, OS isolation or adaptation activation. Direct SQLite clients/custom factories that bypass this primitive remain outside its guarantee.

## Public interface and closed errors

```python
RuntimeWriterLease(root: Path)
lease.check() -> None
lease.close() -> None
RuntimeWriterFailure(ValueError).code  # writer_busy | writer_scope | writer_storage
RuntimeResources(profile, world, store, engine, *, writer_lease=None)
```

Lease is a mutable creator-owned authority object, not a serializable/frozen value or permission receipt. Exact class only for the optional resource argument; no caller JSON field or path loading. Old four-positional-argument RuntimeResources construction and RuntimeFactory.create(release,clock) signature remain compatible. Existing factory subclasses/custom trusted resources are not silently relabeled as lease participants.

## Resource and lock identity

- Input is an existing absolute platform Path: <=64 components, <=1024 characters, no dot-dot. Resolve aliases only for prohibition comparison; opening walks each component with no-follow directory descriptors, never creates resource directories. Existing factory's trusted two-level resource creation stays before lease acquisition.
- Reject exact root filesystem/home/current-workspace cwd targets including aliases before lock creation. A dedicated child resource directory is permitted. Do not open or mutate source/journal contents in this primitive.
- Resource root descriptor must be a directory owned by effective UID; do not change its permissions or ownership. Retained basename is exactly .proofkey-resource-writer.lock. Open read/write with create/no-follow/nonblocking and mode0600. Validate empty regular file, single link, owner effective UID and no group/world permissions before flock. Do not chmod foreign files, unlink/recreate a lock, or repair an unknown target. No broad recursive operations.
- Hold root descriptor and lock descriptor/identities for the entire lease. Nonblocking exclusive flock; a second owner returns writer_busy before any database construction. Invalid paths/aliases/target kind/ownership return writer_scope; operational storage failures writer_storage. Suppress raw path/OS text.
- Record root and lock device/inode. Rewalk root without following aliases and compare identities; lstat retained lock under root must match descriptor, be regular/single-link/owned/restricted. check() also requires creator thread and open state. Root or lock replacement/hardlink/permissions change denies; never acquire a replacement lock to recover.
- check() is a cooperative point-in-time check, not atomic against malicious path swaps, inherited descriptors or nonparticipating clients. No guaranteed hard I/O deadline: legacy factory has no ExecutionContext parameter. Bounded walks and nonblocking flock are not an OS sandbox or hard-time certification.
- close is creator-thread-only and idempotent for that creator. Release flock and both descriptors; no unlink of retained file. Closing after an identity failure still closes its held original descriptors, not an untrusted replacement. A foreign thread may not release ownership.

## Fixed-host integration

In RuntimeFactory.create: keep fixed registration/clock/profile/fixture validation and existing symlink/foreign DB checks. Create the trusted resource directory as before, acquire lease BEFORE the first world/journal constructor, check before and after each constructor and final release validation, then attach it to returned RuntimeResources. No database/account/source construction when busy or invalid lock. Exact inherited failure outcomes must not be converted into a successful result.

RuntimeResources with a lease checks it on construction. Creator close closes CaseStore before releasing lease, then marks closed. If store close fails, do not mark closed/release lease: owner retry remains possible; preserve actual failure. Factory failure cleans constructed store before releasing lease; if cleanup itself fails retain that failure and do not claim clean release. No blanket BaseException suppression or hidden reset. Source opens its own per-operation connections; no new world.close API is invented.

No adapter/engine/gateway/journal/source/schema/profile/process/registry/route/module fixture/test changes. No live/network/provider/install/server/subprocess/paid action or active profile selection. Existing workflow paths run unchanged under the built-in factory's lifetime lease. A later registered factory must use this same primitive, not a separate parallel lock.

## Tests and evidence

The selected plan contains two complete literal tests against the real builtin factory. First behavioral RED is exclusion failure from current factory, not missing-module scaffolding. Both real public journal/source images must retain complete payload on denied second creation; no fake accounting/world.

Add focused cases for direct lease lock type/symlink/hardlink/permission/alias/replacement, creator-thread check/close, idempotent close/reacquire, both builtin resource roots independent, and constructor failure after lease without swallowed failure or stranded ordinary lock. Temporary test trees only. Patch a public constructor solely to observe whether denial occurred before entry, not to replace a positive workflow.

Use qualified bundled3.12.14 with -B/no-bytecode/new private cache. Preserve exact launched raw RED/GREEN/fixture/error/timeout history. One finite NEW-module development discovery, then actual read/import/source/data/private/interpreter/platform closure and literal-ID freeze. Root separately authorizes ONE final NEW cohort, reads original results, performs proportional NEW checks, commits exact3 and obtains DIFFERENT NONAUTHOR separate Spec/Quality gate. No old full host/runtime cohorts repeated as evidence. Whole13/14/15/16/actual adaptation/drills/reproduction/event/archival remain unfinished.
