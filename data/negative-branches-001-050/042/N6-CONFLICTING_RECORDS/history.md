# Case 042-N6 history — Warehouse has no forklift for a booked pallet delivery (Booking log shows a heavier pallet)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 042; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-03-15 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Freight portal
- **From:** Freight account services, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Inline verified booking record DL-042: one 280 kg pallet; consignee declares no forklift, level hard-surfaced delivery bay and clear vehicle access. Registered coordinator Voren Tesk has a verified business-portal channel and spending authority for up to GBP 30.00 total additional unloading cost. Consignee staff are not authorised to manually unload the pallet.

<a id="event-002"></a>
## 2026-03-15 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Business portal
- **From:** Voren Tesk, Fenwick Spur receiving coordinator
- **To:** Iona Quill, Rivet Delivery Desk

Our booking account authorises me to accept up to GBP 30.00 total extra service cost. Please arrange the carrier’s suitable option if it fits that limit.

<a id="event-003"></a>
## 2026-03-15 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Freight planner, Plover Arc Logistics

Please arrange an appropriate unloading service for DL-042, one 280 kg pallet at the declared level hard-surfaced bay. No consignee forklift. Verified coordinator Voren authorises up to GBP 30.00 total extra cost.

<a id="event-004"></a>
## 2026-03-15 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Freight planner, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Tail-lift vehicle and trained unloading crew allocated for DL-042 on 2026-03-16, 09:00–12:00 UTC. Total service addition GBP 24.00 under the recorded authority. Driver will assess conditions on arrival; no unloading has occurred.

<a id="event-005"></a>
## 2026-03-15 10:20:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Freight portal
- **From:** Freight account services, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

Booking amendment log DL-042: pallet weight changed from 280 kg to 480 kg at 09:40 UTC by a shipper user. The declared bay conditions are unchanged. No planner review is recorded against the change.

<a id="event-006"></a>
## 2026-03-15 10:35:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Freight portal
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Freight account services, Plover Arc Logistics

The DL-042 amendment log shows the pallet weight changed from 280 kg to 480 kg at 09:40 UTC by a shipper user, while the verified booking record states 280 kg. Which weight is current for DL-042, and what is its source? We are keeping both records on file.

<a id="event-007"></a>
## 2026-03-15 11:20:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Freight portal
- **From:** Freight account services, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

The 480 kg entry was a keying error by the shipper user, who has confirmed 280 kg from its dispatch note. DL-042 now shows 280 kg. The freight planner has re-confirmed the tail-lift and crew allocation for 280 kg. This settles the record weight; it is not a weighing, and no unloading has occurred.
