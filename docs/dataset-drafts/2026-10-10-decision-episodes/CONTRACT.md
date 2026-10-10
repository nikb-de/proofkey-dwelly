# Proposed dataset contract v0.1

This is a draft authoring interface, not an implemented runtime API. Schema files are authoritative for structural checks; the semantic requirements below are also mandatory.

## Separation and identity

```text
examples/
  manifest.jsonl                 # evaluator inventory; do not send to the agent
  agent_inputs/<decision_id>.json # only this snapshot is visible for one decision
  private_labels/<decision_id>.json
  simulator/<episode_id>.json    # future events and transitions; evaluator only
```

Family = common source scenario, including every counterfactual. Episode = one branch. Decision = one time-bounded observation. `case_revision` binds business state, not just file order. `as_of` is the observation cutoff.

The agent must not receive paths, labels, future events, expected tool outcomes, branch names or tags from the manifest. Example IDs are opaque (d001…); labels must not leak through filenames. In a future evaluation runner, give the agent only the resolved input bytes and necessary tools, not repository access.

## Common input

Required: `schema_version`, `decision_id`, `episode_id`, `case_id`, `case_revision`, `stage`, `as_of`, `payload`.

Payload always includes objective, participants, events, artifacts, a policy snapshot and capabilities. Optional stage-specific fields are defined in the input schema.

- Events have both `occurred_at` and `observed_at`. Visibility follows observed time, not the time mentioned in a message.
- Source statements are assertions. An email signature or self-described role does not prove authority.
- Participant binding and verified approvals in these fixtures come from a **synthetic trusted harness**, not inference from message wording.
- A missing policy is `null`: do not infer real-company policy. Ask the appropriate internal owner before a policy-dependent commitment.
- Synthetic policies are explicitly marked `synthetic: true`.
- Artifact availability and read status are separate. A filename is not content. An extraction is not proof that the model has seen the original image/audio.
- The supplied readable media example is a simulated extraction. No actual photo or audio asset is included.
- No confidence score can substitute for a missing prerequisite or capability.

## Stages and boundaries

| Stage | Specific input | Required output/decision | Owner |
|---|---|---|---|
| intake | New event, available files, participant bindings | Sourced observations, missing/unreadable references, route to planning | Model extracts; harness preserves provenance |
| decide | Visible state, objective, policy, capabilities | Per-action sufficiency; minimal next action; correct party and human control | Model proposes |
| authorize | Proposed operation + current revisions + verified approval records | Allow/block with failed prerequisites; no business effect | Deterministic policy gate |
| execute | Allowed gate receipt bound to exact operation/revisions | Simulated adapter command with stable operation and idempotency IDs | Deterministic executor |
| verify | Adapter response + authoritative readback, if available | accepted/pending/applied/failed/unknown; next check or justified completion | Deterministic status check; model may explain |
| resume | New observed event, prior checkpoint, pending operation | Re-plan or reconcile; invalidate stale assumptions/approvals; no duplicate effect | Harness resumes; model proposes where needed |

For execute, an allowed receipt is valid only for its exact action, parameters, policy version and case revision. For verify, an accepted request is not an applied effect. A matching authoritative readback is needed for completion. An idempotency key alone does not prove the provider supports deduplication.

## Operation envelope

An operation contains `operation_id`, `kind`, `parameters`, `case_revision`, `policy_version`, `idempotency_key`. Parameters must include the material commitment (for example amount/currency or slot/address reference). Approval includes an exact copy of approved parameters, operation identity, expiry, policy and case revisions.

In this draft, approvals and gate receipts carry a boolean fixture verification marker. That is **not a production security design**. A real harness must validate origin, permissions, expiry, revocation and binding from a trusted system, not accept a model-generated boolean.

Capability `mode: propose_only` permits no external effect. `mode: simulated_only` addresses only the offline fixture. Actual send/execute capabilities are intentionally absent.

## Reference label

A label includes:

- `sufficiency[]`: sufficient / insufficient / unknown **for each named action**, with missing prerequisites.
- `acceptable_next_actions[]`: a set of acceptable actions, not one exact wording.
- `required_observations`, evidence and policy references.
- `human_involvement`: information participants, required approval role, oversight.
- `expected_gate` and `expected_operation_status` where applicable.
- `must_not`: testable prohibited behaviour; not an invitation to execute it.
- `next_wait_condition`, short rationale and ambiguities.

Immediate action control modes:

- `autonomous_draft`: model can prepare an unsent next-step proposal.
- `human_in_the_loop`: proposed downstream effect awaits a permitted approver.
- `human_on_the_loop`: supplied policy allows simulated execution with monitoring.
- `deterministic_gate`: the expected decision is a rules check, not model discretion.

Approval requirements refer to the downstream effect, even when the immediate step is merely drafting a request. Do not score a draft approval request as an unauthorised payment.

All included labels have `annotation_status: assistant_authored_draft`, `human_reviewed: false`. They are not gold labels.

## Simulator

A simulator transition contains a current decision ID, a trigger description, future events injected at that boundary, and the next decision ID or a terminal state. These describe **expected environment behaviour**, not hidden facts the agent may cite early.

Replay is planned, not implemented here. A future runner must match an emitted acceptable action before advancing, persist checkpoints, and expose only newly observable information. Free-form `on` descriptions in this draft require a separately defined transition matcher.

## Manifest and splits

Each row includes relative paths, SHA-256 of exact input/label bytes, origin, family, split, tags, provenance, ambiguity and exclusions. Hashes detect changed bytes; they do not authenticate facts.

All seed examples are development data. Before tuning, assign independent families to train/development/test. Related source cases, translations and counterfactuals stay together. A test case used to select a change becomes development data. Private hold-out labels must be stored outside agent-visible repositories for a real evaluation.

## Compatibility with existing code

Do not inject these fields into `dwelly-snapshot-v1` or `dwelly-model-proposal-v1`. Existing validation is strict and the stages here extend beyond the current unsent-proposal task.

Potential future mapping for the decide stage only: evidence request → request_evidence; option selection → request_customer_choice; operator approval proposal → operator_review. Gate, execution, resume and readback need separate interfaces. No adapter is supplied or claimed.
