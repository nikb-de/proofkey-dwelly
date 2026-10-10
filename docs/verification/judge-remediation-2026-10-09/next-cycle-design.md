# Completed remediation cycle: J22, J32 and the five-judge panel

Date: 9 October 2026. Status: **approved J22/J32 implementation, verification and leaf archival complete; separate five-provider reassessment and source adjudication complete**.

## Accepted purpose and current baseline

The user asked to continue implementation, then run the same multi-judge assessment and return to fixing verified findings. Product priorities remain easy integration, rapid adaptation and reliable case resolution. This cycle must preserve existing authority, original-effect identity, deadlines and synthetic/actual labels.

Pre-cycle baseline: `ecf36acdb3ebad7a33ef2257adb583356934c0ff`, with documentation/archive `0628652ec3b373d58a3538a3b4a2a68cb933ba61` and a passed 1,685-test run. Those historical receipts remain unchanged.

Verified current runtime: `40138e1433b9f7ba782385124727dd2ea842f97f`. The complete 1,693-test run passed in 888.064 test seconds with zero errors/failures/skips and 246 stable runtime files; the separate current-source factory qualifier passed 37/37 tests with eight artifact hashes independently checked. Eight J-items are closed and 24 remain open; [this leaf is archived](../../../openspec/changes/archive/2026-10-09-registry-commitments-and-short-parent-evidence/tasks.md), with strict OpenSpec validation 6/6 passed. See [verification](../2026-10-09-registry-commitments.md). This is not a production or event-readiness claim.

## J22: public immutable commitment inventory

At design time, the observed private consumers were `host_admission.py` and `admission_routes.py`, not `host.py`. They now use the approved public projection. `ReleaseRegistryV1` owns sorted canonical `(release_id, wire_bytes)` records, bounded to 32 releases and 32 MiB total.

Approved and implemented interface:

```python
def commitments(self) -> tuple[tuple[str, str], ...]:
    """Detached sorted (release_id, artifact_hash) commitments."""
```

Return exact built-in tuples and strings, not release objects, resource paths, authority handles or full declaration bytes. Validate the actual current records, including exact types, nonempty bytes and count/byte bounds before parsing, sorted unique IDs, canonical valid release and matching outer/embedded ID. Do not return a separate stale cache that hides replaced `_releases`.

Consumers retain their existing constraints:

- Composition requires exactly one matching release/hash and resolves it through the public method before the existing executable/resource/review checks.
- The admission owner captures a detached commitment and compares current commitments on entry. Substitution still denies before claims or business effects.
- Route-store construction enumerates public commitments, resolves each release, checks identity/hash agreement, and retains existing resource/factory consistency, stored canonical bytes and registry-hash format.

Alternatives: exposing raw `(id, wire_bytes)` would leak complete declarations and preserve representation coupling; leaving private access does not satisfy J22. On-demand validation is the clearest initial boundary, but bounded parse cost must be checked because owner validation is on an execution path. A cache that loses mutation detection is not an acceptable optimization.

Implemented surface: `registered_releases.py`, `host_admission.py`, `admission_routes.py`; focused tests in `test_release_route_foundation.py` and `test_host_admission.py`. No new host command, registration authority, storage schema, activation or migration.

Verification includes exact output types/order/detachment; malformed, duplicated, relabeled and oversized entries; valid-envelope substitution after owner creation; two-release composition rejection; unchanged route registry hashes and stored wire bytes; and absence of production `._releases` consumers outside its owning module.

## J32: positive short-parent evidence

This was a missing test, not an observed production defect. `_observation_context` already caps the phase at the minimum of five seconds, remaining UTC and remaining monotonic time. The added real-component tests now cover the positive short-parent case alongside ample remaining time, expiration/backwards clocks and cumulative final-phase exhaustion.

Reuse the existing real fixture, engine and `paced_clock(after_engine)`. Keep the captured parent at tick 100 with its original 120-second window:

| Case at real engine return | Tick | UTC offset | UTC remaining | Monotonic remaining | Required phase |
| --- | ---: | ---: | ---: | ---: | ---: |
| UTC limits | 216 | +2 | 2 s | 4 s | 2 s |
| Monotonic limits | 218 | -2 | 4 s | 2 s | 2 s |

Forwarding spies must call the real capture, route observation and claim-write methods. Assert one shared phase, exact duration/cutoffs, preserved parent and durable original execution fields, observed route/claim and exactly one effect. Also expire the two-second phase immediately before the real final claim write: retain the effect and imported account, with route observed and claim sealed, and return timeout. Explicit phase assertions remain necessary: an outer parent guard could otherwise mask an incorrectly generous phase budget.

No production timing change was made for J32. A subsequently reproduced defect would require separate recording and reassessment before changing behavior. J28 remains closed.

## Reassessment protocol

Use a new immutable run directory and fresh conversations for Claude, Grok, AGY, Muse and a separate Codex session. Do not mutate or reuse the original panel's output directory. Rebuild the source packet from the newly tested commit; the historical builder hardcodes an older commit, source spans and test totals, so merely rerunning it is invalid.

Preserve all eight rubric IDs, names, criteria and scoring anchors. Preserve R1–R5 weights 35/20/20/15/10; report the unweighted eight-rubric score separately. Keep old verdicts, scores and suggested answers out of the fresh judge input. Record exact input bytes, source spans, code/test snapshot, transport attempts, identities, native result IDs where available, latency, usage and failures. Remove credential/PII patterns and native hidden-reasoning fields from retained output.

| Seat | Existing route found locally | Identity constraint |
| --- | --- | --- |
| Claude | `/Users/nbk/.local/bin/claude` | Explicit model selector; the old runner silently depended on configured default. Original native identity was `claude-fable-5-1`. |
| AGY | `/Users/nbk/.local/bin/agy` | Preserve requested `gemini-3.1-pro-high`; initialization selector alone is not backend attestation. |
| Muse | `/Users/nbk/.local/bin/muse-bin-1.4.2-R4684.1` | Disable auto-update; original native facet was `muse-spark-1.3`. |
| Grok | `/Users/nbk/.local/bin/grok` | Earlier CLI failed before inference at Docker-socket sandbox resolution. Web Expert was the completed seat; exact backend remained unknown. No silent replacement or weakened sandbox. |
| Codex | `/opt/homebrew/bin/codex` | Separate fresh session, explicit `gpt-6.1-sol`/high, read-only and no tools; selector is not independent backend attestation. |

Presence of an executable is not current authentication, quota or provider participation. At the 9 October 2026 approximately 20:27 UTC dispatch checkpoint, fresh r2 requests had been submitted to Claude, AGY, Muse and a separate Codex session, and no outcome had yet been adjudicated. The Grok CLI failed at its sandbox/Docker boundary; the approved Grok Web Expert request was submitted separately. That failed CLI attempt remains in the completed record below.

## Fix-loop boundaries and stopping conditions

First run one five-seat panel on the frozen verified candidate. Classify each finding as a reproducible defect, supported capability gap, external/human gate, missing packet evidence or disputed/unsupported claim. Map it to existing J-IDs before adding work. Reproduce alleged defects before editing; do not optimize the numerical score by omitting failures or softening safeguards.

At most one follow-up full panel is approved after in-scope confirmed fixes, with no automatic wrapper retries or provider substitutions. Further panels require a recorded reason and allowance rather than an unbounded spend loop. Native subscriptions may not expose actual monetary cost; report unknown cost as unknown, not zero. Preserve failed transports and incomplete seats.

Transport clarification from local help and prior native metadata: the wrapper makes one bounded invocation per seat and does not retry/resume it. This does not assert that a provider client disables its own internal transport retries. Muse exposes a model-step limit but no documented attempt-limit option in local help; its prior native output declared a retry ceiling. Record observed attempts and native ceilings separately, without interpreting a ceiling as actual requests or unknown subscription cost as zero.

This is a package comparison, not causal attribution to one of J22/J32. Five related model opinions do not supply statistical confidence or an independent operational oracle. There is no protected holdout in this review packet; do not claim generalization from reusing it. Human custody, rights, actual release signoff, native integrations and event acceptance remain external gates.

Stop on a guardrail regression, provider access requiring new authority, an unapproved interface change, or no remaining reproducible in-scope fix. Do not mark the broader program complete while its remaining criteria are unmet.

## Historical read-only preparation

Independent source-backed design review found no concrete defect in the proposed J22 boundary, J32 arithmetic or panel protocol. At that stage, J22 parsing cost remained an implementation verification obligation. This preparation review was not user design approval or implementation evidence. Subsequent implementation, the zero-byte preflight correction, scoped reviews and verification are recorded separately below.

All five named local executables were found, and their local help was inspected without a prompt or model request. The current Claude help supports an explicit `--model`; Grok supports the existing read-only invocation shape; AGY supports the existing bounded print mode; Muse exposes the required no-shell/no-write controls; Codex supports explicit model, read-only sandbox and ignored user configuration. These checks establish command-surface availability, not authentication, quota, successful inference or served-model identity.

No product source, test, dependency, provider account or original judge artifact was changed during the read-only preparation. The subsequent user confirmation authorizes the bounded J22/J32 implementation and panel protocol above; it does not authorize new runtime authority or integrations.

## Verified implementation and completed r2 assessment

Commits `0e71716`, `0122660` and `40138e1` implement the public inventory, correct positive-size preflight ordering and add real short-parent tests respectively. Independent task and whole-package reviews found no remaining Critical/Important/Minor issue within this bounded scope. Observed projection timings are local noisy samples, not an operational SLO; maximum-envelope performance remains unmeasured. J32 introduced no production timing change.

The fresh r2 packet is 327,124 bytes with SHA-256 `16544b8aba044168403910de948da22f04e1ef97493d2ce2a9b158da7def717c`, frozen from the verified candidate. It excludes old verdicts/scores and preserves all eight rubric definitions. The [completed assessment](../../../outputs/proofkey_runtime_panel_2026-10-09_r2/reports/ASSESSMENT.md) records all five returned answers, with four strict schema-eligible score sets; AGY's object-keyed response is preserved but excluded from aggregation, without repair or retry. The weighted R1–R5 result and unweighted eight-rubric result remain separate; excluded scores are unavailable, not zero.

All 30 findings were source-adjudicated. No further J22/J32 defect was reproduced, and no second panel was warranted. Wider integration, adaptation, evaluation and human/provider gaps remain open; the completed bounded cycle does not close the umbrella changes.
