# Dwelly Delivery & Logistics reference review — 2026-10-10

Source snapshot: `/tmp/dwelly-publiccases-Y0GBND/source`, commit `9bcdca585955dfb930005ed742572606e68f5688`.

This is a source-grounded review of all 50 cases, **not a blind independent assessment**. The reviewer previously read the full histories for an ontology audit. For this pass, the reviewer extracted events 001–002, recorded proposed categories, then compared event 003. All 50 cases are already-seen development material, not a held-out benchmark.

Reference recipients and channels below are taken from event 003. Each source is `Delivery & Logistics/NNN/history.md`: visible messages at lines 13 and 23, reference channel at line 29, recipient at line 31, action at line 33. The reference is an example of a suitable next communication, not unique gold wording or proof of an executed API operation.

## Category definitions

- **C — `clarify_customer`**: obtain a customer-side choice, missing details or authorisation.
- **R — `request_evidence`**: obtain measurements, documents or verification records.
- **P — `contact_provider`**: request an operational action, quote, investigation or authorised decision.
- **S — `escalate_specialist`**: transfer a safety or disposition decision to qualified staff.
- **†** marks a materially ambiguous category or a defensible alternative action.

These labels mix purpose and routing, so multiple labels can describe the same safe communication. PA abbreviates Plover Arc Logistics; TG abbreviates Tallowmere Goods.

## All-case review

| Case | Proposed kind | Reference recipient | Reference channel | Major requirement from visible state |
|---|---|---|---|---|
| 001 | C | Vessa Lorne | Customer portal | Obtain selection from offered slots; no invented availability. |
| 002 | C | Tarin Mave | Customer portal | Ask only for missing apartment number; account verification is recorded. |
| 003 | C | Elva Kesh | Call transcript | Verified callback route; no reusable gate code; driver deadline 10:00. |
| 004 | P | Dispatch, PA | Dispatch chat | Use saved verified contact; no promise of exact advance interval. |
| 005 | C | Lira Venn | Customer portal | Named adult household nominee; verify recipient; record before route release. |
| 006 | P | Routing, PA | Email | Chosen available counter; eligibility and recorded choice precede transfer. |
| 007 | P | Sedgeglass Counter supervisor | Email | One two-day extension; before expiry; operator approval and capacity required. |
| 008 | P | Scheduling, PA | Email | Live slot and total-price quote; customer acceptance before change. |
| 009 | C† | Sena Korr | Customer portal | Confirm crew's access checklist; no heavy lifting instruction. |
| 010 | P | Dispatch, PA | Email | Three-day maximum; requested release date is not delivery date. |
| 011 | R† | Destination depot, PA | Depot work queue | Seek physical location/new scan; stale arrival scan is insufficient. |
| 012 | P | Dispatch, PA | Email | Rebook within stated availability; carrier confirms window and charges. |
| 013 | P† | Dispatch review team, PA | Email | Review disputed attempt without presuming customer/driver fault; arrange retry. |
| 014 | C | Rellin Vos, Vellum Rack receiving coordinator | Business portal | Staffed receiving window and entrance, not shop opening hours. |
| 015 | P | Routing control, PA | Email | Correct-depot transfer; distinguish plan from physical receipt. |
| 016 | P† | Locker routing, PA | Email | Customer choice before rerouting; counter option is already known. |
| 017 | P | Notification support, PA | Email | Correct account-linked tracking route; no credential/payment request. |
| 018 | C | Nalo Vere | Call transcript | Authorised recipient chooses before 16:00; carrier must stop return timer. |
| 019 | P† | Dispatch, PA | Email | Suspension/review time without invented restart or delivery estimate. |
| 020 | P | Parcel trace team, PA | Email | Trace DL-020-C; two delivered cartons do not complete three. |
| 021 | R | Lessa Vire | Customer portal | Specified carton/close-up views; approved upload; no unsafe unpacking. |
| 022 | P | Replacement authorisations, TG | Email | Accepted inspection and customer preference; merchant approves replacement. |
| 023 | S | Safety lead, PA | Safety incident queue | Unknown leak: stopped movement, keep clear, qualified safety takeover. |
| 024 | P† | Delivery investigations, PA | Email | Preserve scan/nonreceipt conflict; investigation, not loss/fraud determination. |
| 025 | P | Replacement authorisations, TG | Email | Confirmed loss and chosen remedy do not themselves authorise replacement. |
| 026 | P | Recovery team, PA | Email | Carrier-managed recovery; protect wrong-household details. |
| 027 | P | Misdelivery collections, PA | Email | Collect sealed WP-027 using verified intake; no opening/forwarding; own order separate. |
| 028 | P | Returns authorisations, TG | Email | Accepted SKU mismatch; returns team authorises exchange. |
| 029 | S | Brineleaf Pantry food-safety lead | Email | 9.2 C against merchant's 0–5 C condition; no independent consumption advice. |
| 030 | R† | Secure shipment support, PA | Email | Permitted redacted shipment-specific handover record via verified thread. |
| 031 | P | Return label team, TG | Email | Authorised issuance against RT-031; retain order/shipment linkage. |
| 032 | P | Printer-free returns team, TG | Email | Authorised QR issuance and supported counter/hours; no printer requirement. |
| 033 | P | Collections control, PA | Email | Rebook within availability; actual collection needs custody receipt. |
| 034 | P† | Returns trace team, PA | Email | Merchant physical receipt; depot scan is not merchant acceptance/refund. |
| 035 | P | Refunds team, TG | Email | WH-035 to authorised review team; receiving staff cannot approve refund. |
| 036 | P | Collection planner, PA | Email | All four labelled cartons, dimensions/weights and one manifest. |
| 037 | P† | Specialist returns scheduler, TG | Email | Approved two-person in-home crew for 54 kg item; no customer handling. |
| 038 | P | Reshipment authorisations, TG | Email | Merchant approval, returned/reshippable item, independently verified unchanged destination. |
| 039 | P | Duplicate returns, TG | Email | Merchant authorises original/replacement disposition; no invented duplicate charge. |
| 040 | P | Warehouse dispatch, TG | Warehouse work queue | Recorded cancellation before handover; physical stop; refund separate. |
| 041 | C† | Ossa Rell, Arcloom receiving coordinator | Business portal | Authorised dock appointment/reference/window/entrance before truck dispatch. |
| 042 | P | Freight planner, PA | Email | Appropriate unloading equipment; verified GBP 30 cap; no manual consignee unloading. |
| 043 | R† | Nessa Dray, Orris Span shipping coordinator | Business portal | Measured dimensions including pallet; gross weight including packaging; no guessing. |
| 044 | P | Freight trace team, PA | Email | Trace DL-044-P4; signed three-of-four count does not complete consignment. |
| 045 | R† | Fera Noll, Mavelle Export Studio shipping lead | Email | Shipper supplies broker-requested fields; no invented value/origin. |
| 046 | C† | Mara Vesk, Celand Arc authorised director | Business portal | Independent register; shipment-specific mandate; no impersonation. |
| 047 | R† | Import billing, PA | Email | Operator's itemisation; information request is not payment/waiver authority. |
| 048 | R† | Harbor Thread International transfer team | Email | Actual last-mile receipt and matching reference; clearance/assignment insufficient. |
| 049 | P | Business billing, PA | Email | Verify duplication before credit; unpaid adjustment is not cash refund. |
| 050 | P | Guarantee billing, PA | Email | Reviewed surcharge-only terms; 40-minute delay, GBP 7.50 limit. |

Counts under these definitions: C 9; R 7; P 32; S 2.

## Ambiguities and accepted alternatives

- **009/043:** clarification and evidence acquisition overlap. Either category can describe the same correctly scoped request.
- **011/030/045/047/048:** evidence is obtained by contacting a provider/shipper. Accept R or P unless the taxonomy explicitly separates purpose from addressee.
- **013/024:** provider investigation versus specialist escalation depends on how narrowly S is defined.
- **034:** operational tracing also acquires physical-receipt evidence.
- **037:** booking a specialist service differs from transferring an unresolved safety assessment. A broader definition of S could include it.
- **041/046:** the taxonomy lacks appointment/authorisation requests. C is an imperfect umbrella: these request action, not merely clarification.
- **016:** event 001 already identifies Sedgeglass Counter as available; event 002 asks for the alternative. Directly presenting that option and obtaining the customer's choice is defensible. Reference event 003 routes the offer through the provider.
- **019:** event 001 already supplies an official suspension notice, depot custody and 15:00 review time. A direct factual customer update is defensible. The taxonomy lacks `inform_customer`; do not require unnecessary provider contact solely to match the reference.

## Provenance and evaluation limitations

Reference event 003 calls the order thread verified in **006, 010 and 025**, but events 001–002 do not independently establish that verification. A `Customer portal` channel label alone must not silently become authenticated authority. The pilot may request/use the supplied workflow but should not invent an independent verification finding.

`Recipient` in the index means the **next-action addressee**, not necessarily the shipment consignee. Recipient and channel equality are therefore routing proxies. A proxy match does not establish that a proposed message is factually grounded, safe, authorised, useful or semantically correct. A proxy mismatch does not establish that the proposal is wrong, especially in 016 and 019.

Score action purpose, correct party, source-grounded evidence, authority boundaries, unsupported claims and relevant alternatives separately. Keep semantic correctness `unassessed` unless an explicit semantic review is performed. All reference records are narratives/documents; none proves live connector execution, a completed API mutation, or actual operational fulfilment.
