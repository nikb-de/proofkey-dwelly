# Case 001: two mobile E2E recordings

Status: technically verified, but **rejected by the user for presentation/UI quality**. Date: 10 October 2026. These engineering-console captures are retained as evidence, not the recommended hackathon presentation. The current replacement is the rounded, 40-second mobile showcase described in `SHOWCASE.md`.

## Archived recordings

- Scripted replay — 50 seconds: zero model calls. The rejected film is retained locally at `recordings/synthetic-1791642519120-6cb35564/case-001-synthetic-50s-stable.mp4` and is excluded from repository publication.
- Live LLM — 50 seconds: five actual OpenAI calls; requested and observed `gpt-6.1-sol` on every receipt. The rejected film is retained locally at `recordings/llm-1791642541219-2d58c523/case-001-llm-50s-stable.mp4` and is excluded from repository publication.

Both are actual Chrome captures of the existing platform, edited into five ten-second stages. They are not generated mockups. Waiting, setup and short navigation transients are omitted. The uninterrupted source videos, final-state read-only pickups, edit manifests and screenshots remain in the local archive; `assembly-stable.json` is its final edit decision list. Earlier exports are retained locally but superseded. The current published films are linked in [SHOWCASE.md](SHOWCASE.md); [PUBLICATION.md](PUBLICATION.md) lists the exact publication boundary.

## Published source evidence

- [Successful scripted capture report](recordings/synthetic-1791642519120-6cb35564/capture-report.json), including HTTP/state records and the final local receipt.
- [Successful live LLM capture report](recordings/llm-1791642541219-2d58c523/capture-report.json), including HTTP/state records, five model jobs and the final local receipt.
- Original model-job records: [1](recordings/llm-1791642541219-2d58c523/model-1.json), [2](recordings/llm-1791642541219-2d58c523/model-2.json), [3](recordings/llm-1791642541219-2d58c523/model-3.json), [4](recordings/llm-1791642541219-2d58c523/model-4.json), [5](recordings/llm-1791642541219-2d58c523/model-5.json).

These JSON records are published unchanged. Any `/Users/...` paths inside them describe historical files on the capture machine; they are not portable repository paths. Their source identity, source hashes, model outputs and operational qualifications remain intact.

## What the videos prove — and do not prove

The frozen `source.case-001-terms.json` has SHA-256 `fc1f55e8258346b53f77b5cce03ae6fb7e0b227433daab19894caa4da8d160cf`, from source commit `15ec6c7faa1d48b0bd6ac9093936d2cc8f69a53c`. Dates are explicitly rebased from 2 February to 10 October 2026; times remain UTC. Thus the requested slot is 13 October, 18:00–20:00; the offered and accepted slot is 14 October, 10:00–13:00.

Source messages 001–011 are replayed in order. Complete future states, author labels and later messages are never supplied to an earlier inference. `source-context` supplies initial facts and explicitly labelled routing configuration. Two additional **simulated** Dispatch readbacks bind the local request IDs; they are not authentic carrier responses. The original source messages remain separate and unchanged apart from the documented date transform.

Each recorded case finished at revision **21**, coordination version **7**, `booking_confirmed`, with two local operation receipts. Physical delivery remains `not_confirmed`, and external business effects remain **0**. The LLM proposes; explicit reviewed operator commands change local state. This is neither an autonomous carrier booking nor a production integration.

| Recording | Case ID | Model links | Final state |
|---|---|---:|---|
| Scripted | `terms-video-synthetic-1791642519120-6cb35564` | 0 | `booking_confirmed` |
| Live LLM | `terms-video-llm-1791642541219-2d58c523` | 5 | `booking_confirmed` |

At capture time, the cases were available on the isolated local service at `http://127.0.0.1:8110/`. This is a historical local endpoint, not a published service. The existing service on port 8105 was not restarted or reconfigured. Database schemas: `proofkey_live_video_20261010` and `proofkey_live_video_20261010_models`.

## Actual live model observations

All five jobs succeeded with one dispatch each and no automatic retry. Receipts report 14,805 input tokens, 878 output tokens, and 20.91 seconds of aggregate provider latency. Usage-based Standard-price estimate: **$0.03839**, not an authoritative billing receipt. Configured budget reservation is deliberately conservative and is not actual spend. [Official model information](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [pricing](https://developers.openai.com/api/docs/pricing).

| Source cutoff | Observed next action | Assessment |
|---|---|---|
| 001 | Ask recipient for alternative windows | Differs from the author's cancel-first sequence. Operator follows the cancellation workflow; model context is advisory, not agreement. |
| 005 | Ask Dispatch about requested evening/concierge terms | Aligned; availability is not invented. |
| 007 | Present the daytime, recipient-present, no-charge offer for consent | Aligned; changed terms are preserved. |
| 009 | Ask Dispatch to book accepted terms | Aligned; consent is not treated as booking confirmation. |
| 011 + local readback | Propose notifying the recipient of reported confirmation | Additional follow-up rather than the author's terminal `completed` state. No physical delivery is claimed. |

These are five related prefixes of **one synthetic case**, not five independent evals or a calibrated accuracy score. `evaluation=null` in every job. The model input uses the platform's generic coordination goal, not the source's narrower goal; it also omits the author's separate cancel-first explanation. That task-definition gap must be fixed before treating the first/last differences as isolated model failures. No output was rewritten or retried to hide them.

## Verification

- Backend/model suite: **363 passed**, **361 subtests passed** using the configured PostgreSQL test environment.
- UI suite: **91 passed**, zero skipped/failed, including actual Chrome controls.
- Direct PostgreSQL readback: both case histories contain versions 1–7; head revision 21; model links 0/5; five `succeeded` jobs and five dispatches.
- Archived 50-second MP4 contract: **1080×1920**, **30 fps**, **1,500 frames**, exactly **50.000 seconds**, silent H.264. Full decode and sampled-frame checks are retained in the local archive. These films passed technical checks and were subsequently rejected for UI/presentation quality.
- The first scripted capture failed because hash-only navigation retained stale UI data. The recording runner now explicitly reloads after external event ingestion. That failed attempt is retained separately in the local archive, excluded from repository publication, and is not a final deliverable.

## Reproduce

From this worktree, start a dedicated local platform with current profiles, an isolated schema, and the existing private provider env. Never put keys in this folder. `--allow-live` is required only for the live variant.

```sh
PROOFKEY_RECORD_TERMS=1 PROOFKEY_RECORD_MODE=synthetic node docs/demos/2026-10-10-case-001-terms/record-mobile.mjs
PROOFKEY_RECORD_TERMS=1 PROOFKEY_RECORD_MODE=llm node docs/demos/2026-10-10-case-001-terms/record-mobile.mjs
node docs/demos/2026-10-10-case-001-terms/pickup-final.mjs <new-recording-directory>
node docs/demos/2026-10-10-case-001-terms/stabilize-cuts.mjs <new-recording-directory>
python -m tools.dwelly_platform.video_assembly <new-recording-directory>/assembly-stable.json
```

Each recording creates a fresh case; the live runner is capped at five submissions and stops on a failed or ambiguous provider outcome. Do not rerun paid calls merely to recover video editing; reuse the preserved capture and receipts. The final pickup performs GET requests only. Runtime contracts and the platform state machine were not changed for the recordings.
