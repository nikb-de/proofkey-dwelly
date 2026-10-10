# Training versus evaluation: how to use the same contract

These are **different uses**, not two names for the same dataset. The seed package is development material only. It does not contain a reserved final test set.

## Demonstrations / training

For a reviewed training decision:

- Input: only the decision's agent_input JSON.
- Target: a concise structured response containing per-action sufficiency, the selected acceptable next action, evidence references and a short decision summary.
- Keep evaluator-only fields (must_not, alternative acceptable actions, ambiguity, future transitions) out of the model input.
- If using few-shot examples, include only training-family demonstrations in the prompt, never development/test labels.
- If fine-tuning is later chosen, construct provider-specific messages from this reviewed subset. No weights are trained by creating these files.

Example target shape for a **model-owned decide stage**:

```json
{
  "decision_id": "d002",
  "sufficiency": [
    {"for_action": "draft_evidence_request", "status": "sufficient", "missing": []},
    {"for_action": "propose_refund", "status": "insufficient", "missing": ["readable_damage_evidence"]}
  ],
  "next_action": {
    "kind": "request_evidence",
    "recipient_id": "customer-d",
    "requested_items": ["readable_photo_of_damage"],
    "execution_mode": "propose_only"
  },
  "evidence_refs": ["e101"],
  "decision_summary": "The customer mentions a photo, but no artifact is available. Request a readable copy; do not approve or claim a refund."
}
```

This is a proposed training export shape, **not** the existing service's output schema. Build and validate the exporter separately before using it.

## Evaluation

The system under test receives exactly the input snapshot. The evaluator alone receives private labels, the rubric, simulator and manifest. Generate a fresh candidate, then score it against acceptable behaviour.

Capture candidate bytes, parse status, system/prompt/model versions, timestamp, input hash, latency and cost where known. Never replace a malformed or failed candidate with a reference answer.

Evaluate deterministic stages with exact contract/gate assertions. Evaluate model stages with structured assertions plus semantic review. A fluent model explanation must not override a failing authority gate.

## A comparison worth running later

1. Freeze a baseline on reviewed development families.
2. Measure missing-information decisions, needless questions, needless escalation, missed approval, fabricated evidence and false completion separately.
3. Change one thing: a prompt, a profile mapping or an evidence-normalisation step.
4. Compare paired outputs on the same development families.
5. Confirm on untouched independent families. Report abstentions and uncertain labels.

An aggregate score alone can hide a dangerous failure. Report critical failure counts beside the eight rubric scores.

## Suggested generator work division

- Source analyst: fill a curator-intervention worksheet per source case; do not generate the answer from future resolution.
- Scenario author: create coherent branches using the supplied policy.
- Label reviewer: inspect evidence, recipient, authority and alternate acceptable actions.
- Data QA: run structural checks and review leakage.
- Workflow owner: adjudicate business policy and promote labels after human review.

These are roles for the team, not agents launched by this package. Do not claim agreement of several generators is independent human validation.
