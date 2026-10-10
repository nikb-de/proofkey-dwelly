# Current API profiles

Reviewed against official provider documentation on **2026-10-10**. The adjacent
`model-profiles.current.json` is a separate, explicitly selectable configuration;
the historical example remains intact. This is an offline configuration update,
not a provider benchmark or an authorization to spend.

| Provider | Exact requested API model ID | Standard input USD / 1M | Standard output USD / 1M |
| --- | --- | ---: | ---: |
| OpenAI | `gpt-6.1-sol` | 2.00 | 10.00 |
| Anthropic | `claude-sonnet-5-5` | 2.00 | 10.00 |
| Google | `gemini-3.8-flash` | 0.75 | 3.75 |

These choices balance current reasoning capability and cost for bounded text
analysis. They are not a claim that each provider's most expensive model is
necessary or that these models have passed our workload's quality evaluation.
No API key was read and no inference request was sent to establish this table.

## Sources and boundaries

- OpenAI's [model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
  identifies `gpt-6.1-sol` as a reasoning model and supports the Responses API,
  text output, and structured outputs. Its [pricing table](https://developers.openai.com/api/docs/pricing)
  lists $2 input / $10 output for Standard at up to 272K input tokens. Above that
  threshold the full request is $4 / $15. Cache writes cost $2.50 per million at
  short context; cached reads cost $0.10. Fast, Ultrafast, and regional processing
  have additional charges. The application prompt limit is 65,536 UTF-8 bytes,
  substantially below the documented long-context threshold. This profile does
  not set a custom reasoning effort; the model page specifies `medium` by default.
- Anthropic's [Sonnet 5.5 model page](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)
  establishes the API ID and adaptive thinking support. Its
  [pricing table](https://platform.claude.com/docs/en/about-claude/pricing)
  confirms $2 input / $10 output; five-minute cache writes are $2.50, one-hour
  writes $4, and cache reads $0.10. Global first-party API rates are used here;
  US-only inference carries an uplift. The existing workspace-ID requirement
  is retained. No new provider-specific thinking configuration is added.
- Google's [Gemini 3.8 Flash model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
  identifies the stable `gemini-3.8-flash` endpoint with text output, structured
  outputs, and thinking. The [paid Standard pricing table](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash)
  sets $0.75 input / $3.75 output **through December 31, 2026**, including thinking
  tokens in output billing. It publishes $1.50 / $7.50 from January 1, 2027.
  Refresh or disable this pricing snapshot before that date; the existing loader
  has no automatic date-expiry enforcement. Free-tier availability and data-use
  terms differ. This configuration does not select a billing tier, enable
  caching, or request search/Maps grounding.

## Runtime identity and accounting

Configured/requested model IDs are not observations. Until an authorized live
request succeeds, `observed_model`, request ID, usage, latency, model access,
credentials, and output quality are **not verified**. Preserve the provider's
returned identity separately from `requested_model`; never fill a missing
observed identity from configuration or silently replace an unavailable model.

The $25 per-model budget remains the local ledger limit. Reservations use the
configured input/output prices and are not provider-enforced spending caps.
These simple rates cannot represent every cache-write, service-tier, regional,
tool, tax, or future-price adjustment. Enforce matching provider settings and
billing limits before a paid run; fail closed if the applicable rate is unknown.

The output cap is 8,192 tokens and timeout 120 seconds to leave room for reasoning
and the small JSON result; neither guarantees a successful response. Truncated,
missing, invalid, or mismatched responses remain failures. All validation here
uses the existing local loader with no network calls and no credential values.
