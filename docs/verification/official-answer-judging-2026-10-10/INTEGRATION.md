# Publication and concurrent review boundary

This assessment evaluates the exact originals at
`cebf1b2b9520bcae260f1b8c2a50443490f97969`. Its complete, verified publication
commit is `6421988968ca9023bbb1ff05cd7614cb5985f087`.

While the assessment ran, teammate commit
`fc842ea1a4d1062ef458f8902d3bb7059dc89b2b` reached remote `main`. It added nine
separate `REVIEW.md` proposals, links to those reviews in nine `ANSWER.md` files,
a comparison report, and runtime changes for future execution. It did not replace
the retained candidate JSON or the original answer body. The teammate then reverted
that change in `da18c52`; both commits were integrated without overriding their work.
The human review notes were **not** supplied to the three judges and are **not**
assessed or endorsed by their scores.

Therefore the audit's 346-unchanged-files statement applies to the local
assessment execution against the original snapshot. After the teammate revert,
the `ANSWERS/` tree was byte-identical to that snapshot. The user's subsequent
request added labelled post-hoc assessment sections to each answer and reasoning
file. These change full-file hashes but preserve every original byte as a prefix;
the appended observations were not supplied to any judge. Report answer links
remain commit-pinned, and exact reviewed bytes remain under `packet-final/frozen/`.
No original response, prompt, candidate, judgment, or frozen manifest was changed
to accommodate the concurrent commit.

## Offline reproduction

Use a separate checkout of the assessment commit rather than editing the current
workspace or overwriting any original answers:

```sh
git worktree add --detach /tmp/proofkey-assessment-replay 6421988968ca9023bbb1ff05cd7614cb5985f087
cd /tmp/proofkey-assessment-replay
python3 -B docs/verification/official-answer-judging-2026-10-10/judge.py verify --packet docs/verification/official-answer-judging-2026-10-10/packet-final
python3 -B -m unittest discover -s docs/verification/official-answer-judging-2026-10-10 -p test_judge.py -v
```

The directory must not already exist. These commands make no model calls.
Verification on a later checkout may intentionally report `published_answer_changed`;
that is the preservation guard working, not permission to update frozen hashes.
Neither the teammate review notes nor this new post-hoc assessment prove that a
judge-to-revision loop existed before 16:30 or that replacements are permitted.
Inline score/status summaries and judge explanations are annotations, not
replacement answers, original model reasoning, or new system executions.
