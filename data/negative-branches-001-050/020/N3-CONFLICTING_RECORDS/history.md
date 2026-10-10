# Case 020-N3 history — A multi-parcel order arrives with one parcel still outstanding (Delivery scan but carton not received)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 020; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-02-21 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Parcel support, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Order TG-020 has parcels DL-020-A, DL-020-B and DL-020-C. A and B have delivery scans; C has an inbound depot scan only. All three are required to complete the order.

<a id="event-002"></a>
## 2026-02-21 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Eris Kael, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I received two of the three cartons for TG-020. The missing carton is DL-020-C. Please locate it; I am available tomorrow.

<a id="event-003"></a>
## 2026-02-21 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Parcel trace team, Plover Arc Logistics

Please trace DL-020-C specifically and arrange its remaining delivery. Do not mark TG-020 complete using only the A and B scans.

<a id="event-004"></a>
## 2026-02-21 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Parcel trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-020-C was in the oversize rack and is now on the 2026-02-22 route. Its route handover scan will be reported separately.

<a id="event-005"></a>
## 2026-02-22 11:10:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Eris Kael, recipient
- **To:** Iona Quill, Rivet Delivery Desk

The tracker says DL-020-C was delivered at 10:55 UTC today. I have been home all morning and I still have only two cartons, A and B.

<a id="event-006"></a>
## 2026-02-22 11:25:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Parcel trace team, Plover Arc Logistics

DL-020-C shows a delivery scan at 10:55 UTC today, but Eris Kael says she has been home all morning and has only cartons A and B. We are keeping both records and TG-020 stays open. Please send the evidence behind that scan, including the handover location and the driver's record.

<a id="event-007"></a>
## 2026-02-22 12:20:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Parcel trace team, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Evidence for the 10:55 UTC scan of DL-020-C: the handset location is two streets from Eris's address, with no signature or photo. The driver's record notes 'left with neighbour' without a name. This clarifies the record, not where the carton is. TG-020 stays at two of three cartons.
