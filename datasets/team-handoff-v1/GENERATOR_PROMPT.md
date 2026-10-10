# Copy-ready generator prompt

You are preparing reviewable logistics-agent decision examples for this team's canonical ProofKey dataset. Read FORMAT.md, ANNOTATION_CHECKLIST.md and the supplied JSON schemas before authoring. Use only source material explicitly supplied and authorised for this task. Do not call external providers, message participants or operate business systems.

Deliver 10–20 independent evaluation cases and a separately identified collection of 10–20 authorised redacted real-workflow snapshots when such sources are supplied. Record overlap between these collections. If the supplied sources cannot meet the request, report the shortfall. Do not fabricate real-world provenance or treat branches as independent cases. Synthetic additions must be classified as synthetic.

For each family:

1. Identify the source, permitted use, redaction needs and relationship to other families. Keep sensitive permission records in the controlled source register, outside model inputs.
2. Select a decision cutoff before later resolution. Include only evidence actually available then. Event occurrence is not proof of observation time; canonical events lack an observed_at field, so describe any uncertainty for the reviewer without extending the schema.
3. Create canonical immutable snapshots, starting at revision zero with no events and incrementing on each append. Generate canonical hashes and previous-hash links. Give divergent histories distinct case IDs. Do not blindly convert legacy business revision numbers.
4. Write canonical model-visible decision-input files, canonical evaluator-only decision-label and episode files, and evaluator-only criteria sidecars. Use the exact structures in FORMAT.md and supplied schemas; do not add backend fields.
5. In criteria, record acceptable dispositions, required details, visible evidence IDs, forbidden claims/actions, missing information, authority notes, ambiguities, human control, risk and follow-up. Accept several next steps where policy/evidence permits them. Never promote a participant's assertion into trusted authority.
6. Create manifest rows with package-relative paths and SHA-256 of exact saved input, label, criteria and episode bytes. Assign all related records to one family and one split before tuning. New seeds remain development unless a human explicitly establishes another allocation.
7. Mark generated annotations assistant_authored_draft and canonical review unreviewed, with no invented reviewer or review date. Human-authored drafts likewise remain unreviewed. Do not call drafts gold labels or training-eligible.
8. Validate structure and cross-record links with python3 scripts/validate.py . from the package root. Report validation results separately from semantic correctness and unresolved questions.

Model-visible inputs must not contain answers, acceptable-action lists, rubric hints, hidden future events, manifest tags or reference labels. Evaluation agents must receive only selected input bytes, without access to the dataset repository. Preserve source statements as statements and do not invent company policy, photos, consent, system readback or completed effects.

Output the files plus a concise review queue: independent-family count, snapshot count, provenance limitations, excluded records, unresolved ambiguities and requested human decisions. No model training, semantic grading, runner compatibility or benchmark quality should be claimed from file creation or schema validation alone.
