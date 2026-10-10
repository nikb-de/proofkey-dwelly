# Case 099 history — Depot weight differs from the merchant manifest for the same parcel

All identities, records and communications are fictional. Total events: 5.

<a id="event-001"></a>
## 2026-05-11 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Routing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-099 is held from routing. The Quillmarsh Ceramics manifest lists it at 4.20 kg; the depot inbound scale recorded 5.05 kg at 2026-05-11 06:50 UTC. Rule: a variance above 0.50 kg holds the parcel until Depot operations records a verification scan, and neither weight entry is edited.

<a id="event-002"></a>
## 2026-05-11 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Depot work queue
- **From:** Depot operations, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

DL-099 is on our hold shelf. Can we overwrite the scale weight with the manifest figure so it makes the next route, or should we treat it as a possible wrong parcel?

<a id="event-003"></a>
## 2026-05-11 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Depot operations, Plover Arc Logistics

Please keep both weights on DL-099: manifest 4.20 kg and inbound scale 5.05 kg. Record a verification scan: re-weigh on a calibrated scale, check the label and barcode against the manifest, and note the packaging; do not overwrite either figure or assume tampering or a wrong parcel.

<a id="event-004"></a>
## 2026-05-11 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Depot operations, Plover Arc Logistics
- **To:** Routing, Plover Arc Logistics; Iona Quill, Rivet Delivery Desk

Verification scan VS-099 recorded at 09:44 UTC. Label and barcode match DL-099 and the manifest; the outer seal is intact. Calibrated re-weigh: 5.05 kg. The parcel is in a double-wall outer carton whose packing label reads net 4.20 kg, gross 5.05 kg.

<a id="event-005"></a>
## 2026-05-11 10:05:00 UTC — event 005

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Routing, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

VS-099 shows the manifest gave net weight and the depot scale measured gross weight; the 0.85 kg difference is packaging. Both entries remain on the record with VS-099 linked. DL-099 is released to routing for 2026-05-12. Release to routing is not a delivery, and no charge has been adjusted.
