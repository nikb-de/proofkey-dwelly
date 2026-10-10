# Task13B3 — registered release and original-route foundation

Internal implementation refinement of the already approved Task13 reviewed-adaptation/preserved-contract requirements. The engineer-first priorities and OptionA direction remain unchanged. Exactly NEW `runtime/src/proofkey/registered_releases.py`, NEW `runtime/src/proofkey/admission_routes.py`, NEW `runtime/tests/test_release_route_foundation.py`. Root owns formal/plan/commits; original author corrects findings; separate DIFFERENT NONAUTHOR Spec/Quality gates. Existing host/factory/bootstrap/engine/gateway/journal/source/schema/profile/helper/tests and historical recipe pins remain unchanged. This formal is not itself implementation GO.

This stage supplies a pure closed synthetic-declaration registry and an independent durable local route bookkeeping store. There is NO active-release pointer, executable loading/factory invocation, authority grant, actual review approval, mutation/migration, source/journal opening by the route store or atomic host selection. Full implementation-inventory matching is relative to explicit trusted registration; declaration completeness remains unestablished. No current factory is relabeled as qualified. Missing real approval/native/closure/rights facts remain unavailable.

Two observed seams stay open: current CanonicalRequest/AdmissionAttempt lacks generation before admission accounting can begin; the accepted full host-declared provisional binding is bookkeeping, not actual pre-debt integration. Complete journal images carry integrity, not authenticated resource-file origin. A future host-intake stage must reserve a claim/attempt before debt and seal/verify its real binding under an exclusive resource-set owner. This stage MUST NOT be wired as a current runtime admission/permission gate.

## Exact input types and APIs

Use public Identifier/Hash/RequestBinding/CanonicalRequest/AuthContext/ExecutionContext/RetainedStateClock/RetainedStateSnapshotV1 semantics, never private snapshot encoders/journal connections. All new value objects and registry storage are exact frozen/slotted detached bytes/tuples, reject subclasses, aliases and serializer objects. Public Pydantic profile/binding/request projections are freshly reconstructed, not retained mutable aliases. `ReleaseBlobV1.sha256` is computed from its bytes. `RegisteredReleaseV1(wire_bytes: bytes)`, `RouteRecordV1(wire_bytes: bytes)` and `ObservationV1(wire_bytes: bytes)` are exact frozen projections that independently validate their complete wire grammar. Registry.resolve returns a RegisteredReleaseV1; its `.artifact_hash/.wire_bytes/.profile/.resource/.factory` and route `.binding/.request/.state/.artifact_hash/.observation` are public detached projections. Observation exposes `.observation_hash` and its exact times; no payload/disclosure permission is returned.

```python
@dataclass(frozen=True, slots=True)
class ReleaseBlobV1:
    name: str                 # strict relative logical name, not an openable path
    data: bytes               # bounded exact bytes; hash computed as H(data)

@dataclass(frozen=True, slots=True)
class ResourceSetV1:
    resource_id: str
    root_path: str             # absolute trusted configuration reference only
    root_device: int
    root_inode: int
    journal_name: str          # one safe basename
    source_name: str           # distinct safe basename
    account_ids: tuple[str, ...]  # sorted complete non-null capability accounts
    admission_account_scope: str # exactly "claimed_case_id"

@dataclass(frozen=True, slots=True)
class KnownFactoryV1:
    factory_id: str
    implementation_pins: tuple[tuple[str, str], ...]
    dependency_hash: str
    mode: str                 # exactly "offline_synthetic" in this stage

@dataclass(frozen=True, slots=True)
class ReleaseArtifactV1:
    release_id: str
    factory_id: str
    resource_id: str
    profile_json: bytes       # full validated EnvironmentProfile, exact raw bytes
    policy_json: bytes        # full policy, H(canonical policy) == profile.policy_hash
    source_json: bytes        # complete source basis, explicitly synthetic
    proposal_json: bytes      # full proposal/diff; data, not a proposal-check result
    tests_json: bytes
    regression_json: bytes    # complete declared receipt, not proof of execution
    migration_json: bytes     # exactly preserve strategy; no mutation machinery
    agent_json: bytes         # synthetic/unestablished permitted, never actual claim
    dependency_json: bytes    # full finite implementation/dependency inventory
    implementations: tuple[ReleaseBlobV1, ...]

@dataclass(frozen=True, slots=True)
class RouteLimitsV1:
    max_routes: int = 4096
    max_row_bytes: int = 262144
    max_release_bytes: int = 33554432
    max_routes_bytes: int = 8388608
    max_operation_seconds: float = 5.0
    max_sqlite_steps: int = 1000000

ReleaseRegistryV1(*, artifacts: tuple[ReleaseArtifactV1, ...],
                  factories: tuple[KnownFactoryV1, ...],
                  resources: tuple[ResourceSetV1, ...])
ReleaseRegistryV1.resolve(release_id: str) -> RegisteredReleaseV1
ReleaseRegistryV1.resource(resource_id: str) -> ResourceSetV1

AdmissionRouteStoreV1(parent: Path, *, database_name: str,
                     registry: ReleaseRegistryV1, clock: RetainedStateClock,
                     execution: ExecutionContext,
                     limits: RouteLimitsV1 = RouteLimitsV1())
store.reserve(reservation_id: str, *, attempt_id: str, release_id: str,
              binding: RequestBinding, request: CanonicalRequest,
              auth_claim: AuthContext, execution: ExecutionContext) -> RouteRecordV1
store.observe_admitted(reservation_id: str, *,
              snapshot: RetainedStateSnapshotV1,
              execution: ExecutionContext) -> RouteRecordV1
store.get(reservation_id: str, *, execution: ExecutionContext) -> RouteRecordV1 | None
store.for_generation(resource_id: str, case_id: str, generation: str, *,
              execution: ExecutionContext) -> RouteRecordV1 | None
store.close() -> None
```


Failure class `RouteFoundationFailure(ValueError)` exposes only code and message `invalid|conflict|unregistered|scope|limit|timeout|storage|observation_mismatch`, suppressing raw payload/path/SQL/exception. Registry construction/resolve failures use the same finite contract. Unknown lookup ID in an otherwise registered resource returns None; unknown release/resource denies unregistered. Registry max32 releases/factories/resources,512 blobs/release,1MiB decoded blob,8MiB full envelope,32MiB aggregate. Store release/full-route row bounds below count exact JSON/base64/projection overhead. Close always releases lock/descriptor even on a normalized cleanup failure and is creator-owned/idempotent after expiry.

## Canonical grammar and hashes

`C(x)` is UTF-8 `json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)`. `H(b)` is lowercase SHA-256 of bytes. `J(x)=H(C(x))`. Object keys below are exact; missing/extra/duplicate keys reject. Arrays preserve order unless explicitly sorted. Strict int excludes bool. Identifiers/hashes use existing public Identifier/Hash rules; names use POSIX relative components with no empty, dot, dot-dot, leading slash, backslash, colon or NUL component. Normalize names using NFC and casefold solely to reject aliases; never silently rename. Strings retain original content. Canonical bytes must equal `C(parsed)`.

A `blob` has exactly `{"base64":B,"sha256":H(decoded B)}`. B is canonical padded RFC4648 base64; strict decode then encode must equal B. Reject raw base64 length over its containing limit before decode. A named implementation blob has exactly `{"name":N,"base64":B,"sha256":H(decoded B)}`. Duplicate normalized names reject. Implementation contents are opaque bytes and never executed/imported. JSON declaration blobs additionally must decode to canonical objects of the exact grammar below.

Timestamp grammar is UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`, always six fractional digits, obtained from an aware datetime converted to UTC. Decode strictly and round-trip. Float fields are finite exact Python floats on construction (bool/int aliases rejected); JSON canonical round-trip determines their spelling. Numbers outside public model ranges reject.

### Declaration blob keys

These are local synthetic declarations, not attestations. No declaration accepts `actual`, `passed`, `approved`, `verified`, arbitrary status/provenance fields or executable locations.

| Blob | Exact decoded keys and values |
|---|---|
| source | `kind="route-source-declaration-v1", mode="synthetic", source_id:I, documents:[{source_id:I,text:str}]`; 1–64 unique document IDs; text is evidence data only. |
| proposal | `kind="route-proposal-declaration-v1", mode="synthetic", baseline_profile_hash:H, candidate_profile_hash:H, diff:[{path:N,before:JSON,after:JSON}]`; 0–64 unique normalized paths sorted lexically. Candidate hash equals profile semantic release hash; baseline is an unresolved reference, not an imported approval. |
| tests | `kind="route-test-declaration-v1", mode="synthetic", cases:[{case_id:I,purpose:str}]`; 0–128 unique case IDs sorted lexically. |
| regression | `kind="route-regression-declaration-v1", mode="synthetic", execution="unestablished", tests_hash:H, case_ids:[I]`; tests_hash=H(exact tests blob bytes); unique sorted IDs exactly equal declared test IDs. |
| migration | `kind="route-migration-declaration-v1", mode="synthetic", strategy="preserve", affected_contracts:[I]`; 0–128 unique sorted IDs, a declaration only. |
| agent | `kind="route-agent-declaration-v1", mode="synthetic", authorship="unestablished", agent_label:I`. |
| dependency | `kind="route-closure-declaration-v1", mode="synthetic_declaration", completeness="unestablished", entries:[{name:N,sha256:H,role:R}]`; entries nonempty, sorted by name, exact match to all implementation blobs; R is `code|data|dependency|interpreter|platform|notice`. |

Profile blob decodes to the exact public `EnvironmentProfile.model_dump(mode='json')` shape, then public `validate_profile` validates semantic hashes/processes/policy. Policy blob decodes to exactly the current policy keys `policy_id,version,evidence_mode,native_routes_enabled,live_roles,wait_expiry_seconds,internal_case_creation,automatic_reminders`; `live_roles` has exactly extraction/transcription/planning. Values must equal the literal synthetic policy already used in the previous fixture, and J(policy) must equal profile.policy_hash. No general policy extension is introduced.

The dependency list has to equal an independently constructor-registered KnownFactory's exact pins and dependency hash; matching a self-declared candidate list is insufficient. `completeness="unestablished"` deliberately refuses to certify runtime closure. Actual reviewed closure/runner/rights receipts remain outside this static foundation. No five historical factory constants are changed.

### Registered release envelope

Keep the `ReleaseArtifactV1` input fields/signature from the preparation. It is detached declaration material. Add a frozen output `RegisteredReleaseV1` with `.artifact_hash`, `.profile`, `.wire_bytes`, `.resource`, and `.factory` immutable/detached projections. `ReleaseRegistryV1.resolve` returns this output; artifact_hash now unambiguously refers to the **complete registered envelope**, not declaration material alone.

Its exact wire keys are:

```text
kind="registered-release-v1", version=1, release_id, mode="offline_synthetic",
factory={factory_id,mode="offline_synthetic",implementation_pins:[{name,sha256}],dependency_hash},
resource={resource_id,root_path,root_device,root_inode,journal_name,source_name,
          account_ids:[I],admission_account_scope="claimed_case_id"},
blobs={profile,policy,source,proposal,tests,regression,migration,agent,dependency},
implementations:[named-implementation-blob],
semantic={profile_hash,process_hash,capabilities_hash,policy_hash},
artifact_hash
```

Factory pins/implementation blobs/account IDs are unique lexical-order arrays. Resource fields retain the previous constructor type and validate exact nonnegative int device/inode. All strings naming resources/factories come from constructor registration and must match the input artifact IDs. `profile_hash=profile.release_hash`, `process_hash=J(profile.processes)`, `capabilities_hash=J(profile.capabilities)`, `policy_hash=J(policy)`. `artifact_hash=J(envelope without artifact_hash)`. Full profile contains the full processes and capabilities; semantic projections are hashes, not a second editable copy. `resource_hash=J(resource)`. `registry_hash=J({kind:"route-registry-v1",version:1,releases:[{release_id,artifact_hash}]})`, sorted by release_id; the envelope already binds factory/resource bytes. Unused or multiply defined factory/resource registrations reject.

## Route wire: exact fields and equality

```text
kind="original-admission-route-v1", version=1,
reservation_id:I, attempt_id:I, release_id:I, artifact_hash:H,
resource_id:I, resource_hash:H, account_ids:[I],
case_id:I, generation:I,
binding:{all nine public RequestBinding fields, including supersedes_generation:null|I},
request:{all eleven public CanonicalRequest fields, including narrative:null|str},
binding_hash:H, request_hash:H, business_fingerprint:H,
auth_claim:{caller_id:I,proof_digest:H}, auth_claim_hash:H, dedup_hash:H,
reservation_hash:H, state:"reserved"|"admission_observed",
reserved_at:T, observation:null|ObservationV1, record_hash:H
```

Canonical public model dumps include all default fields; no exclude_none/exclude_defaults. In particular, preserve full arguments, evidence_ids **in their original order**, narrative text including whitespace, consent mode, request revisions, and supersedes_generation including null. Identity comparison is equality of C(full dump), not business fingerprint alone. Strict revalidation of a supplied binding/request/auth object does not authenticate its claims.

Hash recipes are exact:

- `binding_hash=J(binding)`; `request_hash=J(request)`; `business_fingerprint=J({kind:request.kind,consent_mode:request.consent_mode,arguments:request.arguments})`; equals binding.fingerprint.
- `proof_digest=J({proof_reference:auth_claim_input.proof_reference})`; store no raw proof reference. `auth_claim_hash=J({caller_id,proof_digest})`. Accept only `type(auth_claim_input) is AuthContext`, then validate its full dump; reject subclasses/dicts/objects with serializers.
- `claim` has exactly `case_id,object_id,principal_id,request_id,request_revision,consent_revision` from request. `dedup_hash=J({caller_id,proof_digest,claim,business_fingerprint})`, matching public admission semantics.
- `reservation_hash=J(route without reservation_hash,state,reserved_at,observation,record_hash)`; these are the immutable original fields. `record_hash=J(route without record_hash)` binds first timestamp and observation too.

`ObservationV1` has exactly `kind="journal-admission-observation-v1", snapshot_kind="case-store-retained-state-v1",schema_version=1,schema_hash:H,content_hash:H,table_counts:[[str,int]],total_rows:int,captured_at:T,finished_at:T,elapsed_seconds:float,observation_hash:H`. The counts retain the public snapshot's exact table order. `observation_hash=J(observation without observation_hash)`. The first accepted complete image therefore binds its exact content hash **and** captured/finished time, elapsed time and envelope. Do not store the private snapshot payload in the route.

`reserved` requires observation=null; `admission_observed` requires a valid complete ObservationV1. Exact reserve retry compares all immutable original fields/reservation_hash, returns the first stored row even if now observed, and never rewrites reserved_at. Any reservation/attempt/natural-key collision with different IDs or original fields fails. A later snapshot must pass every join below; if consistent, return the first stored observed row without replacing its image/time/hash. A changed/wrong later image fails; merely having state admission_observed is not a bypass. Observation is retained historical bookkeeping, never current admission/authority proof.

## Exact public journal image join

Input must be exact `RetainedStateSnapshotV1`, with `payload` bytes <=4 MiB **before** constructor revalidation/JSON parse. Reconstruct the public class from its public fields to validate canonical whole image, complete counts/schema and permitted scalar grammar. No private `_TABLES`, `_canonical`, `_read`, encoder or connection access. Parse its already bounded payload using duplicate-key/nonfinite rejection; independently require the documented public table/column sets before indexing. The journal payload uses plain JSON `str|int|null` rows, **not** Source13's typed `['text',...]`/REAL tags (`retained_state.py:13–29,124–172`). Reject tagged substitutions.

Select exact matches without filtering away malformed alternatives:

| Public table and columns, in exact order | Required join |
|---|---|
| `requests`: case_id,generation,binding_json,versions_json,stop_requested,request_id,request_revision,consent_revision,fingerprint | Exactly one matching `(case_id,generation)`; all identity/index columns nonnull and equal route. Parse binding_json with public RequestBinding, compare C(full dump) including supersession. versions_json **nonnull for observation**; parse exact keys profile_version/process_version/policy_version. Compare to registered profile.version, profile.processes[request.kind].version and policy.version. stop_requested must be 0 or 1; preserve/allow both, never clear stop. |
| `original_requests`: case_id,generation,request_json | Exactly one same pair; parse public CanonicalRequest, compare C(full dump) including narrative, evidence list and all arguments. No replacing it with current input or a fingerprint-only comparison. |
| `admission_attempts`: attempt_id,claimed_case_id,dedup_hash,attempt_json,state | Exactly one matching attempt_id, nonnull. Outer state=`transferred`; outer case/dedup agree with route and parsed public AdmissionAttempt. Parsed exact public keys: attempt_id,claimed_case_id,claimed_object_id,claimed_principal_id,request_id,request_revision,consent_revision,claimed_caller_id,proof_digest,business_fingerprint,request_hash,dedup_hash,created_at,deadline,state. Compare every original material field to route; public timestamps must be valid with deadline>created_at; do not invent equality with reservation/snapshot times. Both state copies transferred. |

Stored JSON text need not already be canonical: strict-parse/model-validate then compare canonical full model values. The whole snapshot preserves the raw text unchanged. A missing row, duplicate match, malformed selected text or null selected identity fails `observation_mismatch`; a globally invalid image fails `invalid`. Unrelated legitimate nullable-key duplicates/multiplicity remain valid and unfiltered; observation does not demand uniqueness of every physical nullable key. Do not tighten the public snapshot schema or normalize its rows. No requirement that the current checkpoint still belongs to this generation, has a non-stopped state, unchanged debt or current permission. Public snapshot validation is bounded integrity validation, not re-running the journal's private semantic validator or establishing source custody.

## Exact store DDL and validation

Only the NEW control DB may use connection-local foreign_keys=ON/query_only changes and its initial rollback/FULL settings; reopening never converts an unexpected WAL/foreign configuration. The new DB executes these three canonical statements only when creating a previously absent exclusively owned target. The expected sqlite_master SQL is each literal below without its final semicolon, matching SQLite's stored form; compare it byte-for-byte, without general SQL normalization. No schema upgrade or overwrite of an existing empty/unknown/partially created DB.

```sql
CREATE TABLE meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL CHECK(version=1),registry_hash TEXT NOT NULL);
CREATE TABLE releases(release_id TEXT PRIMARY KEY NOT NULL,artifact_hash TEXT NOT NULL,artifact_json TEXT NOT NULL);
CREATE TABLE routes(reservation_id TEXT PRIMARY KEY NOT NULL,attempt_id TEXT NOT NULL UNIQUE,resource_id TEXT NOT NULL,case_id TEXT NOT NULL,generation TEXT NOT NULL,release_id TEXT NOT NULL REFERENCES releases(release_id),state TEXT NOT NULL CHECK(state IN ('reserved','admission_observed')),record_json TEXT NOT NULL,UNIQUE(resource_id,case_id,generation));
```

Exactly one meta row `(1,1,registry_hash)`. Exact configured release count 1–32, each canonical envelope/hash matching registry; no omitted or extra registration. Routes count 0–4096 and all selected columns nonnull; validate every route's grammar/hash, projections, registry membership, natural key/attempt/reservation uniqueness and monotone valid state shape. Zero routes is legitimate. No new nullable-key relaxation: this new schema explicitly makes all route identities NOT NULL, while old journal null multiplicity remains untouched.

Exact sqlite_master inventory (query excludes no user object): three tables plus four automatic indexes: `sqlite_autoindex_releases_1`; `sqlite_autoindex_routes_1`, `_2`, `_3`, with `tbl_name` releases/routes respectively and SQL NULL. Table names match their tbl_name and exact DDL. No explicit index, view, trigger or extra table, no sqlite_sequence (no AUTOINCREMENT). Verify `PRAGMA table_info` column cid/name/type/notnull/default/pk order, FK from routes.release_id to releases.release_id, and `PRAGMA index_list/index_info` corresponding PK/UNIQUE columns. The INTEGER meta primary key's table_info notnull flag is SQLite's actual 0 despite the required singleton row; do not invent a NOT NULL flag. Table DDL statements are a proposed future implementation contract, not SQL run in this task.

`record_json` is C(route). The FULL stored route for the 262144-byte limit is C({reservation_id,attempt_id,resource_id,case_id,generation,release_id,state,record:parsed_record_json}); indexed projections are counted again and observation/hash fields are included. A reserved row that fits but whose observation would exceed the full-row limit must remain reserved and fail limit. Aggregate routes limit is 8388608 bytes of these full-row encodings. A release limit is 8388608 bytes of C({release_id,artifact_hash,artifact:parsed_artifact_json}); sum <=33554432 bytes. Count all registry/envelope/base64 overhead, not just decoded content.

Before any DB payload fetch or giant parse, bound schema count/DDL lengths; table counts; SQL scalar types; UTF-8 byte lengths using bounded SQL projections; then stream batches of at most 32 rows, exact full-row encoded bytes, aggregate counts and complete validation. Raw record_json/ artifact_json byte bounds are necessary preliminary checks; final full-row encoding decides exact acceptance. For supplied objects, bound bytes/base64/collection sizes before deep revalidation. All loops/parsing/encoding remain under original call time/VM limits. Public snapshot may be 4 MiB even though the retained route row is smaller because only its envelope is stored. No fetchall before bounded preflight, and no “already observed” fast path skipping later-image checks.

## Ownership, paths, context and public signatures

Select database basename grammar `[A-Za-z][A-Za-z0-9_-]{0,63}\.sqlite`; lock basename is exactly `<database_name>.owner-lock` in the same pre-existing parent. Constructor opens the lock with create/no-follow, mode 0600, validates regular file/single link and takes nonblocking exclusive flock for the entire lifetime. Lock file is retained after close; never unlink/recreate it to evade another owner. DB is regular/single link/no-follow checked, with parent/file identities checked before and after open and every operation. Initial creation uses exclusive file creation; any pre-existing target must validate full known schema/data. A crash leaving a partial DB is storage failure, not permission to repair it automatically.

The constructor parent must be a scoped existing directory, never a broad workspace/user root. Canonical parent/DB/lock paths must differ from every registered root/journal/source path declaration under NFC+casefold normalized absolute path comparison; resource basenames use the same safe filename grammar. For any existing registered root/target, bounded lstat checks reject symlink/nonregular target/alias to DB or lock by `(device,inode)`; do not open/read source or journal contents. Missing resource targets are allowed declared fixture identities, not proof of availability. DB/lock may not alias each other or a resource root. No path supplied through request/blob content is considered. This remains local cooperative ownership with observed identity checks, not atomic OS custody or a multi-resource barrier.

Keep exact signatures below (only resolve output, state and clarified lookup types differ from prior preparation):

```python
ReleaseRegistryV1.resolve(release_id: str) -> RegisteredReleaseV1
ReleaseRegistryV1.resource(resource_id: str) -> ResourceSetV1
AdmissionRouteStoreV1(parent: Path, *, database_name: str,
    registry: ReleaseRegistryV1, clock: RetainedStateClock,
    execution: ExecutionContext, limits: RouteLimitsV1 = RouteLimitsV1())
store.reserve(reservation_id: str, *, attempt_id: str, release_id: str,
    binding: RequestBinding, request: CanonicalRequest, auth_claim: AuthContext,
    execution: ExecutionContext) -> RouteRecordV1
store.observe_admitted(reservation_id: str, *, snapshot: RetainedStateSnapshotV1,
    execution: ExecutionContext) -> RouteRecordV1
store.get(reservation_id: str, *, execution: ExecutionContext) -> RouteRecordV1 | None
store.for_generation(resource_id: str, case_id: str, generation: str, *,
    execution: ExecutionContext) -> RouteRecordV1 | None
store.close() -> None
```

The method name observe_admitted is retained for compatibility with proposed fixtures, but returns state admission_observed and explicitly means observation of stored admission, not permission. Constructor's <=5-second original execution covers constructor work **only**. Each method requires its own caller-supplied exact original ExecutionContext, with duration <=5 seconds, creator-thread use, non-reentrancy and unexpired/nonreversed UTC/monotonic bounds. It does not capture a context internally or extend/reuse constructor time as an implicit allowance. A later new call may have a new caller-captured context; no call recaptures midway. Constructor/call work cannot mutate case debt. `close()` takes no execution and is creator-owned/idempotent cleanup even after expiry.

RouteLimitsV1 remains exactly max_routes=4096, max_row_bytes=262144, max_release_bytes=33554432, max_routes_bytes=8388608, max_operation_seconds=5.0, max_sqlite_steps=1000000; positive strict types, only lowering allowed. The separate per-release 8 MiB ceiling and registry limits remain fixed. Preserve finite failure codes from preparation. Once a transaction committed but final time/response check fails, return failure without claiming rollback; idempotent retry/get under a fresh caller context resolves actual committed state. No response claims success after its original deadline.

## Adjustments to the two literal fixtures

Keep their public setup, temporary DBs, ordering and assertions. Both fixtures create a separate existing `control = root / 'route-control'; control.mkdir()` and pass control as the route-store parent (including reopen); declared resource root remains root. This resolves the otherwise conflicting parent/resource-root identities without reading or creating resource DBs. Replace the declaration construction with the exact grammars above: source has one synthetic text document; proposal uses baseline=candidate profile.release_hash and empty diff; tests has empty cases; regression has execution=unestablished, tests_hash=H(tests bytes), empty case_ids; migration has preserve/empty affected_contracts; agent has authorship=unestablished and agent_label; dependency has exactly the one fixture text blob entry with role=data and completeness=unestablished. The known factory dependency hash is H(exact dependency bytes). No fixture declares test success or approval. `resolve` now yields the complete RegisteredReleaseV1 envelope.

In fixture 2 expect `admitted.state == 'admission_observed'`. Save the first observation object/hash and assert same-image replay returns the identical row. Then capture the unchanged journal using another explicit `ExecutionContext(NOW+1s+5s,NOW+1s,11.0,16.0)` and a new test clock returning NOW+1s/11.0; confirm equal payload/content hash but different captured/finished times. Pass a separately original caller context for that operation; all joins still match, so the returned row must retain the **first** observation and record hash. Add a mismatching original/narrative or supersession image case via ordinary public journal fixture construction, not mutation of private DB rows, and assert observation_mismatch plus unchanged first row. The original request-hash test must retain narrative/evidence order even though business fingerprint excludes them.

Add exact full-row threshold assertions for reserved and observation-expanded rows, using the defined full stored encoding rather than record_json alone; one-over failure leaves prior row unchanged. Add reopen with existing empty/foreign/partial schema and lock/DB/resource alias cases, no overwrite; strict AuthContext subclass/dict rejection; constructor expiration followed by a new explicit valid operation context; close after expiry. These are future tests, not executions performed here.

Evidence read this turn: `schema.sql:1–40`, public snapshot shape/scalars `retained_state.py:10–54,100–172`, public admission material/model joins `admission.py:104–115,152–168,340–356`, public request/binding/auth fields `contracts.py:118–134,177–186`, and request identity `journal.py:638–643`. No private encoder is proposed for use. Existing complete snapshot supports no resource-origin authentication; no static schema/hash refinement changes that limitation.

## Evidence and completion gate

Original writer prepares two literal public behavioral fixtures and finite additional guards in the selected Superpowers plan; all required semantic/storage cases must fail genuinely before minimal code, not only missing-module errors. Preserve every raw launched command/outcome, fixture/loader error, failure/timeout and corrected history. Freeze exact3 plus actual observed import/open/source-data/private/interpreter/platform closure; root separately authorizes ONE finite final NEW cohort and only justified selected unchanged controls. Root reads original receipts, checks proportionally with NEW checks, locally commits exact3, then DIFFERENT NONAUTHOR assesses Spec and Quality separately. No broad old API/source/processing suites are repeated as a substitute for current evidence. Public rights/README/reproduction/providers/human/timed/wholeTask13/16/most-capable final review and archival remain separate unfinished gates.
