# Post-hoc assessment of the exact official answers

This auxiliary experiment judges the 30 already-published answers in `ANSWERS/`,
without generating replacement answers. At the user's subsequent request, the
current `ANSWER.md` and `REASONING.md` files append labelled post-hoc sections;
their original content remains a byte-exact prefix, and `packet-final/frozen/`
preserves the complete original reviewed files. The canonical
frozen input is [packet-final](packet-final/manifest.json). Earlier local
preparation packets are superseded, made zero API calls and are excluded from
the published package.

See the [append-only audit](APPEND-AUDIT.md) and
[annotation manifest](ANNOTATION-MANIFEST.json) for original-prefix and appended-file hashes.

The evaluated answers are pinned to `cebf1b2b9520bcae260f1b8c2a50443490f97969`,
not whichever text is currently on `main`. Concurrent teammate commits added
and then reverted separate human review notes. See [INTEGRATION.md](INTEGRATION.md)
for that history and the exact reproducible assessment revision.

Completed: 90 attempts and retained responses, 87 valid judgments, 84 scored
judgments, three abstentions for case 014, and three malformed Anthropic
judgments retained without repair. See [RESULTS.md](RESULTS.md) and the
[trace manifest](TRACE_MANIFEST.json).

The three requested seats are `gpt-6.1-sol`, `claude-sonnet-5-5` and
`gemini-3.8-flash`. Each is scheduled once for each answer: 90 attempts total,
subject to safety stops. Every request includes the exact original `INPUT.json`,
`ANSWER.md`, `REASONING.md`, structured candidate and status. Producer identity,
prior judge results and human reference answers are not included. Original
`SOURCE_RESULT.json` bytes are preserved only as offline provenance.

The existing eight rubric anchors are unchanged, but the whole-answer review
framing is new. **These are uncalibrated model opinions, not official scores,
human ground truth or operational approval.** The earlier action-only reliability
pilot does not establish reliability for this framing. Case 014 has no accepted
candidate and is unassessable; its abstention placeholder scores are excluded
from averages, never interpreted as zero accuracy.

Evidence is text-only: the original inputs contain the available extracted
attachment text, but the judges do not inspect original image/PDF pixels or
missing OCR confidence metadata. See [INVENTORY.md](INVENTORY.md) for coverage.

## Safety and provenance

The packet freezes hashes for all four original files per case (120 files),
all 30 effective prompts, the unchanged rubric, current provider configuration,
and the reviewer/provider/validator implementations. Original hashes are checked
before and after execution. Requests are limited to six globally and two per
provider, with no retries. Authentication/model/429 failures stop new calls to
that seat; a budget refusal stops its seat without discarding active results.
New dispatch stops after 450 seconds; provider requests have a 120-second
timeout. Durable timestamped intents, reservations, complete normalized provider
responses, identities, judgments, hashes and statuses are retained.

Conservative full reservation for all 90 scheduled attempts is $8.67439775:
$3.652378 each for OpenAI and Anthropic and $1.36964175 for Gemini. Each seat has
a $25 local reservation cap. Reservations are not provider billing receipts and
are not refunded after failed or unknown requests.

## Reproduce

Run from the root of a separate clean checkout of assessment commit
`6421988968ca9023bbb1ff05cd7614cb5985f087`, as described in [INTEGRATION.md](INTEGRATION.md).
Do not prepare from today's annotated `ANSWERS/`: that would expose prior judge
comments to a new reviewer. Preparation makes no API calls. A new empty packet
path is required; no frozen packet is overwritten.

```sh
python3 -B -m unittest discover -s docs/verification/official-answer-judging-2026-10-10 -p test_judge.py -v
python3 -B docs/verification/official-answer-judging-2026-10-10/judge.py prepare --packet /absolute/path/to/new-packet
python3 -B docs/verification/official-answer-judging-2026-10-10/judge.py verify --packet /absolute/path/to/new-packet
```

Only after explicit live authorization, pass `run --live --env-file` with the
private environment file path. Never include credentials in a packet. A rerun
does not retry persisted intents, including unknown outcomes.

The canonical packet's `verify` command intentionally rejects a checkout whose
original answer bytes have changed. Use the assessment revision documented in
[INTEGRATION.md](INTEGRATION.md); do not repair the frozen hashes to match later notes.

The live [summary](packet-final/live/summary.json), [all results](packet-final/live/results.json)
and [RESULTS.md](RESULTS.md) separate valid/scored coverage, abstentions,
failures and critical-flag disagreement. No majority or aggregate authorizes a
business action.
