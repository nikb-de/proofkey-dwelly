# Official-input model harness

Runs the existing submitted coordination model contract against separately supplied official cases. This is a direct model runner, not a claim that the whole UI or operational platform was exercised. No business actions are executed. Inputs are held out; this tool has no grading oracle or prompt-tuning loop.

The 10 October 2026 primary run selects `anthropic-claude-sonnet-5-5`, with explicit high effort, before dispatch. Its frozen campaign is `/tmp/proofkey-reality-campaign-20261010`; official input source commit is `ce84e8c0d8f7f8ddacd8d8fcfe53516c22885db7`, and submitted application commit is `fd8533297d259f4a997710045852e4eb2f3ef771`. The manifest freezes all 30 inputs, 79 source files, the selected profile settings, exact prompts and runner/provider code hashes.

The existing baseline prompt SHA-256 is `61592fb429180e7da972a572ffc17e0379944c8bd7f2a84f049f725e510cbf80`. Its only difference from the submitted platform system string is a trailing newline: they match after trimming, and the newline is preserved in the effective request. The baseline is not rewritten for the official cases.

Prepare a fresh immutable campaign after attachment extraction completes:

```sh
python -B -m tools.dwelly_reality prepare \
  --source '/tmp/proofkey-reality-inputs.3DEw1Q/Delivery & Logistics' \
  --sidecars /tmp/proofkey-reality-sidecars \
  --output /tmp/proofkey-reality-campaign-20261010 \
  --system-file '/Users/nbk/Documents/Pitch project/outputs/llm-prompt-tuning-2026-10-10/frozen-v2/prompt-baseline.txt' \
  --effort high
```

That directory must not already exist; the command documents how the frozen campaign was prepared and must not be repeated over it. Use a different directory for a separately authorized future campaign. Omit system-file and effort to use the submitted platform defaults. The explicit baseline is copied byte for byte; its semantic equality after trimming to the submitted system is recorded. The input adapter retains source evidence, validates the existing widget contract, and uses existing `model.prepare` serialization. Source-declared actors retain distinct IDs, original names, attributed messages and E01-style evidence IDs. Known-at-desk timestamps and decision time exclude later events.

Attachment extraction is a separate, zero-model-call step documented in [the extraction guide](../dwelly_evidence_extract/README.md). This run used Poppler text extraction for 13 PDFs and native Apple Vision OCR for six PNGs. All 19 are marked `extracted_unverified`; original attachments, text sidecars, OCR bounding boxes/confidence and the extraction manifest are retained. The copied extraction manifest SHA-256 is `d77419be122210880bc7f0fca9958ccdb45d031a15a351ae0067402d2271e542`. These are source derivatives, not authenticated records or visual scene descriptions. Case 022 contains a low-confidence OCR line; no barcode or graphical meaning was inferred. Attachment derivatives remain untrusted evidence with hashes and source-event links.

Run only after approving external model calls:

```sh
python -B -m tools.dwelly_reality run --prepared /tmp/proofkey-reality-campaign-20261010 \
  --profile anthropic-claude-sonnet-5-5 --live \
  --provider-env-file /absolute/private/provider.env \
  --concurrency 3 --cap-usd 25 --deadline-seconds 900
```

The current profile configuration is explicitly frozen during preparation. High effort adds Anthropic adaptive thinking/output_config.effort, or OpenAI reasoning.effort, at the transport boundary. Exact effective JSON bodies are retained without authorization headers. The existing provider parser and model.parse validate responses. A shared durable budget ledger reserves before per-call intent and dispatch; errors retain reservations. An existing intent or reservation is never retried. A crash after intent is an unknown outcome, not a reason to send another call. Queue entries whose deadline expires never dispatch. No provider or prompt substitution occurs.

The initial conservative reservation for 30 Claude calls is USD 2.891794, with a maximum USD 0.099112 per call, within the configured USD 25 per-provider/model cap. Usage and requested/observed provider identities remain in the receipts; reservations are not an invoice or a claim that the provider billed precisely that amount.

`--profile` can be repeated for explicitly approved secondary runs. Each profile has separate preserved records. One process has at most three active calls. The $25 limit is per provider/model in this campaign under configured rates, not an invoice or provider billing cap. Keep campaign directories private: source text, model responses, wire bodies and provider identifiers are retained; known credential values are redacted.

Export the selected primary profile into a fresh official directory:

```sh
python -B -m tools.dwelly_reality export --prepared /tmp/proofkey-reality-campaign-20261010 \
  --profile anthropic-claude-sonnet-5-5 --output /absolute/new/ANSWERS
```

Every input case receives ANSWER.md and REASONING.md, including failed/missing cases. Output is templated only from actual retained candidates, public evidence references and uncertainty. The model contract has no rationale field; this tool does not reconstruct hidden reasoning. Original sources, exact input, full result, wire trace and intent are copied with provenance. It never replaces failed primary results with a secondary model's answer.

The accepted model schema contains only coordination state, waiting targets, one proposed next action, visible evidence references and uncertainty. A successful parse proves conformity to that schema, not the correctness of the decision. ANSWER.md displays the exact proposed action and actual dispatch count separately from business activity. Rescheduling, refusal/return, customer contact and operator escalation remain proposals: this runner performs no courier, booking, return, messaging or payment operation. Physical delivery is never inferred. Failed and incomplete responses remain failures in the exported files.

Verification: `python -B -m unittest discover -s tools/dwelly_reality/tests -v`. Network tests use replaced transport boundaries and are not live provider evidence.
