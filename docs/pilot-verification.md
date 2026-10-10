# Dwelly case intake pilot — verification

Date: 2026-10-10. Scope: standalone tools under `tools/dwelly_cases` in the source workspace, outside the trusted runtime. Executable tools and runtime source are not included in this repository. This report does not qualify a live agent or hackathon submission.

## Source and measured corpus

Source: [DwellyOrg/HackatonPublicCases](https://github.com/DwellyOrg/HackatonPublicCases), local commit `9bcdca585955dfb930005ed742572606e68f5688`.

The final local-workspace import at `outputs/dwelly-intake-2026-10-10-final`, packaged as [offline pilot data](../data/dwelly-public-cases/README.md), contains:

| Quantity | Observed |
|---|---:|
| Logistics cases | 50 / 50 |
| Source files | 106 |
| History events | 228 |
| Total attachments | 6 |
| Attachments available at the decision cutoff | 0 |
| Held-out cases | 0 |

Source inventory SHA-256: `8e4552be3861d047b9be18cba2a6eeba83d00d54d7c8deb5dfb4e230ad513669`.

Input set SHA-256: `d68860ef69a5994b940a9e858a12b4ff84617ccce9a08ef4e54aa80544164f0a`.

The importer preserves raw byte copies. The proposer receives only visible messages and visible-attachment metadata. Whole-history/index data and their hashes stay outside its input. A future-answer mutation test leaves the agent snapshot unchanged.

## Final pilot outputs

Primary result: [pilot summary](../data/dwelly-public-cases/pilot/summary.json), copied from local-workspace `outputs/dwelly-pilot-2026-10-10-reviewed/summary.json`.

Independent repeated invocation: local-workspace `outputs/dwelly-pilot-2026-10-10-reviewed-repeat/summary.json` (not included in this repository).

| Measurement | Result | Interpretation |
|---|---:|---|
| Produced valid unsent drafts | 50 / 50 | Schema/contract coverage only |
| Missing outputs | 0 / 50 | No baseline execution failure |
| Exact normalized routing agreement | 11 / 50 | Recipient + channel proxy, **not accuracy** |
| Explicit operator-review drafts | 24 / 50 | Unresolved fallback, **not resolution** |
| Source-cited safety-escalation drafts | 2 / 50 | Tested heuristic behavior, not safety calibration |
| Same-input proposal repeatability | 50 / 50 | Deterministic baseline |
| Same-input grading repeatability | 50 / 50 | Deterministic structural evaluator |
| Semantically assessed decisions | 0 / 50 | Still unassessed |
| Live provider calls / operational effects | 0 / 0 | Offline only |

Proposal set hash: `fef641f6e072b4538af4d3fbec578e7431e17371858818416c09067233bb649d`.

Assessment set hash: `b099c3296ee550ab294d93c919d52439e2d5c61fe65727da0052c0cb05c076f6`.

Routing disagreement includes preserved role suffixes, different channels, alternative defensible actions, and genuinely weak baseline routing. The counter must not be renamed correctness. It deliberately does not strip recipient roles just to inflate agreement.

## Tests and review

Provisioned interpreter: CPython 3.12.14 at `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python`. System `python3` is 3.9.6 and is not the qualified interpreter.

Historical standalone command from the local workspace (the interpreter and test source are not included here):

```sh
PYTHONDONTWRITEBYTECODE=1 \
  .superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python -B \
  -m unittest discover -s tools/dwelly_cases/tests -v
```

Observed: **58 tests passed**. The initial importer/CLI tests failed before implementation. Independent review findings were reproduced as failing tests before correction: alternate-link bypass, whitespace metadata, pre-read resource bounds, staged publication, malformed/self-hashed future provenance, malformed reference actions and completion-claim patterns. Canonical case 001 and single-window controls also went RED/GREEN.

Controls separate known-valid, wrong-route, missing/malformed, unsupported-completion and unknown-role outputs. Swapped/repeated assessor order is tested. These controls qualify those narrow checks only, not a semantic judge. An independent agent reviewed the importer and final boundaries; the author applied the final fixes and reran tests. A fresh read-only post-fix review independently checked all 106 raw files against the pinned source, all 50 snapshots/references, saved proposals/assessments and aggregate hashes, and byte-identical repeat outputs. It reported no further findings in that offline scope. This is not production or semantic-quality certification.

Full runtime regression remains **pending** at this package snapshot; no completed-runtime claim is made. Runtime source/package files were not modified by the offline pilot slice and are not included in this repository.

## Architecture companion

The [detailed architecture](architecture.md) incorporates all four current files from the supplied Drive folder. It separates the implemented offline pilot and synthetic runtime from proposed semantic reasoning, authenticated ingress and native adapters. A 19-row source-to-design-to-test matrix marks existing test hooks separately from missing acceptance tests. The Drive originals are not copied into this repository.

All four Mermaid diagrams were parsed and rendered with Mermaid 11 in headless Chrome 155.0.8059.40 and visually inspected. One sequence-diagram punctuation error and one attachment-case enumeration error were corrected. The copied [render receipt](diagrams/render-report.json) and [components](diagrams/diagram-1.png), [information model](diagrams/diagram-2.png), [resolution sequence](diagrams/diagram-3.png), and [adaptation](diagrams/diagram-4.png) images originate from local-workspace `outputs/architecture-verified-OiUWxH/`. The receipt's document digest identifies the source document at render time, not the later edited body or this repackaged document; the four diagram definitions are unchanged. Rendering is presentation QA, not validation of the proposed live architecture.

## Limitations and next decision

- The deterministic baseline is a reference consumer and smoke test, not the desired semantic agent. It is weak on many specialist workflows and cannot substantiate complete safe resolution.
- All public examples and source references have been exposed. Use a genuinely separate unseen case set before any generalization claim.
- Raw data is included only in the explicitly authorized private internal snapshot. Upstream rights remain unresolved; no public redistribution is authorized by this report. Upstream data is not relicensed by a repository code license; see [dataset provenance and rights](../data/dwelly-public-cases/README.md).
- No live connectors, LLM inference, vision, speech, authentication, payout or actual operator acceptance is demonstrated.
- In-process isolation is a data-flow convention, not a malicious-agent security boundary. An external agent must receive only its selected snapshot/assets.
- Publication is atomic on the tested local filesystem, but crash recovery and hostile concurrent filesystem mutation are not qualified.

The next useful increment is a provider-backed semantic proposer against the same isolated inputs, with explicit run identity and independent human-reviewed scoring. It should not bypass the existing deterministic operational gates.
