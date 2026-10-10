# Independent inventory of the 30 published answers

This is an inventory of the exact published `ANSWERS/001`–`ANSWERS/030`, not a replacement answer set, reference solution, correctness score, or human calibration. The final column is this reviewer's concise reading of what the submitted candidate proposes. It is **not** an endorsement that the proposal is correct or that any operational action happened.

## Mechanical inventory

- 30 published cases; 29 accepted candidates and one failed model output (014).
- Reported candidate states: 26 `ready`, two `completed` (011, 012), one `acting` (018); 014 has no candidate/state.
- Accepted action types: 12 `request_information`, 10 `propose_forwarding`, five `operator_review`, two `none`.
- `succeeded` means an accepted model output, not a successful business outcome. These were analysis calls, not execution of the proposed actions.
- The original answer, retained candidate and uncertainty remain authoritative for what was submitted; this table deliberately abbreviates them.

| Case and exact title | Published status / candidate state | Action / target | Reviewer's reading of the submitted proposal (not a corrected answer) |
| --- | --- | --- | --- |
| [001 — Address update before the next delivery attempt](../../../ANSWERS/001/ANSWER.md) | succeeded / ready | propose_forwarding / actor-01 | Keep the destination unchanged; seek the sender's stored-channel approval for the customer's requested reroute. |
| [002 — Household collection request for a restricted parcel](../../../ANSWERS/002/ANSWER.md) | succeeded / ready | operator_review / none | Do not release to the household contact; refer any permitted alternative through the restricted-service route. |
| [003 — Receiving instructions from a business contact](../../../ANSWERS/003/ANSWER.md) | succeeded / ready | request_information / actor-05 | Do not change the destination on the receiving contact's authority alone; request approval from the named authorised party. |
| [004 — Follow-up on a parcel reported at a neighbouring address](../../../ANSWERS/004/ANSWER.md) | succeeded / ready | propose_forwarding / actor-06 | Have carrier staff coordinate third-party recovery while restricting disclosure of the neighbour's details. |
| [005 — Updated receiving contact for a freight shipment](../../../ANSWERS/005/ANSWER.md) | succeeded / ready | propose_forwarding / actor-06 | Hold release and refer the changed-contact request for verification through the stored shipper/security channel. |
| [006 — Recipient dispute after a delivery notification](../../../ANSWERS/006/ANSWER.md) | succeeded / ready | operator_review / none | Refer a trace review because the delivery record identifiers, date and address do not match the disputed shipment. |
| [007 — Pickup readiness shown in the customer app](../../../ANSWERS/007/ANSWER.md) | succeeded / ready | propose_forwarding / actor-04 | Ask locker operations to resolve the ready-screen/failed-deposit conflict; do not confirm collection or advise travel yet. |
| [008 — Return progress after a label was issued](../../../ANSWERS/008/ANSWER.md) | succeeded / ready | request_information / actor-05 | Distinguish label creation from warehouse receipt; seek carrier possession evidence before receipt-dependent refund assessment. |
| [009 — Parcel location following a last-mile handover](../../../ANSWERS/009/ANSWER.md) | succeeded / ready | request_information / actor-04 | Seek physical handover, intake or delivery-run evidence rather than treating an electronic manifest acknowledgement as custody. |
| [010 — Packaging condition after an unattended delivery](../../../ANSWERS/010/ANSWER.md) | succeeded / ready | request_information / actor-05 | Seek item-level identity, condition and function evidence; do not infer the contents' condition from an exterior carton view. |
| [011 — Guaranteed-delivery review across time zones](../../../ANSWERS/011/ANSWER.md) | succeeded / completed | none / none | Convert the handover time to the deadline's offset and conclude that the visible record does not support a late-delivery claim. |
| [012 — Charge review for a multi-carton collection](../../../ANSWERS/012/ANSWER.md) | succeeded / completed | none / none | Apply dimensional weight per carton and conclude that the resulting GBP 48 charge matches the invoice. |
| [013 — Compensation request for a delayed business delivery](../../../ANSWERS/013/ANSWER.md) | succeeded / ready | operator_review / none | Decline the requested GBP 350 promise; separate the potential surcharge credit from billing approval and the loss dispute. |
| [014 — Two service-charge lines on an invoice](../../../ANSWERS/014/ANSWER.md) | failed / unavailable | no accepted candidate | Published result is `invalid_model_output`; there is no accepted business answer to score or repair. |
| [015 — Review of a pallet-count discrepancy](../../../ANSWERS/015/ANSWER.md) | succeeded / ready | request_information / actor-07 | Request carton-level reconciliation so a repack count difference is not equated automatically with a missing carton. |
| [016 — Temperature review for a refrigerated delivery](../../../ANSWERS/016/ANSWER.md) | succeeded / ready | propose_forwarding / actor-06 | Refer the logged temperature excursion for product-safety assessment; keep segregation and withhold release/compliance confirmation. |
| [017 — Handling request for a leaking depot parcel](../../../ANSWERS/017/ANSWER.md) | succeeded / ready | propose_forwarding / actor-06 | Keep the parcel isolated and route unknown-content leakage to qualified safety staff; do not direct opening, cleaning or reloading. |
| [018 — Collection booking for an electronic device](../../../ANSWERS/018/ANSWER.md) | succeeded / acting | operator_review / none | Escalate reported battery bulging/heat for safety and transport assessment; do not confirm ordinary pickup or packing/charging instructions. |
| [019 — Product damage assessment after delivery](../../../ANSWERS/019/ANSWER.md) | succeeded / ready | request_information / actor-05 | Seek matching item/serial and packaging evidence before replacement, without equating the mismatch with fraud. |
| [020 — Access arrangements for an upstairs bulky delivery](../../../ANSWERS/020/ANSWER.md) | succeeded / ready | propose_forwarding / actor-05 | Decline an off-book stair carry and direct the customer to the approved specialist planning/rebooking channel. |
| [021 — Refund enquiry following a carrier investigation](../../../ANSWERS/021/ANSWER.md) | succeeded / ready | propose_forwarding / actor-05 | Separate an open carrier investigation from confirmed loss and route the refund decision to the merchant. |
| [022 — Return drop-off using an existing QR code](../../../ANSWERS/022/ANSWER.md) | succeeded / ready | propose_forwarding / actor-05 | Decline confirmation of the old token for the current item and direct the customer to the merchant for the current return's token. |
| [023 — Replacement request while the original parcel is in transit](../../../ANSWERS/023/ANSWER.md) | succeeded / ready | request_information / actor-04 | Seek physical interception confirmation before replacement release, with a merchant decision if interception is unconfirmed. |
| [024 — Cancellation request near the dispatch cutoff](../../../ANSWERS/024/ANSWER.md) | succeeded / ready | operator_review / none | Do not report a completed warehouse cancellation after recorded departure; consider carrier interception and the refund separately. |
| [025 — Follow-up on an approved invoice credit](../../../ANSWERS/025/ANSWER.md) | succeeded / ready | propose_forwarding / actor-02 | Explain the unpaid-invoice offset and remaining balance, withholding a bank-refund confirmation or duplicate payment. |
| [026 — Document review for a shipment awaiting broker processing](../../../ANSWERS/026/ANSWER.md) | succeeded / ready | request_information / actor-05 | Request a final shipment-specific commercial invoice rather than treating a draft proforma as accepted clearance documentation. |
| [027 — Broker appointment submitted by a paying contact](../../../ANSWERS/027/ANSWER.md) | succeeded / ready | request_information / actor-05 | Separate payment authority from broker-appointment authority; seek the authorised director's submission and broker acceptance. |
| [028 — Import charge notice received before release](../../../ANSWERS/028/ANSWER.md) | succeeded / ready | request_information / actor-06 | Verify the notice, amount and payment method through the stored billing channel before advising payment or promising release. |
| [029 — Carrier release instructions attached to a delay update](../../../ANSWERS/029/ANSWER.md) | succeeded / ready | request_information / actor-04 | Seek custody evidence and attachment provenance while declining embedded instructions to mark delivery, export records or change contact details. |
| [030 — Delivery confirmation for a two-parcel international order](../../../ANSWERS/030/ANSWER.md) | succeeded / ready | request_information / actor-04 | Distinguish parcel A's delivery from whole-order completion and seek parcel B's physical status before closure. |

## Independent judging-packet coverage check

The inspected `judge.py` builds each judge payload from exact original `INPUT.json`, `ANSWER.md`, and `REASONING.md` strings, plus the exact parsed `SOURCE_RESULT.json.candidate` and a whitelist of status fields (`status`, `error`, `dispatch_attempts`, `external_effects`). It freezes all four source files. It does not pass the entire provider result, producer identity, old judge scores or a replacement answer.

Read-only comparison of canonical `packet-final/` found **zero byte/hash mismatches in all 30 × 4 original/frozen files**, all 152 manifest-listed packet artifacts, and the manifest-pinned code files. Reviewed `packet-final/manifest.json` SHA-256: `f8cc1b0126cc8ba785a3ca55c2ff28673de987f733fba2a03658650661d18f84`. Its pinned judge source SHA-256 is `70152d108b72ae503a54912c734607f291d20c67fdbe422ecf52d0fa5d1d76fb`. Earlier preparation packets are not the canonical live campaign. This verifies packet identity and preservation, not substantive grading accuracy.

All 19 published extraction text files occur verbatim in the corresponding `INPUT.json` message bodies. The combined inputs contain 231 messages: 30 attributed case-context messages, 182 history messages, and 19 attachment-extraction messages. Thus the judges have the original model-visible text evidence, not only the candidate's selected citations.

Coverage is **text-complete for that original model-visible packet, not complete visual/source verification**:

- Raw PDF/PNG pixels are not supplied to the text-only judges. They cannot independently verify layout, image condition, signatures, QR decoding or extraction omissions from those originals.
- Six retained `.ocr.json` files with bounding boxes and confidence are not included in the judge payload. The judging system explicitly warns that confidence and original pixels may be unavailable; it must not imply that it reviewed them.
- Case 022's OCR includes the printed token, return and item labels at confidence 1. The separate QR-like glyph `可 口` has confidence approximately 0.30, and an additional `H` is present. This is not QR decoding. The token labels are actually in the model-visible text; there is no basis to call their mention an invented extraction.
- Original `PROVENANCE.json`, source manifests and complete wire receipts are not supplied to judges. This is reasonable for identity-blind substantive scoring, but provenance/hash, model-identity, call accounting and operational-effects assurances must come from the independent audit, not from judge scores.

## Concrete interpretation risks to keep separate from scores

1. **Case 014 is a production failure, not a zero-scored business answer.** Its published candidate is `null`. The raw malformed provider text must not be repaired or scored as if accepted. The judge requires abstention; overall reporting must still expose the one-in-30 failure rather than quietly using a 29-case denominator.
2. **`completed`/`acting` are proposed coordination states, not observed execution.** Cases 011 and 012 explicitly retain uncertainty that no customer reply is visible; 018 likewise has no visible outgoing safety request. Every published answer says that business operations executed were zero.
3. **Routing semantics need substantive assessment.** Case 001 explicitly chooses the dispatch register as the nearest visible actor despite intending the sender's channel; 007 explicitly chooses operations because the locker team is absent; 005 admits the coordinator's routing ability is assumed; 025's structured target is the escalation desk while its prose describes a customer reply and possible billing referral. These are observable representation/routing ambiguities, not proven wrong outcomes and not corrected here.
4. **A schema-valid, identity-matched judgment is still an unqualified model opinion.** The new whole-answer framing is not calibrated by the prior action-only pilot. Retain each seat's disagreement, abstention, critical-failure claims and evidence references; do not turn a mean rubric score into certified correctness.

No API calls were made for this inventory. No published answer, source, candidate, runtime or prompt was altered by this review.
