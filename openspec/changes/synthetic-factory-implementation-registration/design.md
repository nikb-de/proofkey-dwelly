# Explicit synthetic factory registration — proposed design

## Intended outcome and scope

Restore meaningful current-source factory regression coverage while retaining
historical evidence. The immediate user goal is to fix observed failures, not to
weaken the admission gate or manufacture an assessment pass. This interface is
for trusted host configuration, not case content. A Python constructor does not
authenticate the host; the existing host trust boundary still applies.

## Options considered

1. **Explicit immutable synthetic registration (recommended).** Add one optional
   context value, keep the historical default, and bind new provenance. This is
   a small interface extension requiring code review and new tests.
2. **Historical isolated regression lane.** Run matching historical source and
   tests together. Honest historical evidence, but not current coverage.
3. **Replace hashes, self-hash expectations or monkeypatch constants.** Rejected:
   loses historical identity or makes the admission check tautological.

## Data flow and components

`independent fixed test fixture -> trusted FactoryContext registration -> exact
material comparison -> registration-bound proposal -> bound regression/review
checks -> registration-bound staged_simulation`

Add `SyntheticImplementationRegistration`, frozen and slotted, with
`registration_id: str`, `provenance: str` (exact value
`local_controlled_synthetic`) and `implementations: tuple[tuple[str, str], ...]`.
Append `implementation_registration: SyntheticImplementationRegistration | None`
to FactoryContext, default None. None follows the historical recipe unchanged.

The explicit path requires the exact six registered logical source paths, no
duplicates/aliases/additional paths, exact tuple/string types, lowercase 64-hex
SHA-256 values and a nonempty bounded ASCII registration ID. Reject subclasses
and mutable containers. IDs match `[a-z0-9][a-z0-9._-]{0,127}`. Use a 2 MiB
per-source limit and a 12 MiB aggregate source limit on the explicit path only;
do not change historical admission with new source-byte limits. Do not expose environment, CLI or packet
overrides or a global registration mutator.

Normalize the immutable host value once. Pass it consistently through initial
validation, `_resolve`, `_proposal_hash` and `prepare_proposal`. Candidate source
bytes must match independent fixed expected pins exactly. Source mismatch is
`unsupported_adapter_implementation`; malformed registration is
`invalid_implementation_registration`; oversize material is
`material_limit_exceeded`.

For the explicit path only, the proposal body and staging manifest contain
`implementation_registration` with exactly `registration_id`, `provenance` and
`inventory_sha256`. Its digest preimage is the existing canonical UTF-8 JSON
encoding of a list of `{"path": <logical path>, "sha256": <lowercase hash>}`
objects sorted by path; hash the encoded bytes using SHA-256. Existing observed
`adapter_sources` remain. Thus
different registrations cannot reuse proposals, regression or approval hashes.
The default adds no fields and retains the old canonical serialization recipe.

## Current-source evidence and limits

Create a separate literal fixture with a new final ID and the fixed six pins.
The expected hashes must not be derived from submitted material at runtime.
The behavioral lane starts in a fresh interpreter, verifies the selected
snapshot before importing its six implementation modules, and uses an empty
private `pycache_prefix` with bytecode writes disabled so existing timestamp
caches are not read. Verify imported module origins against the selected
checkout after import. A reused/preloaded module or replacement/monkeypatch of
those six modules invalidates the lane. Add a negative probe for a preloaded
stale module; an on-disk hash alone must not grant a current-source receipt.

Require optimization level zero in both launcher and child, remove inherited
`PYTHONOPTIMIZE`, and record the effective flag. Existing behavioral helpers use
assertions; optimized execution cannot produce passing evidence. The inner
suite is exactly `test_adaptation_factory` and `test_factory_registration`,
never the qualifier's own tests. Record the test-ID inventory and require every
planned test once with no skipped, expected-failure or failed positions.

The broader snapshot includes added/untracked executing files, the qualifier
and selected fixtures, not only Git-tracked files. Validate origins and retained
identities for loaded project-local factory, contracts and test/helper modules
against the selected snapshot as well as the six pins. External distribution
identity is reported separately. These checks are trusted-test provenance,
not hostile-code isolation or complete transitive closure.

Record the observed broader source/test/fixture inventory, Python/dependency
identity and pre/post stability in a separate run manifest. That manifest also
enumerates exact regression-receipt byte SHA-256 values, execution IDs, proposal
hashes and any staged-manifest byte SHA-256 values. Finalize it only after all
required import/stability checks succeed. A failed check invalidates associated
run evidence. This explicit association does not alter legacy receipt schemas
or authenticate the host. Six pins are not a transitive runtime closure.

The current six pins as observed at `f220de2` are recorded in the investigation;
the implementation run must independently confirm them and record its exact
source snapshot. Do not call a filename or ID “qualified” or “actual”.

All current business tests execute real current SimulatedWorld, verifier and
ProcessController code. Recreate all proposal/regression/simulated-review
artifacts under the new binding. Readiness candidate stays unavailable;
supported control stays staged_simulation only. No activation, migration,
authenticated human review, live agent or 600-second drill is established.

## Verification

First demonstrate the missing opt-in registration path fails. Add strict type,
mutation, malformed hash, alias, duplicate, missing/extra source, size and drift
tests. Assert historical constants and complete legacy serialization stay
unchanged using golden proposal/staged-manifest bytes and digests with fixed
historical materials, timestamps, receipts and inventory. Add an explicit-path
golden vector for the registration object and digest preimage;
historical material may be used only for serialization tests, never as evidence
that historical source executed in the current runtime.

Legacy vector generation supplies fixed synthetic regression rows directly,
without calling current behavioral helpers through `reviewed()` or the default
`evidence()` path. The fixed historical material, time and case hashes are
serialization inputs; they are not a historical execution receipt.

Verify deterministic reordered inventories, different-ID hash separation,
cross-registration receipt rejection, consistent prepare/resolve/check/stage
binding and detached context/artifacts. Run all factory tests, not only the
fourteen formerly blocked selectors. Independently review both the extension
and the relevant five-file semantic changes; publish exact review scope and
remaining closure limits. Then run the complete suite with API dependencies
available. No test pass alone grants production qualification.

## Rollback

Remove the explicit registration argument from callers to restore the historical
default. Do not rewrite past artifacts. No durable runtime schema or activation
state changes are proposed.
