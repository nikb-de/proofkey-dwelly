# Public-source research and engineering implications

Checked during this revision, 7–8 October 2026, Europe/London. Sources below are first-party public documentation or company/event descriptions. They establish documented patterns, not credentials, native event capabilities, audited company performance or a working ProofKey implementation. Company descriptions are self-reported. Onfleet, Bringg and Shippo are logistics analogues, not asserted direct Dwelly competitors.

## What Dwelly already describes

Dwelly describes AI processing tenant descriptions and images, consulting property records/landlord instructions, coordinating contractors/access, following up and returning difficult cases to a person. This supports the operational relevance of multimodal evidence and human decisions. That page does not document a Delivery & Logistics API, media-fetch contract or operator-inbox schema. Payment recognition in this account is not refund adjudication. [Dwelly AI operations](https://www.dwelly.group/blog/ai-operations).

The Hall of Fame lists multiple agency brands and regions. This motivates a cross-environment integration hypothesis, but it does not demonstrate incompatible schemas or a common native API. [Dwelly Hall of Fame](https://www.dwelly.group/hall-of-fame).

**Project inference:** another scheduling chatbot would overlap with described operations. ProofKey should instead demonstrate portable authority mapping, reviewed process adaptation, durable actions and clear evidence of what was actually completed. That differentiation is our proposal, not a claim by Dwelly.

## Realistic logistics patterns for offline profiles

| Source | Observed public pattern | Proposed rehearsal use | Not established |
|---|---|---|---|
| Onfleet | Task lifecycle restricts updates; active tasks allow only notes/metadata, completed tasks metadata/custom fields. | Reject a reschedule when lifecycle makes the scheduling operation unavailable. | That a valid customer window permits changing an active task, or that the event uses Onfleet. |
| Bringg order creation | Nested task/order fields and native/external identifiers; documented errors can use HTTP 200 with business `success`/message fields. | Parse business rejection independently of HTTP success; preserve order/customer/inventory binding. | Conditional writes across consent/risk/policy, general exactly-once or event-native endpoints. |
| Bringg return event | Separate original task/delivery and return task identifiers; described failed-delivery return pattern. | Keep original-order binding, refusal and return initiation/readback separate. | A universal refusal/RMA API, post-delivery acceptance policy or physical receipt. |
| Shippo returns | A separate return shipment/label workflow with carrier-specific handling. | Distinguish initiation/label from collection, receipt and refund review. | Refund authority or permission to buy a label; live label creation can carry cost. |

Sources: [Onfleet update task](https://docs.onfleet.com/reference/update-task), [Bringg Create Order (Task)](https://developers.bringg.com/reference/create_task), [Bringg Return Delivery Created](https://developers.bringg.com/reference/return-delivery-created), [Shippo Returns](https://docs.goshippo.com/shipments/returns).

These documents do not establish the composite conditional-write guarantee required by our policy. Simulated atomic version vectors remain **offline contract models**. Capture actual samples/versioned native guarantees before enabling a native effect. More public research cannot substitute for that discovery.

Bringg's `ready_to_execute` descriptions conflict between response/output and request/body sections: the same boolean is associated with opposite planning/driver-visibility states. This is a concrete discovery ambiguity, not a permission to pick the convenient interpretation. A rehearsal can reproduce the ambiguity; native use needs version-specific authoritative samples. [Create Order field descriptions](https://developers.bringg.com/reference/create_task).

### Source locators and retention

| Live-read source in this revision | Locator used for the stated finding | Retained evidence status |
|---|---|---|
| Dwelly AI operations | Tenant request/images, contractor coordination and escalation paragraphs | Dated live read + this paraphrase; no new byte-identical page snapshot in this revision |
| Onfleet update task | Lifecycle restrictions at the endpoint introduction | Dated live read + this paraphrase; native version/sample still required |
| Bringg Create Order | Potential Errors; Response (Output) Params `success` and `ready_to_execute`; Body Params `ready_to_execute` | Dated live read + this paraphrase, including both conflicting sections; not a pinned provider contract |
| Bringg Return Delivery Created | Original/return task and delivery identifier fields | Dated live read + this paraphrase; narrower failed-delivery scope |
| Shippo Returns | Return shipment/label workflow and `is_return` field | Dated live read + this paraphrase; no live transaction |
| Public event / supplied Guide | Public schedule text; local Guide sections 4 and 7 | Live page read plus previously retained local Guide; public page has no new byte snapshot |

This ledger is authored research, not raw capture. A future released source-inspired profile must retain its source observation/capture locator, retrieval time, version where available and capture/sample hash; absence is disclosed rather than inferred. Native capability still needs actual environment evidence, not merely a public page snapshot.

## Event facts and unresolved rule conflict

The Dwelly announcement describes synthetic environments, unseen exceptions, missing context and failures. It confirms the 10 October event and partners, not a published native tool contract. [Dwelly hackathon announcement](https://www.dwelly.group/blog/london-ai-hackathon).

The canonical public event page still describes a 4.5-hour build and video timing that do not resolve the supplied Guide's detailed schedule. The supplied Guide separately mentions source/demo freeze at 16:30 and code/results by 17:00. Conservative preparation is to freeze source/config/prompts/process/demo at 16:30, export only generated unseen results by 17:00 and retain both hashes until organizers clarify. Do not claim the ambiguity is resolved. [Public event page](https://luma.com/ja5x0m76).

The supplied Guide is the detailed local planning reference: `outputs/proofkey_factory_proposal_v2_2_2026-10-07/evidence/rules_2026-10-07/HACKATHON_GUIDE.txt`. It requires public Apache-2.0 code, reproducibility, all case outputs, video, LinkedIn/X requirements and a 2–5-person individually registered team. Its 70% technical / 30% demo split and technical outcome/coverage/safety weights are not replaced by our product priorities. Specific prebuilt eligibility, native workload and the freeze conflict remain unknown. Four 600-second drills are **user targets**, not organizer tests.

## Practical multimodal/backend bet

- Anthropic documents image input and PDF processing; use a provider-neutral extraction/planning protocol, then an initial Anthropic implementation after credential/model/privacy/cost preflight. Documentation support is not a successful image/PDF receipt. [Vision](https://platform.claude.com/docs/en/build-with-claude/vision), [PDF support](https://platform.claude.com/docs/en/build-with-claude/pdf-support).
- ElevenLabs documents speech-to-text; propose actual raw-audio transcription, retaining source hash and processor output. A supplied transcript is a different input class, not an ASR test. Live calls/TTS are not required. [Speech to text](https://elevenlabs.io/docs/overview/capabilities/speech-to-text).
- Exact models, current supported file limits and package pins must be recorded during implementation preflight. Do not adopt example IDs or assume a web subscription provides API credits.

## License boundary

Own new release code is Apache-2.0. The checked Anthropic SDK, ElevenLabs SDK, FastAPI and Pydantic licenses are MIT; OpenTelemetry Python is Apache-2.0. Retain notices and recheck selected pinned dependencies. SDK copyright licensing is separate from hosted service/model and input-data terms. No blanket license is assigned to private evidence, third-party source or organizer materials. [Anthropic SDK license](https://raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/LICENSE), [ElevenLabs SDK](https://github.com/elevenlabs/elevenlabs-python/blob/main/LICENSE), [FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE), [Pydantic](https://github.com/pydantic/pydantic/blob/main/LICENSE), [OpenTelemetry](https://github.com/open-telemetry/opentelemetry-python/blob/main/LICENSE), [Apache license](https://www.apache.org/licenses/LICENSE-2.0).

## Prior team material and capture limits

The current draft also uses redacted local team discussion and captured atlas/meeting-note derivatives in the frozen v2.2 reference archive. They support the original broad delivery/logistics harness direction and exception examples, not verified incident frequencies, financial impact or native API behavior. The atlas's generated case catalogue is not an empirical ranking. Automated meeting-note metrics are not independently verified.

The current fetch of the team atlas was unavailable to the research tool; a prior local redacted capture exists. The shared ChatGPT source was previously unavailable; no missing conversation content is invented. The Granola derivative is captured summary material, not authenticated access to every original recording. The full private transcript was not freshly reread end-to-end in this revision. Historical originals and redacted lineage stay unchanged and outside automatic public release.

## Newly supplied Drive workflow source

On 8 October, seven stored files from the user's linked folder were fetched and copied locally with exact sizes/hashes. START-HERE, all Draw.io labels/transitions and four PNG previews were read; the Figma shortcut was read as a pointer without opening the board. The source declares emulation and unresolved logic defects. It is not an official Dwelly/native contract. See [capture/crosswalk and limitations](drive-workflow-v3.md); original private data is not included in automatic public release. Ten new decisions precede the next plan revision.
