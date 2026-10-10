# Case 002-N4-A1-LONG history — Pending address readback after an extended intake history

All identities, records and communications are fictional. This independent training case ends at the decision cutoff; subsequent parent events are excluded.

<a id="event-001"></a>
## 2026-02-03 08:48:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Address import.
The intake record for DL-002 stores 18 Copperfin Court, Merrow Quay as the street and building destination. The imported address has a separate field for an apartment, but that field is empty. The building name and street text are kept in their original order rather than split into a different destination. This record documents the incoming address fields for the parcel; it contains no new instructions from the recipient. The text copied from the order does not include a floor, apartment, or unit suffix. The import log is retained with the order so the address desk can trace how the original destination entered the system.

<a id="event-002"></a>
## 2026-02-03 08:49:00 UTC — event 002

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Building record.
The building directory identifies Copperfin Court as a property with multiple apartments sharing the street entrance. Its address entry describes the building as a whole and does not identify which apartment belongs to the recipient of DL-002. A building-level directory match therefore leaves the apartment field unresolved. The directory extract is stored as supporting context for the same address record, with the street and town written as they appear on the order. The extract contains no apartment allocation for this parcel and no statement from the recipient. Its purpose in the record is to explain why the street address alone does not identify the final unit.

<a id="event-003"></a>
## 2026-02-03 08:50:00 UTC — event 003

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Label rendering.
The label preview for DL-002 renders the street and building lines from the imported destination. Its layout includes space for an apartment line, which is blank in this preview. The preview is a representation of the imported text, not an additional source of destination details. Line wrapping leaves the building name together and prints Merrow Quay on the locality line. No apartment number was inferred during formatting. The label-rendering entry is retained alongside the import record so the address desk can compare the displayed address against the underlying fields. This entry documents the layout only; it does not record a recipient response or an address correction.

<a id="event-004"></a>
## 2026-02-03 08:51:00 UTC — event 004

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Order-field comparison.
The order-field comparison for DL-002 shows that the street and building text in the label preview agrees with the imported order. The apartment field is empty in both views. The comparison covers the written address fields and does not link the recipient to an apartment in the building directory. No replacement address is proposed in this record. The purpose of the comparison is to distinguish a formatting difference from information that was absent at intake. For this order, the displayed lines preserve the supplied building destination, while the unit detail remains unsupplied. The comparison is retained as background for the incomplete-address investigation.

<a id="event-005"></a>
## 2026-02-03 08:52:00 UTC — event 005

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Address queue entry.
The address queue lists DL-002 under incomplete address because a multiple-apartment building is specified without an apartment number. The queue description repeats the street and building from the order and leaves the apartment field empty. It does not provide a candidate unit for the address desk to adopt. This queue entry describes the intake issue rather than a later resolution. The attached text is limited to address completeness: it contains no revised booking, delivery confirmation, or new recipient instruction. Keeping the entry with the order allows a coordinator reviewing the correspondence to identify what information was absent when the address issue was first recorded.

<a id="event-006"></a>
## 2026-02-03 08:53:00 UTC — event 006

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Parcel reference.
The intake paperwork uses DL-002 as the parcel reference throughout the address records. The reference connects the imported destination, label preview, building-directory extract, and incomplete-address queue entry to the same parcel. It is not an apartment identifier and should not be parsed as one. This background entry exists because several administrative documents appear in the case record with different document titles. Each title describes the type of record rather than a different delivery. The paperwork contains no recipient-supplied unit detail. The parcel-reference entry describes how the records are associated and provides no evidence that an address change has been submitted or saved.

<a id="event-007"></a>
## 2026-02-03 08:54:00 UTC — event 007

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Street-text check.
The address intake check retains Copperfin Court in the street-and-building text and Merrow Quay in the locality field. The check does not replace either value with a different destination. Its scope is the text already supplied with DL-002, including the ordering of the written address lines. It records no apartment-number lookup and no conversation with the recipient. The intake note explains that a complete street line and locality can coexist with an empty apartment field in the same address record. This note is kept with the address-desk paperwork to document the original field structure, rather than to establish that the incomplete-address issue has been resolved.

<a id="event-008"></a>
## 2026-02-03 08:55:00 UTC — event 008

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Apartment-field provenance.
The apartment field in the DL-002 intake record has no source value. The imported order, label preview, and building-level directory extract do not fill that field. The provenance record distinguishes a blank input from a value that was supplied and subsequently removed. In this case, the archived intake documents show an unsupplied unit detail. No guessed number is stored as a substitute. The record describes the state of the original address fields at intake; it is separate from later correspondence. It includes no recipient consent, no requested correction, and no response from an address correction form.

<a id="event-009"></a>
## 2026-02-03 08:56:00 UTC — event 009

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Building-level match.
The building-level match for DL-002 connects the written destination to the Copperfin Court directory entry in Merrow Quay. The matching result stops at the building level. The directory represents multiple apartments under that building address and provides no parcel-specific link to one apartment. The archived result is useful context for understanding why the address desk has an incomplete-address item despite a recognized street destination. It does not expand the destination to a unit and does not certify that the parcel can be delivered to an unspecified apartment. This record describes a reference-data match, with no new information about recipient instructions or the outcome of an address correction.

<a id="event-010"></a>
## 2026-02-03 08:57:00 UTC — event 010

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Record bundle inventory.
The archived address bundle for DL-002 contains the imported order address, a label-layout preview, a building-directory extract, and an intake comparison of those fields. These records all describe the original street-and-building destination. None contains an apartment value supplied by the recipient. The inventory lists the administrative documents in the bundle so a reviewer can understand why several records refer to the same incomplete address. The existence of several documents does not create additional apartment information. This inventory is a description of the intake bundle only; it has no correction reference, recipient message, or saved-address readback to report.

<a id="event-011"></a>
## 2026-02-03 08:58:00 UTC — event 011

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Display-field review.
The display-field review for DL-002 checks the address as it appears in the intake paperwork. The street and building lines are visible, while the apartment line is absent because its source field is blank. This review does not alter the stored address and does not propose a replacement destination. Its scope is whether the paperwork faithfully displays the originally supplied fields. The review notes that an empty unit field may be omitted from a rendered label even though it remains a separate field in the order record. The archived review supplies background about the display, without adding any apartment number or resolving the address issue.

<a id="event-012"></a>
## 2026-02-03 08:59:00 UTC — event 012

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Archived intake note — Intake bundle handover.
The intake address bundle for DL-002 is retained for the address desk with the street, building, locality, and blank apartment field preserved. The bundle explains the original incomplete-address item through the import record and the building-level directory match. It contains no later recipient clarification. The handover text describes what is in the intake bundle so correspondence can be interpreted against the original fields. Its contents should be understood as historical records of intake, rather than a readback after an address correction. This final archive entry supplies no new destination details and records no successful change or clearance of the address hold.

<a id="event-013"></a>
## 2026-02-03 09:00:00 UTC — event 013

- **Stage:** Context
- **Channel:** Email
- **From:** Address desk, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-002: 18 Copperfin Court, Merrow Quay. The building has multiple apartments; the order has no apartment number. Hold reason: incomplete address. The recipient’s order-linked portal session was verified by our account team.

<a id="event-014"></a>
## 2026-02-03 09:10:00 UTC — event 014

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Tarin Mave, recipient
- **To:** Iona Quill, Rivet Delivery Desk

The tracking page says address clarification required. The building is correct; what do you need from me?

<a id="event-015"></a>
## 2026-02-03 09:25:00 UTC — event 015

- **Stage:** Agent action
- **Channel:** Customer portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Tarin Mave, recipient

Please confirm the apartment number at 18 Copperfin Court. We do not need entry codes or any other household details.

<a id="event-016"></a>
## 2026-02-03 09:50:00 UTC — event 016

- **Stage:** Follow-through / confirmation
- **Channel:** Customer portal
- **From:** Tarin Mave, recipient
- **To:** Iona Quill, Rivet Delivery Desk

Apartment 4B. Please add that to DL-002; the street and building remain unchanged.

<a id="event-017"></a>
## 2026-02-03 09:57:00 UTC — event 017

- **Stage:** Escalation
- **Channel:** Email
- **From:** Address desk correction form, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Automatic response. Your address correction for DL-002, Apartment 4B, submitted at 09:54, ended with 'Session expired'. The form may have saved before the session closed. No correction reference was issued.

<a id="event-018"></a>
## 2026-02-03 10:12:00 UTC — event 018

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Address desk, Plover Arc Logistics

Our address correction for DL-002, Apartment 4B, submitted at 09:54, ended with 'Session expired' and no reference was issued. What do DL-002's saved address and hold status show now? Please do not create a second change. We will not resubmit the correction until we know.
