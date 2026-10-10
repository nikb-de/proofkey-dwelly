# Independent packet and completed-run integrity audit

Audited the final packet and completed 90-record run on 2026-10-10. This auditor made no provider calls and changed no published answer, production code, frozen runner, or prior report.

## Frozen identity and preservation

- Canonical packet: `packet-final/`. Earlier draft packets are not the audited run input.
- Packet manifest SHA256: `f8cc1b0126cc8ba785a3ca55c2ff28673de987f733fba2a03658650661d18f84`.
- Frozen `judge.py` SHA256: `70152d108b72ae503a54912c734607f291d20c67fdbe422ecf52d0fa5d1d76fb`.
- All **152 packet artifact hashes** verified, including all **120 original files**: `INPUT.json`, `ANSWER.md`, `REASONING.md`, and `SOURCE_RESULT.json` for each of 30 cases. Frozen copies equal original bytes.
- The independent pre-audit inventory at `/tmp/proofkey-answers-before-judging-20261010.json` covers **346 files** under `ANSWERS/`. At the completed-run check, every path and SHA256 was unchanged: zero additions, removals, or changed files.

This statement is scoped to the completed assessment checkout. Subsequent merges
preserved a teammate's concurrent review commit and their later revert. Neither was
part of the assessed snapshot. [INTEGRATION.md](INTEGRATION.md) records the history.

## Judge boundary

- Every transmitted payload contains exactly the original `INPUT.json`, `ANSWER.md`, and `REASONING.md` UTF-8 strings; the exact retained `candidate`; and only `status`, `error`, `dispatch_attempts`, and `external_effects` from the result envelope. Full `SOURCE_RESULT.json` is retained offline, not transmitted.
- No producer/provider/model identity strings were detected in the 30 payloads. Provider identities remain in the host-side profiles and receipts, not judge-visible answer data.
- No human reference answer, expected score, prior judge output, or additional outcome label is introduced. The eight rubric definitions are the existing unchanged rubric object, not case-specific ground truth.
- Case 014 retains a null candidate. The system requires abstention, and host validation rejects a non-abstaining judgment for a missing candidate. Abstentions and missing judgments do not contribute numerical scores.
- All 19 messages appended after the formal E-numbered cutoff are existing attachment derivatives, timestamped at the cutoff and citing earlier visible E-numbered events. No later business events were added. Exact supplied evidence remains untrusted; OCR and unseen-image limitations are explicit.

## Operational checks

Nine offline tests passed, using mocked providers only. Reviewed controls include a 450-second worker-start dispatch deadline; six concurrent calls maximum and two per provider; durable reservation and intent before dispatch; no retry of persisted intents; stop on HTTP 401/403/404/429 or model-identity mismatch; per-provider/model USD 25 admission cap; retained error records; and a 30-case denominator per provider even when calls are missing.

The requested seats are `gpt-6.1-sol`, `claude-sonnet-5-5`, and `gemini-3.8-flash`. All 90 retained provider responses report the exact requested model identity.

## Completed-run receipts

- **90 scheduled requests, 90 unique intents, 90 unique records, 90 budget reservations and 90 outcomes**; zero missing scheduled records and no replacement attempts.
- All record self-hashes and response hashes verify. Each intent and record matches its frozen schedule row, model, system hash and prompt hash. Each prompt remains bound to the exact published candidate and source text described above.
- All 87 accepted judgments reparse and validate identically from their retained raw response text; the consolidated `results.json` equals the individually retained records.
- Three raw responses are retained as `invalid_judgment` errors: `004-anthropic`, `009-anthropic`, and `017-anthropic`. They are not repaired or scored. All three judges abstained on case 014, whose candidate remains null.

| Provider / observed model | Recorded | Valid judgments | Scored | Abstained | Errors | Missing records |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OpenAI / `gpt-6.1-sol` | 30 | 30 | 29 | 1 | 0 | 0 |
| Anthropic / `claude-sonnet-5-5` | 30 | 27 | 26 | 1 | 3 | 0 |
| Gemini / `gemini-3.8-flash` | 30 | 30 | 29 | 1 | 0 | 0 |

Accounting caveat: the inherited nested Anthropic `assessment.missing_count` is 3 and `assessment.invalid_count` is 0 because the wrapper passes each rejected judgment to aggregation as `None`. Those are the three **recorded errors**, not three absent calls. The canonical outer `errors=3`, `missing=0`, retained records and table above preserve that distinction; the frozen result was not rewritten.

The ledger reserved USD 8.67439775 total under the conservative local admission policy (Anthropic 3.652378; OpenAI 3.652378; Gemini 1.36964175), below each USD 25 provider/model cap. Reservation is not verified provider billing.

- `packet-final/live/results.json` SHA256: `ca5346dd92879f760e62101dce7c99b6db7efdf7fae87787d1338268f511a1c5`.
- `packet-final/live/summary.json` SHA256: `b67ad99117a4186078faba5c8940a02456c376daad16669686bbeca0d0a905aa`.
- All **221 local Markdown links** in the assessment directory's top-level reports resolve, including the completed results, summary, trace manifest and original answer links.

## Limitations and interpretation

The validation adapter now accepts both original E-numbered events and the supplied `attachment-*` derivative IDs. It first requires a unique original cutoff, rejects every message timestamp after that cutoff, and rejects post-cutoff-position messages unless their channel is `attachment_derivative`. It then extends only the citation-validation boundary to include those original, cutoff-safe supplements. No prompt or source answer was changed by this fix.

This is an **unqualified post-hoc whole-answer assessment**. Human calibration is **NOT_RUN**; the earlier action-only pilot does not qualify this framing. Scores cannot establish factual correctness, production readiness, or authorization. Published actions remain proposals/model analysis, not completed business operations.
