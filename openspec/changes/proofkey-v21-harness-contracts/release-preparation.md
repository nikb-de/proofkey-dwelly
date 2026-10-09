# Clean-source preparation refinement

9 October 2026. Internal implementation of approved Task15; no new authority, publication, legal certification or freshly user-reviewed feature. Parentplan and task-15-release-design.md guide this boundary. Pure15A source preparation/static verification is independent of the active10B consumer change; actual15B reproduction waits for whole-candidate, packaging, rights and dependency freeze.

## Pure15A boundary

Exactly new runtime/src/proofkey/release.py and runtime/tests/test_release_manifest.py. Preserve shared SourceReleaseReceipt/CommandReceipt/ReproductionReceipt and all existing product/source/data/package bytes. README/LICENSE/NOTICE/RIGHTS/.gitignore, real source manifest/context, artifact lock/installer notices, fresh install/demo/video are separately assigned15B; no caller or test fixture asserts those real gates achieved. Unit tests use task-owned synthetic files and documentary rights, not private recordings or actual source custody.

prepare_release(source_root, rights_inventory, output_root, *, context=None) -> SourceReleaseReceipt requires an immutable exact trusted SourceReleaseContextV1; missing context denies. verify_release_static(receipt, *, release_root, context) -> StaticReleaseVerificationV1 returns separately labeled static readback. verify_release(receipt, *, release_root, context, reproduction_plan) -> ReproductionReceipt is explicitly unavailable until actual15B implementation; no empty-command success or static-as-reproduction.

Context is trusted host configuration, never canonical/body activation. It binds exact source-root identity, finite intended relative paths/expected hashes, rights digest/evidence, candidate recipe/hash, dependency/notice/lock pins and semantic groups, count/size limits, narrow exact synthetic-origin scan exceptions, offline/replay/unsupported modes and observed creation clock. Supplied rights inventory must match the entire approved digest and entries; booleans/changed pins cannot authorize a file. Programmatic synthetic test contexts are not actual rights approval or signatures.

## Canonical identity and exclusion

rights_hash=sha256(canonical_bytes(approved_rights_inventory)). dependency_hash=sha256(canonical_bytes(DependencyReleaseV1)), covering exact pyproject/lock/dependency-inventory/notice/installer-artifact pins and declared verification mode. candidate_hash=fingerprint({kind:SourceReleaseCandidateV1,file_hashes:sorted_intended_mapping,rights_hash,dependency_hash,groups:exact_semantic_group_inventory}) equals independently pinned context expected candidate. release_hash=fingerprint({kind:SourceReleaseReceiptV1,candidate_hash,file_hashes,rights_hash,dependency_hash,created_at}), excluding itself. Generated manifest/receipt are outside copied inventory; no self-hash recursion or equivalence to differently scoped assessment hashes.

Copy only finite exact normalized runtime-relative allowlist entries with unique rights/hash/origin/license/notice joins. Missing/orphan/stale/private/restricted/provider/org/raw-archive/credential/unknown classifications fail even with include/public_rights true. Always exclude attachments/organizer/customer/rawprovider/privateeval/outputs/work/git/cache/venv/databases. Owned provider adapter code is distinct from provider content. Apache applies only to actually owned new code; third-party declarations/notices stay separate and no legal clearance is inferred from a hash/public URL.

Paths require relative POSIX/no aliases/dotdot/absolute/drive/UNC/NUL/backslash/casefold-Unicode collisions. No-follow pinned ancestry/regular-file identity/containment and count/individual/aggregate bytes are checked before/cross-copy/readback. Reject symlink/nonregular/hardlink aliases; generic failures never echo matched secret/private bytes. Bounded intended-source credential/private scans are exclusion guards, not proof of perfect detection. Exact pinned synthetic field exceptions only, never blanket tests/synthetic exemption. Dependency version/notice/artifact joins must agree; no guessed licenses or implicit downloads.

## New output and static verification

Validate first, then claim an absent output directory under trusted pinned parent exclusively with no-follow/no-overwrite/nonblocking lock. Source/output disjoint and neither broad workspace/user root. Copy exact expected bytes with pre/post source identity+hash, exclusive new files, flush/fsync and actual output hash readback. Recheck ancestry/source; observed change invalidates preparation instead of updating pins.

Fixed RELEASE-MANIFEST.json/SOURCE-RECEIPT.json publish only after all intended files succeed and agree with context/recipe/mode. Failures retain task-owned partial output and safe failure marker when possible, no valid receipt/subset certification. Marker failure states explicit durability limitation; no cleanup/retry-overwrite. Existing sources are untouched.

Static verification reads explicit trusted release root/context, exact manifest/receipt/allowlist actual bytes and no unexpected files. Reject missing/stale/extra/symlink/collision/partial/failed marker/wrong root/recipe/hash/notice. Closed static receipt labels static_source_readback, times/observed hashes and outcome; no install/test/effect/native/custody/reproduction qualification.

## Required tests and later gates

15A TDD: synthetic private-like denial, missing/orphan/stale rights, forbiddenarchive/org/provider/secret bytes and precise origin exception, unsafe/colliding/no-follow/root substitution/nonregular/hardlink, missingnotice/artifact pin, mutation acrosscopy, outputhash substitution, preexistingroot/partialfailure/durability limitation, modes and static verification versus unavailable actual reproduction. No test reads a real private file, alters current runtime/hash pins or fabricates provider receipts. One focused named coherent receipt and different nonauthor spec+quality review required.

15B selects source-editable clean reproduction, not wheel qualification. Frozen exact artifact hashes/notices and no-index fresh venv, stripped credentials/user-site/PYTHONPATH, actual required command exits/times/nonempty coverage/full packaged tests/new positiveCLI/API/library demo/readback are prerequisites. Python floor versus actually tested interpreter/platform remains explicit. Failure/timeout commands retained without invented normal exit. Actual sixty-second captured/rendered/native-reviewed video and social drafts stay private/unsent. No publication/submission/live/campaign/accounts/security changes are inferred.
