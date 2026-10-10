# Canonical interchange format

The eight canonical JSON schemas copied into `schemas/` describe backend-facing records. Their repository source of truth is `contracts/v1/schemas/`; this package includes the [decision-input](schemas/decision-input.schema.json), [local-case](schemas/local-case.schema.json), [decision-label](schemas/decision-label.schema.json) and [episode](schemas/episode.schema.json) schemas. Do not add fields to closed schemas. The model input is `decision-input`, containing an exact `dwelly-local-case-v1` snapshot; it is not the legacy `logistics-decision-v0.1` payload.

## Record relationships

| File | Required relationship and purpose |
|---|---|
| `examples/inputs/<input_id>.json` | `schema_version: proofkey-decision-input-v1`, `visibility: model_visible`; `source` exactly matches the enclosed snapshot's case, revision and hash. |
| `examples/labels/<label_id>.json` | `proofkey-decision-label-v1`, evaluator-only; points to input ID and identical source; includes expected disposition, rationale, review and provenance. |
| `examples/episodes/<episode_id>.json` | `proofkey-episode-v1`, evaluator-only; lists case, input IDs, label IDs and transition IDs. Referenced transitions must exist when used. |
| `examples/criteria/<input_id>.json` | `proofkey-eval-criteria-v1`, evaluator-only; richer evaluation expectations, not an API request. |
| `manifest.jsonl` | One `proofkey-dataset-row-v1` row per input; inventory and family split, never model context. |

For a concrete included example, inspect [input i-71ac-1](examples/inputs/i-71ac-1.json). Its `input_id`, `source` and `snapshot` illustrate the binding. See its companion [label l-71ac-1](examples/labels/l-71ac-1.json) and [episode ep-71ac](examples/episodes/ep-71ac.json). These are unreviewed synthetic development seeds, not evidence of permission for any real source.

## Immutable source identity

A source is the exact tuple `(case_id, revision, snapshot_hash)`. Revision zero has no events. Each append increments revision and preserves previous snapshots; hash the canonical UTF-8 JSON with sorted keys, compact separators, no NaN, excluding `snapshot_hash` itself. Exact-byte manifest hashes are different: hash the entire saved file bytes, including formatting.

The package validator requires the complete input snapshot chain from revision 0 through the latest captured revision N for each case; an isolated revision N is insufficient. Ancestor rows may carry an exclusion reason such as `context_only`: retain them for history validation, but exclude them from scored decisions and training. No scorer is supplied, so downstream consumers must enforce these exclusions. The nine seed snapshots represent three cases, not nine independent cases.

Different branches with different histories need distinct case IDs. Multiple decisions may reuse a source only when its snapshot is identical. Do not map legacy `case_revision` directly: earlier drafts reused one case/revision for different event sets. Preserve original provenance in an appropriate record, and rebuild append history explicitly.

The manifest's `as_of` is the curator-checked observation cutoff. Canonical events do not have a separate `observed_at`; event timestamps alone cannot establish when an email, extraction or receipt became available. Curators must exclude later-known information and record uncertainty. Do not extend the closed event schema to solve this.

## Evaluator sidecars

Criteria fields: `schema_version`, `visibility`, `input_id`, `source`, `acceptable_dispositions[]`, `required_details[]`, `required_evidence_ids[]`, `forbidden_claims[]`, `forbidden_actions[]`, `missing_information[]`, `authority_notes`, `ambiguities[]`, `human_control`, `risk_level`, `follow_up_trigger`.

`human_control` is `proposal_only`, `requires_approval` or `no_action`; `risk_level` is `low`, `medium` or `high`; `follow_up_trigger` is a string or null. Required evidence IDs must refer to evidence visible in the input. Describe missing evidence under `missing_information`, not as a required visible evidence reference. These criteria express review expectations; no semantic grader is implemented here.

Manifest fields: `schema_version`, `input_id`, `family_id`, `episode_id`, `split`, `origin`, `as_of`, `files`, `sha256`, `annotation_status`, `tags[]`, `exclusions[]`. `files` and `sha256` each contain `input`, `label`, `criteria`, `episode`. Paths are relative to this package root. `split` is `train`, `development` or `test`; `origin` is `synthetic` or `redacted_real`. Annotation status is `assistant_authored_draft`, `human_authored_draft`, `human_reviewed` or `rejected`. Family membership controls splitting, including related sources and counterfactuals.

Canonical label review remains authoritative for whether an individual annotation is reviewed: `reviewed` needs a real reviewer ID and review timestamp. Keep the manifest status consistent. Preserve provenance without claiming that collection time proves the source was available at the cutoff. Detailed source permission/redaction evidence should remain in the team's controlled source register; never embed private source material in the model input merely to document permission.

`decision-run`, `transition`, `asset` and `analysis` schemas are provided for their canonical uses. Their presence does not imply executable replay, real media extraction, business authority or model service support. No conversion may silently discard unsupported information or promote raw messages to trusted authorization.
