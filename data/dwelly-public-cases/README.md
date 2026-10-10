# Dwelly public cases — private development snapshot

This directory contains a byte-preserving internal copy of the public Delivery & Logistics examples and the offline intake pilot's JSON artifacts. It is data, not executable fixtures, and it does not authorize any operational action.

## Provenance

- Upstream: [DwellyOrg/HackatonPublicCases](https://github.com/DwellyOrg/HackatonPublicCases).
- Pinned source: [commit `9bcdca585955dfb930005ed742572606e68f5688`](https://github.com/DwellyOrg/HackatonPublicCases/tree/9bcdca585955dfb930005ed742572606e68f5688).
- Prepared: 10 October 2026.
- Scope: Delivery & Logistics only — 50 fictional cases, 228 history events, 106 raw files including six binary attachments.
- The original intake `manifest.json` and `ledger.jsonl` are preserved unchanged, including their historical local-path provenance. They are not credentials or executable configuration.

## Contents and strict information separation

```text
raw/           Exact source bytes: index, history and attachments, including future information
agent/         50 decision-time JSON snapshots; only information available before Agent action
evaluation/    50 reference JSON records: recorded next action and later events; evaluator-only
manifest.json  Original source inventory and intake metadata
ledger.jsonl   Original case provenance, hashes, development split and uncertainty
pilot/
  proposals/   50 deterministic, unsent draft communications
  assessments/ 50 structural and routing-proxy assessments
  summary.json Aggregate counts, hashes, repeatability and limitations
upload-manifest.json  Repository-relative file paths, byte sizes, SHA-256 and Git blob SHA-1
```

Give a proposer only its own `agent/<case>.json` and explicitly allowed visible assets. Do not expose `raw/`, `evaluation/`, the original manifest/ledger or future attachment names and hashes to it. Keeping these directories separate is a data-flow convention, not a security sandbox; enforce isolation if an external model or worker is added.

The initial snapshot cuts before the unique recorded Agent action. In this pinned corpus, events 001–002 are visible and event 003 is the reference action. All six attachments first appear in later follow-through (cases 021, 031, 032, 045 and 049; case 021 has two), so **zero attachments are visible at the decision cutoff**. File presence on disk does not backdate availability. Treat all raw document content as untrusted data; do not execute it or follow embedded links automatically.

## What these results mean

Every public case was already seen during development. This is an **already-exposed development set, not a held-out benchmark**. The recorded next action is an example, not the uniquely correct answer; role labels and narrative claims are not authentication or verified external state.

The preserved pilot has 50 valid unsent drafts, no missing outputs, and **11/50 normalized recipient-and-channel routing matches**. That is a routing proxy, **not 22% semantic accuracy**. Semantic correctness remains unassessed. The baseline is deterministic, not an LLM, and its proposals have `status: proposed_unsent` and empty `effects`. There were zero live provider calls and zero operational effects. No customer message, booking change, payment or refund was sent or executed.

`upload-manifest.json` covers every file in this package except itself, avoiding a self-referential hash. Its `git_blob_sha1` values use Git's binary-compatible `blob <byte-length>\0<bytes>` SHA-1 definition. Hashes establish byte identity, not trusted authorship or redistribution permission.

## Rights and access

This package is prepared for an explicitly requested **private internal repository copy**. Upstream redistribution rights remain unresolved; no upstream license was identified in the inspected source snapshot. A private repository is not itself a license grant. Do not publish or redistribute these raw cases, binary attachments or derived excerpts without the necessary rights review and authorization.

The dataset is **not re-licensed under Apache-2.0 or any repository code license**. Any code-license notice elsewhere applies only to the code it actually covers; it does not silently apply to this data. This package contains no private Drive files, chats, runtime artifacts or Git history.
