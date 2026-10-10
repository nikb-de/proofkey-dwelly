# Task14B2 — pure candidate-evidence audit foundation

This is a binding additive refinement of Task14 and preparation for Task16. A host-declared required driver roster is joined to safely bounded immutable capture receipts and independently regraded. This does not execute the runtime, discover files, authenticate source origin, calibrate labels or qualify the whole candidate.

## Exact ownership and composition

Only NEW `runtime/src/proofkey/assessment/audit.py` and NEW `runtime/tests/test_audit.py` may be implemented. Preserve all existing assessment/shared/runtime/provider/catalog/factory/schema/test/fixture files. Root owns specification, plan, ledger and local commits. Original author fixes findings; a different nonauthor separately reviews Spec then Quality.

Use current DriverManifest/RunnerReceipt/canonical_bytes/strict_loads/require_source and public assess_driver, and exact shared ImplementationAudit/RequirementReadiness. No runtime/driver/source/provider/model callback, ArtifactReader, filesystem traversal/open, environment discovery, shell, serializer, pickle, source updater, rights grant or caller-selectable readiness dimension. This pure API receives already captured in-memory data; raw captures remain with the host. Hashes and exact types are integrity checks, not origin authentication.

## Root refinements of the accepted preparation

AuditPositionV1 includes six detached required-roster identity fields (driver_id,variant,case_id,independent_group,obligation,required_predicate_ids). These allow the result constructor to recompute group/pass inventories and check predicate membership without storing raw manifest/expectation bytes or trusting an uncheckable passed_variants tuple. They carry declared identity, not a full variant registry or provenance. All original proposed fixture behavior remains unchanged.

Exact aware audited_at is detached to a datetime with timezone.utc singleton during input construction and boundary revalidation; mutable tzinfo may not alias into the result. It is a host label, never measured run timing. Scalar receipt integers must fit signed64 bits at safe-shape preflight; narrower semantic ordinal/repetition/process_exit errors are retained as invalid observations. Optional elapsed uses exact int/float (not bool), finite values; negative is safe-shaped but semantic-invalid. UTF8 checks concern Python string fields; raw byte payloads are never decoded merely for shape validation.

Path validation applies the declared request source map and required path roster. Receipt PRE/POST snapshots remain bounded canonical evidence bytes under existing RunnerReceipt validation; they are never followed as paths. An eligible exact-byte match necessarily shares the validated request path map. No source map proves actual filesystem safety.

Required expectation grammar matches assess_driver: exact version/expectation_version/predicates keys; version driver-expectation-v1; joined version/hash; nonempty1..64 list of exact id/event_tag/field_path/operation/expected objects; unique safe predicate IDs; nonempty bounded exact event_tag; field_path list0..16 of bounded nonempty str or exact int0..4095; operation equals or count_equals; count_equals requires empty path and exact expected int0..2**63-1. Canonical JSON validation bounds expected values. Validate this syntax without invoking the grader, so no grading occurs until all request/supplied shapes and occurrence budgets have passed.

Input constructors/function raise only AuditInputError with the closed codes below for expected invalid input. Output constructor violations use ValueError with fixed safe reason invalid_audit_projection. Do not emit raw values, exception text, event/error bytes or paths. Revalidate every exact nested projection when consumed by CandidateEvidenceAuditV1; validate cross-references, represented groups and passed variants from the six declared identity fields. Validated expected predicate order is carried in each position, not inferred from scores. Its provenance is still host-declared.

## Exact input grammar and global limits

All new dataclasses use `@dataclass(frozen=True, slots=True)`. All containers below must be exact `tuple`, bytes exact `bytes`, strings exact `str`, integers exact `int` (bool is not int), time an exact aware `datetime`. No duck typing, subclasses, generators, lists, mappings or automatic conversion at API boundaries. Request fields are revalidated when entering the audit even when a frozen object was previously constructed. Frozen prevents ordinary mutation; `object.__setattr__` bypass is explicitly covered by boundary revalidation, not treated as impossible.

```python
@dataclass(frozen=True, slots=True)
class RequiredDriverPositionV1:
    ordinal: int                         # 0..255
    repetition: int                      # 0..15
    manifest_bytes: bytes                # <=1_048_576, DriverManifest.from_bytes
    expectation_bytes: bytes             # <=1_048_576, closed canonical expectation
    required_predicate_ids: tuple[str, ...]  # 1..64, unique, exact predicate order

@dataclass(frozen=True, slots=True)
class CandidateAuditRequestV1:
    source_manifest_bytes: bytes         # <=1_048_576, require_source
    required_source_paths: tuple[str, ...]  # 1..4096, unique and sorted
    positions: tuple[RequiredDriverPositionV1, ...]  # 1..256
    audited_at: datetime                 # host-supplied aware label, not run timing
```

Request IDs destined for the public projection (driver, variant, case, group, predicate, obligation) use the additional safe identifier grammar `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`. This is an audit projection restriction, not a change to existing DriverManifest. Hashes use existing exact lowercase SHA256 validation. Required ordinal/repetition keys are unique; `(driver_id,variant,repetition)` is unique too, so changing ordinal alone cannot count one declared attempt twice. Required manifest candidate hash equals the digest of request.source_manifest_bytes. Independent expectation bytes must exactly join manifest expectation hash/version and required predicate IDs; malformed required configuration is a global request error.

Path grammar: relative POSIX strings,1..1024 characters, nonempty components using ASCII letters/digits/underscore/dot/hyphen, no `.`/`..` component, leading/trailing slash, backslash, NUL, absolute/drive/UNC form or case-insensitive collision. Apply to both required_source_paths and source-map keys. This is string validation only, not proof of symlink/actual filesystem safety. Unsafe/ambiguous paths reject globally. Exact safe keys missing from either side, extra safe source keys, or `src/proofkey/schema.sql` missing from the declared list/map are **scope incompleteness**, not malformed input. Fixture-only input may be scope-complete as a declaration but remains fixture-only and unqualified.

Global limits, all before semantic grading: at most256 supplied records; each raw byte field <=1MiB; raw event/barrier tuples <=64 items; each existing RunnerReceipt <=8MiB under its existing raw-byte accounting; combined request+supplied input budget <=32MiB. The 32MiB accounting sums every byte field occurrence and UTF8 string field occurrence, including repeated references to the same bytes/object, all required manifests/expectations/source bytes/path/ID strings and all supplied receipt fields. Scalars/tuple slots are additionally bounded by the counts above. Do not deduplicate by Python object identity to reduce the budget. Check lengths before copying or parsing. Oversize means explicit global rejection, never truncation or a partial “success” audit.

For supplied records, exact type `RunnerReceipt` is necessary but not sufficient. Read only its declared fields using direct dataclass slots, never `repr`, property discovery or arbitrary iteration. Safe-shape pass requires immutable primitive field types, bounded byte/string/tuple counts, safe UTF8 strings and finite numeric types. It does **not** require valid enum values, hash equality, ordinal range, manifest syntax or semantic consistency yet. Thus `status="invented"`, an out-of-range exact integer ordinal, a mismatched claimed hash, canonical-but-wrong source and semantically contradictory completed/error fields are bounded invalid evidence, not unsafe Python. A mutable list, arbitrary object, invalid UTF8, boolean in numeric slots, NaN/infinity or resource overflow rejects globally. No receipt object is passed to `__post_init__`/grading until every supplied record passes the whole-input safe-shape/budget preflight.

## Closed result grammar

Use only the following fields; no dynamic mappings or new readiness booleans. Names below are normative for the literal tests.

```python
PositionStatus = Literal["captured", "missing", "invalid"]
CaptureStatus = Literal["completed", "failed", "invalid_output", "no_output", "not_started"]
AssessmentStatus = Literal["passed", "failed", "insufficient", "ungraded"]
SourceObservation = Literal["none", "not_checked", "missing", "matched", "mismatched"]
SuppliedStatus = Literal["matched", "duplicate", "unexpected", "invalid"]

@dataclass(frozen=True, slots=True)
class PredicateAuditV1:
    predicate_id: str
    status: Literal["passed", "failed", "insufficient"]
    event_ordinals: tuple[int, ...]       # sorted unique, 0..63, <=64

@dataclass(frozen=True, slots=True)
class AuditPositionV1:
    ordinal: int
    repetition: int
    manifest_hash: str                   # digest of REQUIRED manifest bytes
    driver_id: str
    variant: str
    case_id: str
    independent_group: str
    obligation: str                     # R01..R15
    required_predicate_ids: tuple[str, ...] # declared expected ID order,1..64
    supplied_indexes: tuple[int, ...]     # sorted unique indexes into supplied
    status: PositionStatus
    capture_status: CaptureStatus | None
    assessment_status: AssessmentStatus | None
    source_observation: SourceObservation
    reasons: tuple[str, ...]             # exact safe codes below, no duplicates
    predicates: tuple[PredicateAuditV1, ...]  # <=64, expected predicate order

@dataclass(frozen=True, slots=True)
class SuppliedAuditV1:
    index: int                          # 0..supplied_count-1
    required_index: int | None           # index into required positions, not ordinal
    ordinal: int | None                  # valid 0..255, else None
    repetition: int | None               # valid 0..15, else None
    manifest_hash: str | None            # COMPUTED from raw bytes if available
    status: SuppliedStatus
    capture_status: CaptureStatus | None # only after semantic receipt validation
    source_observation: SourceObservation
    reasons: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class CandidateEvidenceAuditV1:
    source_manifest_hash: str
    source_kind: Literal["filesystem", "fixture-only"]
    source_scope_status: Literal["matched", "incomplete"]
    positions: tuple[AuditPositionV1, ...]
    supplied: tuple[SuppliedAuditV1, ...]
    required_count: int
    supplied_count: int
    joined_count: int
    missing_count: int
    invalid_required_count: int
    invalid_supplied_count: int
    position_counts: tuple[tuple[str, int], ...]   # exact3 order below
    capture_counts: tuple[tuple[str, int], ...]    # exact6 order below
    assessment_counts: tuple[tuple[str, int], ...] # exact5 order below
    supplied_counts: tuple[tuple[str, int], ...]   # exact4 order below
    independent_groups: tuple[str, ...]           # sorted unique valid joined groups
    passed_variants: tuple[tuple[str, str, str], ...] # driver,variant,obligation
    scope_status: Literal["unqualified"]
    limitations: tuple[str, ...]             # exact fixed order below
    implementation: ImplementationAudit
```

Every output class checks its enums, safe IDs, hashes, exact tuples/nested exact types and primitive bounds. No collection aliases are allowed. Bytes/strings/tuples are immutable; tuples contain only validated immutable scalar tuples or exact validated frozen projection objects. `ImplementationAudit` must be an exact validated detached instance rebuilt from its dumped content at the boundary, retaining WireModel's deep snapshot protection. Do not store a caller-provided `ImplementationAudit`, `DriverAssessment` or mutable mapping. Predicate projection copies only validated expected IDs, status and integer event indexes; **no raw event/error/output/expectation values** are published.

`CandidateEvidenceAuditV1.__post_init__` recomputes all count tables/scalars from its tuples and rejects disagreement; verifies sorted/unique indexes and ordering, exact prescribed status-table labels, required/supplied index cross-references, predicates allowed by their validated expected roster, unique passed_variants in required order, and mandatory missing requirement statuses. The implementation must construct from validated internal values; a typed output alone does not attest external origin. Ordinary attempts to assign attributes or mutate nested shared-wire lists/dicts fail. Repeat boundary checks defeat explicit frozen bypass when an object is consumed again.

## Exact inventory and status recipes

First create one supplied record for **every** input tuple index, in original order. Associate a required index by safely valid `(ordinal,repetition)` only; semantic failure never silently moves a receipt to a different slot. Do not invoke a grader while building this preflight inventory.

After semantic validation, classify supplied entries:

- More than one supplied item with the same declared required key: all those supplied items are `duplicate`, and the required position is `invalid`; retain all indexes. If one is also semantically invalid, preserve `invalid_receipt_semantics` in its reasons. Do not choose a “best” duplicate.
- No matching declared key: semantically valid entries are `unexpected`; semantic invalid entries are `invalid`. No extra required position is invented.
- Exactly one entry for a key but failed semantic validation or nonidentical required manifest bytes: supplied and required are `invalid`.
- Exactly one semantically valid entry with identical required manifest bytes: supplied `matched`, required `captured`. This is an identity join, independent of completion/source observation/grading.
- No supplied item for a required key: required `missing` with empty supplied_indexes. Invalid/out-of-range evidence never fills another required slot.

`joined_count = count(required.status == captured)`, including legitimate noncompleted captures with no source observation. `missing_count = count(required.status == missing)`; `invalid_required_count = count(required.status == invalid)`. Their sum equals required_count. `invalid_supplied_count` counts supplied status in `{invalid,duplicate,unexpected}` and is not the same measure as invalid_required_count. `required_count=len(positions)` and `supplied_count=len(supplied)`; no filtered denominator.

Exact3 `position_counts` order: `(("captured",n),("missing",n),("invalid",n))`, sums to required_count. Exact6 `capture_counts` order: `(("completed",n),("failed",n),("invalid_output",n),("no_output",n),("not_started",n),("none",n))`, **over required positions**, sums to required_count. Capture labels are populated only for required.status captured; invalid/missing rows use None and contribute to the `none` bucket, never to their untrusted claimed status. Exact5 assessment_counts uses `passed,failed,insufficient,ungraded,none` in that order over required positions. Exact4 supplied_counts uses `matched,duplicate,unexpected,invalid` in that order over all supplied records. Do not combine these different denominators.

For captured noncompleted records, assessment_status is `ungraded`, predicates empty and reason includes `capture_not_completed`; reuse existing `assess_driver` or its explicit documented noncompleted result only after preflight/semantic joins. For captured completed records eligible under exact source bytes, recompute existing `assess_driver` against the pinned expectation. Project its real predicate statuses/indexes; passed/failed/insufficient remain distinct. Invalid/missing required positions have assessment_status None and no predicates. A completed capture with failed predicates stays captured/completed/failed. `completed` never implies `passed`.

`independent_groups` is the sorted set of groups from semantically valid identity-joined captures, including noncompleted ones; it reports represented groups, not successful groups, statistical independence certification or sample size. `passed_variants` includes a unique required-order triple only when the position is captured, completed, source_observation matched, source_scope_status matched and assessment_status passed. No tuple is promoted to complete Rxx coverage.

## Source scope versus observed source

`source_scope_status` concerns only the declared source-map/path inventory. Missing/extra safe keys or absent schema make it incomplete; do not reject construction and do not discard captures. `source_kind` is descriptive, not origin authentication.

Per-record source_observation has these exact meanings:

| State | Meaning |
| --- | --- |
| none | No required capture exists; required missing position only |
| not_checked | Invalid/duplicate/unexpected required join, or semantic receipt invalid; no eligible source conclusion |
| missing | Identity-joined valid record, no wrong observed bytes, but one or both PRE/POST snapshots absent |
| matched | Identity-joined valid record and BOTH snapshots exactly equal request source_manifest_bytes |
| mismatched | Identity-joined valid noncompleted record with ANY present snapshot bytes unequal to request bytes, even if the other snapshot is absent |

Wrong present bytes take precedence over absence. A valid `not_started` record with PRE=None/POST=None is captured/ungraded/missing, counts toward joined_count and gets `source_observation_missing`; it cannot enter passed_variants. A valid failed record with matching PRE and POST=None is captured/ungraded/missing. A valid failed/not_started record with wrong PRE and POST=None is captured/ungraded/mismatched, gets `source_snapshot_mismatch`, and remains in its original status bucket. That mismatch is evidence of failed source observation, not an invented full-record structural defect.

Only a completed eligible record requires exact PRE and POST request bytes. Existing RunnerReceipt already imposes its own completed source/hash constraints. A completion that fails them is semantic-invalid. If a semantically valid completed record could still disagree with the required exact source bytes, mark the required/supplied join invalid with `source_snapshot_mismatch`; never grade it as eligible or call it observed success. None of these observations proves current filesystem state, custody or whole closure.

## Closed errors, reasons and limits

`AuditInputError(ValueError)` contains **one** of these exact global error codes, no attached arbitrary value/message: `invalid_request_type`, `invalid_request_shape`, `invalid_request_identity`, `unsafe_supplied_shape`, `input_limit_exceeded`. Catch only expected validation failures; sanitize at this boundary. Do not call `str(error)`, `repr(value)`, log raw bytes, dynamically format invalid fields or follow a supplied path. KeyboardInterrupt/SystemExit are not converted into audit success.

Projection reason enum, emitted in this canonical order when applicable:

```text
missing_capture
duplicate_capture
unexpected_capture
invalid_receipt_semantics
manifest_mismatch
source_scope_incomplete
source_observation_missing
source_snapshot_mismatch
capture_not_completed
invalid_capture_or_expectation
predicate_failed
predicate_insufficient
```

`candidate_mismatch` from the earlier note is subsumed by `manifest_mismatch` when the supplied manifest is not byte-identical to the required one; request manifest candidate disagreement is global invalid_request_identity. `fixture_only_source` belongs to limitations, not per-position failure reasons. Each reason tuple is a unique subsequence of the canonical list.

Fixed limitations, exact order, always present:

```text
source_origin_unattested
current_source_not_read
required_scope_host_declared
full_required_variant_matrix_unregistered
provisional_reference_not_gold
actual_vs_replay_unjoined
protected_custody_missing
whole_candidate_unqualified
```

Append `fixture_only_source` iff source_kind is fixture-only, and `source_scope_incomplete` iff source_scope_status is incomplete. No other caller-supplied limitation text.

ImplementationAudit requirements are emitted once each in this order: `source_scope_join`, `driver_inventory_join`, `declared_driver_results`, then R01 through R15, then `whole_candidate_closure`, `actual_content_roles`, `development_activation`, `calibrated_labels`, `protected_isolation`, `timed_drills`, `clean_reproduction`, `source_rights`, `independent_whole_branch_review`, `official_eligibility`. The final25 IDs (15 Rxx + ten broader dimensions) are always missing, with empty evidence_refs and `reason="outside_foundation_evidence_scope"`.

`source_scope_join`: satisfied/matched_declared_source_scope or missing/incomplete_declared_source_scope. `driver_inventory_join`: invalid/invalid_driver_join when any invalid required/supplied entries exist; otherwise missing/missing_driver_capture when missing_count>0; otherwise satisfied/matched_declared_driver_inventory. `declared_driver_results`: invalid/invalid_driver_join when any invalid required/supplied entry exists; otherwise missing/declared_results_incomplete unless every required row is completed, source matched, source_scope matched and predicate passed; otherwise satisfied/declared_variants_passed. The word declared is essential: it is not full Rxx readiness. Evidence refs for these three use only deterministic safe `required-{index}`/`supplied-{index}` labels; no external/private reference text.

`implementation.candidate_hash=source_manifest_hash`; audited_at is the validated request time. missing_evidence/invalid_evidence are deterministic unique requirement IDs in the requirement order matching missing/invalid statuses. No free caller requirements or green completion flag. The whole-candidate IDs remain missing even when all three narrow joins are satisfied.

## Implementation and verification scope

Implement complete pure preflight, independent joins, grading and immutable projections; the two literal fixtures and six literal refinement tests in the plan are mandatory, with additional focused guard cases. Include genuine failed/insufficient predicate controls, empty required/supplied inventories, unexpected/duplicate semantic-invalid observations, source missing/mismatch, expectation/predicate joins, unsafe paths/types/numerics, frozen bypass/revalidation, projection count/cross-reference tampering and 32MiB occurrence overflow. Actual-looking model/approval/protection flags cannot upgrade fixed missing dimensions.

Record all original command/return/output/error evidence; distinguish missing-module RED and fixture mistakes from genuine behavior failures. Run a tiny fixture-only end-to-end audit and then one development discovery of the NEW module, freeze its literal current IDs/current source/data/platform/interpreter inputs and request one separate root finite final GO. Do not rerun old engine/driver/API cohorts as this task's evidence. Root conducts proportional NEW checks, exact-two local integration and separate different-nonauthor Spec/Quality review.

The declared source scope and narrow result joins may become satisfied; wholeTask14/16, complete R01–R15 variant matrix, actual content/model roles, development activation, gold calibration, protected custody, rights/reproduction, timed drills, final whole-branch review, official eligibility and whole-change archival remain unfinished.
