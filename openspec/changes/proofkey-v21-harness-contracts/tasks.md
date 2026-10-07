Status: revised work breakdown for written review on 8 October 2026, Europe/London, incorporating the user's 18 answers. No runtime task is complete. Development uses the user and coding agents; actual event people/registrations remain unconfirmed. Revised estimate: 54–86 additive person-hours, not agent wall-clock time or an event promise. This file is input to, not a replacement for, the detailed Superpowers implementation plan.

## 1. Design approval and execution planning — user + agents, 2–4 hours

- [x] 1.1 Confirm that more connections means the six proposed adapter surfaces, with no new autonomous workflow or live service access. Evidence: user's clarification reply, “Yes—six integration adapters”, 7 October 2026.
- [ ] 1.2 Review and approve the revised written design, decision ledger, required modalities/model roles, native assumptions and offline/live boundaries.
- [ ] 1.3 Assign local file owners, agent tasks, human review and go/no-go checkpoints; keep actual event people/registrations separate from development resources.
- [ ] 1.4 Create the detailed Superpowers implementation plan in docs/superpowers/plans; review it and select subagent-driven or inline execution.
- [ ] 1.5 Freeze initial approved ProcessSpec/schema examples, public contracts, shared file ownership and operation-by-failure fixture allocation before parallel consumers.
- [ ] 1.6 Resolve the ten source-specific questions in follow-up-questions.md; preserve earlier decisions unless explicitly changed.
- [ ] 1.7 Revise source-linked consent, stop/cancel, pre-effect/terminal recovery and ownership requirements; add the return companion, allocate regression tests and revisit effort before the next written-design review. Reminders/internal-case effects/native diagram sync remain pending scope choices.

## 2. Shared contracts and six-adapter bundle — adapter owner, 8–12 hours

- [ ] 2.1 Create the clean runtime/ source-release subtree, package/tests/public fixtures and Apache-2.0 owned-code boundary; preserve all archived evidence.
- [ ] 2.2 Implement Pydantic request, authority, binding, capability, initial versioned ProcessSpec, intent, dispatch and verification schemas with failing tests first; pin dependencies and retain notices.
- [ ] 2.3 Implement flat/nested normalization with no-text parity, malformed-input rejection and explicit evidence-processing status; cite source-inspired offline shapes without claiming native integrations.
- [ ] 2.4 Implement read-only case/principal adapter and scope-specific authority/consent/risk observations.
- [ ] 2.5 Implement delivery stage/refusal adapter with independent goods and completed-service registration/readback contracts.
- [ ] 2.6 Implement slot discovery and one authoritative conditional rescheduling adapter.
- [ ] 2.7 Implement return-policy/create/readback adapter with item, quantity, destination and initiation-versus-receipt checks.
- [ ] 2.8 Implement bounded customer clarification/status adapter, authenticated recipient binding and distinct message receipt stages.
- [ ] 2.9 Implement operator enqueue/readback/resume adapter with packet identity, owner receipt and authenticated version-bound decision fixtures.
- [ ] 2.10 Verify unsupported/unknown capabilities, conditional-write races, shared account quota/concurrency/backpressure and bounded rate-limit handling; adapters cannot bypass the action gateway.

## 3. Durable runtime, both workflows and recovery — core owner, 12–18 hours including section 4

- [ ] 3.1 Implement request generations, stable logical action IDs, separate fingerprints, duplicate binding and explicit supersession.
- [ ] 3.2 Implement the SQLite intent journal with immutable prepared/dispatch state committed before transport and failure-closed dispatch.
- [ ] 3.3 Implement per-case ownership, persisted time/call/effect budgets and bounded reconciliation without resetting counters on restart.
- [ ] 3.4 Enforce the approved baseline ProcessSpec graph/prerequisites and fresh route/permission/risk/consent/version gates before every business, message and operator effect, before enabling model-backed effect planning.
- [ ] 3.5 Implement operation-specific verifier and the two-condition safe-resend rule; preserve original keys and never retry unresolved unsafe effects.
- [ ] 3.6 Run journal-failure, pre-send, post-send/pre-verification and post-verification restart tests, recording actual outputs and limitations.

## 4. Workflow controls — included in core estimate, no additional effort allocation

- [ ] 4.1 Implement positive structured/no-text rescheduling and autonomous selection inside authenticated window/timezone/constraints, native lifecycle/capacity and conditional-write gates.
- [ ] 4.2 Implement whole-order goods refusal/return with authoritative complete inventory/quantity binding, independent effects and partial-item operator routing.
- [ ] 4.3 Verify refusal-success/return-pending, rejected, unknown and wrong-object/item/quantity/destination outcomes without replaying refusal.
- [ ] 4.4 Implement service-refusal registration and evidence-rich operator delivery; record scoped human refund/coverage/internal-case dispositions without autonomous financial adjudication or execution.
- [ ] 4.5 Verify unsupported request classes cannot trigger a business write and separately authorized clarification/handoff remain possible.
- [ ] 4.6 Verify forged, replayed, expired, wrong-case, stale and scope-expanding operator decisions cannot resume effects.

## 5. Common entry points and clarification — interface owner, 6–10 hours

- [ ] 5.1 Implement one shared library/CLI/loopback FastAPI pipeline and canonical response/export contract; localhost is not principal authentication.
- [ ] 5.2 Implement scripted and interactive authenticated clarification, persisted waiting owner/deadline/binding/budget and clearly simulated fixture replies.
- [ ] 5.3 Verify interface parity, scope/authentication checks, partial/pending waiting states and no hidden effect shortcuts.

## 6. Required evidence processing and model roles — evidence/model owner, 12–20 hours

- [ ] 6.1 Implement artifact catalog with MIME/hash/source/access/case binding, original references and transformation/assertion lineage.
- [ ] 6.2 Implement declared TXT/JSON, supplied transcript, JPEG/PNG, unencrypted PDF and WAV/MP3 intake with malformed/encrypted/unsupported states and scoped redaction.
- [ ] 6.3 Implement provider-neutral extraction/planning/transcription protocols, explicit replay/unavailable modes, versioned prompts and processor/usage receipts.
- [ ] 6.4 Preflight exact Anthropic/ElevenLabs API routes, observed model identity, privacy rights and a capped authorized campaign; do not infer API access from subscriptions or execute unapproved paid work.
- [ ] 6.5 Process actual text/transcript/image/PDF/audio test content through declared processors; record mode/provenance, failures and media-specific adversarial cases. Stub/replay tests cannot satisfy actual-processing readiness.
- [ ] 6.6 Implement model-backed bounded step proposals constrained by approved ProcessSpec and deterministic gates; verify prompt injection cannot change authority/process/policy.

## 7. Reviewed adaptation factory — adaptation owner + human reviewer, 6–10 hours

- [ ] 7.1 Implement process diff/release tooling over the initial ProcessSpec established in 2.2 and enforced in 3.4; preserve schema/policy separation, approval/wait and completion meanings.
- [ ] 7.2 Prepare engineer/coding-agent adapter/process proposals with source basis, changed tests, diff, migration impact and reproducible candidate release.
- [ ] 7.3 Require human approval before activation; verify runtime content cannot rewrite mappings/process/policy or expand permission.
- [ ] 7.4 Reconcile pending old-version intents or use explicit compatible migration; preserve original keys/fingerprints/postconditions/budgets.
- [ ] 7.5 Execute the 600-second new-profile drill changing semantics AND process; retain schema/no-text regressions and full clock/human review evidence.

## 8. Output, acceptance, labels and release preparation — review/eval owner, 8–12 hours

- [ ] 8.1 Implement system-generated ANSWERS/<case>/ANSWER.md and REASONING.md with auditable facts, per-effect/evidence states and all failures retained; verify path/collision safety.
- [ ] 8.2 Implement incremental batch saves, shared deadline and measured export reserve; rehearse declared workloads with complete denominators.
- [ ] 8.3 Freeze/run the remaining 600-second positive, crash-recovery and unsafe-rejection exercises; report full elapsed times, unfinished cases and independent interface/modality readiness.
- [ ] 8.4 Prepare provisional LLM labels under explicit campaign boundaries, disagreements and evidence basis; prepare an unsent team revalidation pack, not a claimed gold set.
- [ ] 8.5 Version label-set/rubric/lineage hashes, invalidate affected cached scores and regrade changed references; qualify repeatability/sensitivity, group variants and record validation contamination. Deterministic effect checks remain independent.
- [ ] 8.6 Enforce oracle isolation with denied-access/canary probes and assign independent human custody before protected holdout; otherwise explicitly report rehearsal.
- [ ] 8.7 Independently review/reproduce the frozen candidate, verify actual requirements and report missing runtime/native/provider evidence as unfinished.
- [ ] 8.8 Prepare a clean source/license/rights package, reproducible instructions, sixty-second video and unsent LinkedIn/X drafts without publication/submission.

## 9. Native/event enablement and archival — separate evidence/authorization gates

- [ ] 9.1 Complete native discovery for every enabled effect and media source; unsupported guarantees remain unknown/disabled.
- [ ] 9.2 Confirm prebuilt eligibility, real human registrations, rights, provider access/budget and freeze clarification; preserve conservative source/result hashes.
- [ ] 9.3 Obtain separate authorization before live logistics connections, paid campaigns, team/organizer messages, publication or submission.
- [ ] 9.4 Archive only when implemented requirements pass, updating openspec/specs; never archive this planning revision as completed runtime.
