# Registered host admission — engineering handoff

## What changed

The library can now bind an explicitly registered, fixed synthetic profile to
the existing runtime. This is an opt-in path, not a new CLI default or arbitrary
profile loader. Both rescheduling and goods refusal use the same admission
protocol; the six adapter surfaces are unchanged.

```text
Engineer-owned registration + synthetic review grant
                       |
          Exact code/profile/resource checks
                       |
           Persist original request + attempt
                       |
              Discover verified identity
                       |
            Reserve route -> seal binding
                       |
           Atomic journal admission + debt
                       |
               Execute existing workflow
                       |
          Capture state -> observe admission
```

The route and binding seal must exist before case debt is imported. Direct
engine entry cannot skip the prepared request. Existing cases or orphaned
admission debt cannot be treated as fresh requests. A failed/uncertain operation
retains its state; it is not automatically replayed.

## Integration boundaries

Use `RuntimeFactory.create_registered(..., composition=..., execution=...)`
and `RuntimeResources.run_registered(...)`. The composition must be provisioned
by trusted application bootstrap code, never supplied by case JSON. Public
types and a synthetic fixture are in `runtime/src/proofkey/host_admission.py`
and `runtime/tests/test_host_admission.py`.

- First adoption requires a new isolated resource root and dedicated fresh
  control stores. A registration marker binds their identities.
- A marked root cannot be opened through the old unregistered factory.
- Reopen requires the original existing stores. Missing files, pending claims,
  changed configuration or uncertain cleanup fail closed; no repair/reseed.
- Registered recovery/reply/stop remain unavailable. Old unmarked registrations
  retain their existing path; no cases are migrated.
- Review grants are explicitly **synthetic rehearsal** grants. No actual-human
  approval, live service, payment, arbitrary code loading or activation occurs.

## Verification

The corrected new module passes **31 tests**. Three additional independently
written public-boundary checks pass: seal before real admission, refusal to
recreate a missing route DB, and rejection of orphan debt without new effects.
Independent review accepted the corrected feature scope after two real cleanup
defects were reproduced and fixed: uncertain descriptor retry, and cleanup via
replaceable public fields.

The final corrected full run executed **1,619 tests in 367.650 seconds**, with
**1 failure and 16 errors**. Its exact failed selectors match the earlier
1,617-test run and all reproduce on the immutable pre-feature commit `7205195`
(17 selected baseline checks, not a full baseline run). There were no newly
observed failing selectors; the whole suite is still **not green**.

The existing failures are fourteen adaptation-factory pin mismatches, two API
module import errors from missing `starlette`, and one missing-evidence
authorization expectation. None was hidden, relabeled as passing, or fixed by
weakening a check. Source is committed locally as `738e002`; no push or release
was performed. The independently reviewed scope is the fixed synthetic
registered-admission feature, not overall production or hackathon readiness.

## Next work, without weakening the gates

1. Requalify the adaptation factory against a new explicitly reviewed code
   inventory. Its old static pins mismatch five unchanged implementation files;
   do not simply replace hashes and call the old evidence current.
2. Resolve the existing test/contract mismatch for an unavailable evidence ID.
   Current intake denies missing evidence; the older test expects authorization.
3. Prepare and verify an isolated API test environment: the current bundled
   interpreter lacks the optional `starlette` dependency. No install was made.
4. Then exercise a genuinely changed process/readback contract, preserved-route
   recovery and the timed adaptation drill. This feature does not complete them.

The exact implementation contract is
[`registered-host-admission.md`](../../openspec/changes/proofkey-v21-harness-contracts/registered-host-admission.md);
the execution plan is
`2026-10-09-registered-host-admission.md` (historical worklog retained in Git history).
Original test streams, baseline archive, independent probes and review snapshots
are retained locally under `.superpowers/sdd/2026-10-08-proofkey-runtime/`.
