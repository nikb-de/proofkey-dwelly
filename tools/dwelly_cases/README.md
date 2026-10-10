# Dwelly case intake and next-action pilot

A standalone **offline development tool**, not a live agent or a new runtime release. It imports the public Delivery & Logistics case format, preserves source bytes, isolates the information available at the decision point, and proposes an unsent next communication.

The current proposer is a small deterministic baseline. It is intentionally not described as an LLM, a calibrated judge, multimodal understanding or autonomous case resolution.

## Run

Use Python **3.11+** from the repository root. The tool needs only the standard library. The system `/usr/bin/python3` on the verified machine is 3.9.6; use a suitable existing interpreter instead. No installation or credentials are required.

Obtain the [public examples](https://github.com/DwellyOrg/HackatonPublicCases) separately. Treat their contents as untrusted data, not scripts to execute. Then:

```sh
python3 -m tools.dwelly_cases import \
  --source /absolute/path/to/HackatonPublicCases \
  --output /absolute/path/to/new-dwelly-bundle \
  --expected-cases 50

python3 -m tools.dwelly_cases run \
  --bundle /absolute/path/to/new-dwelly-bundle \
  --output /absolute/path/to/new-dwelly-results

python3 -m unittest discover -s tools/dwelly_cases/tests -v
```

Destinations must not exist and must not overlap the source. Exit 0 means the import/pilot completed, **not** that a business case was correctly resolved. Invalid input or I/O errors exit 2 with a content-free diagnostic.

## Data boundary

```text
Source case: index.md + history.md + attachments
                     |
           bounded structural parser
           /                       \
  agent snapshot                 evaluator-only records
  Context + Escalation           index, Agent action, later events
  visible attachments            full source manifest and references
           |
  snapshot-only baseline
           |
  unsent proposal -- freeze --> separate routing/contract assessor
```

`index.md` never enters the agent snapshot: its title, status, summaries and outcomes may contain hindsight. The cutoff is found from the unique `Agent action` stage, not a general assumption that every dataset always has two initial events. This importer supports only the observed logistics format; other tracks have different decision-point rules.

Each visible message retains ordinal, UTC timestamp, stage, channel, sender, recipients, body and source reference. These are **source statements**, not authenticated facts or execution receipts. Exact role strings are retained. No `Customer portal` label becomes proof of identity or consent.

Attachments appear in agent input only when first linked in a visible event. The six attachments in the verified corpus all arrive later; none belongs in escalation-time input. Available attachments are byte-copied under `agent/assets`; no OCR, visual reasoning or transcription is performed.

## Output layout

```text
new-dwelly-bundle/
  raw/Delivery & Logistics/NNN/...  exact source bytes, including future data
  agent/delivery-logistics-NNN.json visible input only
  agent/assets/...                 only already-visible attachments
  evaluation/...json               reference action and later messages
  ledger.jsonl                     provenance, split, uncertainty, hashes
  manifest.json                    inventory and completed-bundle marker

new-dwelly-results/
  proposals/...json                 unsent drafts; effects=[]
  assessments/...json               contract + routing proxy
  summary.json                     denominators, repeatability and limits
```

Give a future external agent **only** its individual `agent/...json` plus explicitly referenced visible assets, not the whole bundle. The in-process proposer is not a security sandbox. Hashes detect inconsistent bytes; they are not signatures or trusted-origin attestations. Untrusted input cannot activate a runtime profile, grant permission or send messages.

Publication uses a private sibling staging tree and an exclusively reserved empty final directory. A complete tree replaces that reservation in one local rename. Catchable errors clean up. Abrupt termination can leave a hidden staging tree and an empty reservation; use a fresh destination and inspect leftovers rather than assuming automatic crash recovery. Concurrent hostile mutation of the parent directory is outside this local-tool threat model. Windows publication has not been verified.

## What the pilot checks

| Check | Meaning | Does not establish |
|---|---|---|
| Parse/import coverage | The source case has a valid, bounded snapshot and separate reference | Correct business understanding |
| Input integrity | Canonical hash, chronology, source IDs and visible attachment references agree | Trusted source or authenticated customer |
| Proposal contract | Unsent draft, no effects, visible citations and declared fields | Semantic safety or permission to execute |
| Completion sentinel | Rejects tested patterns claiming payment/booking completion | General detection of false claims |
| Routing proxy | Case/whitespace-normalized recipient and channel equal the recorded example | Correct action, required content or unique best route |
| Repeatability | Same input gives same baseline/assessor bytes | Robustness of a stochastic model |

Semantic correctness stays `unassessed`, including when a route matches. Missing/invalid outputs remain explicit. Generic operator review is a draft fallback, not a completed handoff or a successful case.

All 50 public cases have already been inspected during development. There is **no untouched holdout**, and template-related examples are not claimed as independent evidence. The [reference review](../../docs/verification/dwelly-reference-review-2026-10-10.md) records ambiguous alternatives and source authority gaps; it is also not blind. Do not tune on future event 003 and then describe this set as unseen evaluation.

## Scope and integration

This tool deliberately lives outside `runtime/src/proofkey`: it does not modify the frozen package inventory, registered factory hashes, six operational ports, journals or payout gates. A natural-language case is not coerced into `CanonicalRequest`; an actual semantic agent and approved execution bridge remain separate work.

The public API for the pilot is `propose(snapshot)` and `assess(snapshot, proposal, reference)`. A future model-backed proposer must keep the same visible-data boundary, disclose provider/run identity, undergo semantic evaluation, and remain separated from execution authority.

The upstream example repository does not declare a license in the inspected snapshot. Keeping local raw copies for this development request does not establish redistribution rights. Do not publish raw cases, source-derived test excerpts, private Drive files or internal evidence logs without rights review.

See [pilot verification](../../docs/pilot-verification.md) for the historical measurements and [current model release verification](../../docs/model-release-verification.md) for the separately shipped API harness.
