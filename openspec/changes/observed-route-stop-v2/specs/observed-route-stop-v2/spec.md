## ADDED Requirements

### Requirement: Closed versioned factory and complete named first-party inventory
The system SHALL add only `fixed-synthetic-observed-stop-v2` as an explicit trusted factory selection, preserving default `fixed-synthetic-v1`. V2 SHALL require the exact reviewed sorted first-party Python/schema inventory, matching embedded bytes, factory pins and dependency declaration. Existing per-release limits and `completeness=unestablished` SHALL remain. Factory selection MUST NOT come from business content. Old markers, roots, grants, hashes and schemas MUST NOT be rewritten.

#### Scenario: Mixed or incomplete executable declaration
- **WHEN** factory keys, pins, embedded bytes or dependency entries disagree, or a key is unsupported
- **THEN** preparation/composition is rejected before runtime admission or new preparation child allocation.

#### Scenario: Default v1 remains isolated
- **WHEN** callers omit the new trusted keyword or select v1
- **THEN** the old inventory and run-only control contract apply without silently selecting v2.

### Requirement: Stop requires current-owner observed authority
Only a fully successful observed admission in the current live v2 owner and original exact SyntheticReplayClock SHALL mint an in-memory nonserializable stop receipt. It SHALL bind original request, generation, claim, route, transferred attempt, immutable wait context and original execution identity. Prepared, sealed, uncertain, interrupted, reopened, closed, cross-thread or reentrant owners MUST NOT qualify. A stop-first host request MUST be denied before runtime creation.

#### Scenario: Observed route with incomplete final claim
- **WHEN** a final observation/claim write or final time check fails
- **THEN** no stop receipt is minted even if another persisted record says observed.

#### Scenario: Restart or direct bypass
- **WHEN** a new owner opens retained state or code directly invokes engine stop without the owner capability
- **THEN** stop is denied without new admission or business effects.

### Requirement: Current authentication and original-only identity continuity
Each stop SHALL use fresh transport-resolved AuthContext, the original principal and proof identity for this v2 contract, and existing current-source stop authorization. The owner SHALL validate exact claim/route identity and current bounded journal projection against its observed receipt: original request/binding, request versions, transferred attempt selected by attempt_id with explicit identity/hash fields, imported account, immutable intents and waits. It MUST NOT create admission/route/attempt/account/generation, reset debt or infer authority from stored hashes alone.

#### Scenario: Wrong identity or revoked current authorization
- **WHEN** case/generation/caller/proof differs or current source authorization was revoked
- **THEN** stop is denied and no unauthorized business effect occurs
- **AND** legitimate current-source read accounting remains recorded.

### Requirement: One bounded control window preserves original time and fences
Stop SHALL use one fresh control context clipped to five seconds, exact current clock identity and nondecreasing UTC/monotonic observations. Original admission windows, business deadlines, attempt cutoffs, wait expiry/context and intent cutoffs MUST remain unchanged or no later where the existing checkpoint contract allows tightening. Existing consumed debt MUST NOT decrease, nor may frozen allowances change. Already observed stop flags and stopped waits MUST NOT revert. No post-business-deadline stop guarantee is introduced.

#### Scenario: Preflight exhausts the shared window
- **WHEN** aggregate preflight consumes the control deadline
- **THEN** no new source or engine stop begins under a renewed phase window.

#### Scenario: Stop commits before interruption
- **WHEN** the existing atomic stop/wait fence commits and later return/postflight fails
- **THEN** the durable stop remains, the active capability is cleared, and later permitted inspection/control cannot re-enable work or extend a wait.

### Requirement: Stop-only tagged gateway scope and bounded snapshot decoding
The owner capability SHALL authorize only the existing engine stop entry, with exact execution object and snapshot. Run/recover/reply/bind paths MUST reject that token. Canonical outer retained snapshots and bounded noncanonical inner journal model strings SHALL be decoded separately; duplicate/nonfinite/oversized/malformed inner input MUST fail closed without relaxing existing claim parsing. Existing snapshot limits remain mandatory.

#### Scenario: Token operation substitution
- **WHEN** a stop capability is presented to run, recover, reply or new admission
- **THEN** it is rejected before source or state entry.

#### Scenario: Genuine inner journal JSON
- **WHEN** valid journal models use their ordinary noncanonical field ordering
- **THEN** bounded exact-model validation succeeds without rewriting the original bytes
- **AND** mismatched attempt identities or altered immutable wait fields are rejected.

### Requirement: Bounded stop acceptance evidence
Completion SHALL require real same-owner run-to-stop execution with the exact clock class, authenticated current source read, unchanged business effect count, preserved originals/claim/route/deadlines, nondecreasing debt, real pending-wait fencing and successful owner closure. Negative controls, focused regression, full frozen regression and independent review SHALL be retained. Documentation MUST keep recover/reply/restart, installed-wheel qualification, human release approval and live systems outside this source/trusted-library claim.

#### Scenario: Successful local acceptance
- **WHEN** a fresh v2 trusted-library fixture is run and stopped within one owner
- **THEN** evidence records the stopped original generation, preserved identities and cutoffs, charged read, no repeated business effect and actual owner closure.
