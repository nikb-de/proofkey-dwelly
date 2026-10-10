# Annotation and review checklist

Complete this review per source family and per decision. Structural validation supplements human review; it does not replace it.

- **Use and privacy:** source owner permits this use; source register records provenance and restrictions; identifiers and identifying combinations are reviewed; no credentials or unnecessary personal details are copied.
- **Independence:** family groups all related sources, translations and counterfactuals; split is assigned before tuning; branches have distinct canonical case IDs where histories differ.
- **Time:** `as_of` is the observation cutoff; every event, extraction and receipt was available then; future resolution is absent. Canonical events lack `observed_at`, so this needs curator verification.
- **Identity:** input ID is unique; source tuple matches snapshot; canonical hashes and previous hashes are correct; append revisions are immutable; episode/label/criteria references resolve.
- **Evidence:** separate messages, readable content and verified facts; missing attachment does not imply absent inline evidence; cited evidence IDs are visible; no invented media bytes or extraction provenance.
- **Policy and authority:** policy is sourced or explicitly hypothetical; raw message roles do not grant authority; uncertain policy is acknowledged; proposed actions do not claim execution; required approval and recipients are explicit.
- **Decision:** expected disposition fits the visible state; alternatives are accepted where justified; required details are minimal; missing information, forbidden claims/actions, risk and follow-up are clear.
- **Human control:** distinguish ordinary information requests from approval; do not label every question an escalation; do not infer consent, cancellation or completion from silence or an intermediate status.
- **Review:** mark drafts as drafts. A real reviewer resolves or preserves ambiguities and records their own ID/time before promotion. Rejected or unreviewed records cannot enter training; reviewed data is still not automatically an independent benchmark.
- **Isolation:** evaluated agent sees input bytes only; private labels, criteria, manifests, other snapshots and generator instructions are inaccessible.
- **Validation:** run `python3 scripts/validate.py .` and relevant tests; inspect failures without weakening checks to fit data; record semantic limitations separately from structural success.

Reviewers should record uncertain or disputed policy, missing source permission, incomplete cutoff evidence and alternative correct decisions. Exclude unresolved examples from scored comparisons or report them separately; never invent certainty to make a label easy to score.
