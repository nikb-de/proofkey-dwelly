# Official Reality Test export audit — 10 October 2026

The exported [ANSWERS](../../../ANSWERS/README.md) contains all 30 case directories, `001`–`030`, with one `ANSWER.md` and one `REASONING.md` each. This audit checks packaging and retained-record fidelity; it does not grade the business correctness of the model answers.

| Check | Observed result |
| --- | --- |
| Answer and reasoning pairs | 30 / 30 present |
| Required answer sections | 30 / 30 contain input, proposed decision, actions actually taken, escalation, uncertainty, errors/final status, and exact retained candidate |
| Local links in answer/reasoning files | 402 checked; zero broken after attachment alias packaging |
| Exact candidate JSON | 30 / 30 match the retained candidate, including the null failed candidate |
| Public evidence references and uncertainty | 30 / 30 match retained output exactly |
| Exact cited source excerpts | 155 / 155 match the frozen model-input message bodies |
| Accepted candidate reparse | 29 / 29 reproduce the stored candidate with unchanged `model.parse` |
| Failed result preserved | Case `014`: `invalid_model_output`; raw response and error retained, no replacement answer |
| Retained record byte equivalence | 120 / 120 match campaign files: result, wire, intent and input for each case |
| Original source byte equivalence | 79 / 79 match the frozen campaign source files |
| Extraction sidecar byte equivalence | 25 / 25 match the frozen campaign sidecars |
| External operational effects | Explicitly zero; model actions remain proposals |

## Attachment-link packaging fix

Verbatim history excerpts contain links such as `attachments/file.pdf`. Since those excerpts appear in top-level `REASONING.md`, 18 such links initially resolved outside their preserved `SOURCE/attachments` location. All 19 original attachment files were copied, without modification, to matching per-case `attachments/` alias directories. Every alias is byte-identical to its `SOURCE/attachments` original and therefore has the same SHA-256 recorded in [EXTRACTION_MANIFEST.json](../../../ANSWERS/EXTRACTION_MANIFEST.json).

Aliases cover cases `002`, `006` (two files), `007`, `008`, `010`, `012`, `014`, `015`, `016`, `018`, `019`, `022`, `025`, `026`, `027`, `028`, `029` and `030`. No answer text, reasoning text, original source, model result, wire record, input, intent or frozen runner file was edited by this fix. The subsequent link check reports zero broken links.

## Provenance and interpretation

The comparison source is `/tmp/proofkey-reality-campaign-20261010`, primary profile `anthropic-claude-sonnet-5-5`, explicit high effort. Its exact baseline system SHA-256 is `61592fb429180e7da972a572ffc17e0379944c8bd7f2a84f049f725e510cbf80`; the baseline differs from the submitted platform system only by its preserved trailing newline. Official input commit is `ce84e8c0d8f7f8ddacd8d8fcfe53516c22885db7`; submitted application commit is `fd8533297d259f4a997710045852e4eb2f3ef771`.

The run exercised the frozen model input/prompt/provider/parser path directly. It did not exercise the product UI or execute customer messages, carrier changes, bookings, returns, payments, or real escalations. Schema acceptance and source fidelity are distinct from independently assessed decision quality. PDF text and native PNG OCR remain unverified source derivatives; case `022` retains its low-confidence OCR caveat.
