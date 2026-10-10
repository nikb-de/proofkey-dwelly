# Case 032-N4 history — Customer cannot print a return label (Counter scanner rejects the issued token)

All identities, records and communications are fictional. Total events: 7. Events 001–004 are retained from public case 032; events 005–007 are this branch.

<a id="event-001"></a>
## 2026-03-05 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Returns support, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

RT-032 for TG-032, original shipment DL-032, is approved. Our return service supports printer-free QR presentation at Copperfin Returns Counter, 10:00–18:00 UTC. The token must be issued by returns; no customer printer is required.

<a id="event-002"></a>
## 2026-03-05 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Oska Vey, customer
- **To:** Iona Quill, Rivet Delivery Desk

I do not own a printer. Could you arrange the QR return option and tell me which counter accepts it?

<a id="event-003"></a>
## 2026-03-05 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Printer-free returns team, Tallowmere Goods

Please issue the printer-free QR token for approved RT-032 and confirm a supported drop-off counter and its hours.

<a id="event-004"></a>
## 2026-03-05 09:50:00 UTC — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Printer-free returns team, Tallowmere Goods
- **To:** Oska Vey, customer; Iona Quill, Rivet Delivery Desk

Token DL032R is valid for RT-032 in our fictional returns system. [Open the QR return token](attachments/return-qr.png). Copperfin Returns Counter supports it, 10:00–18:00 UTC; staff print the service label after scanning the token. No payment or credential URL is encoded.

<a id="event-005"></a>
## 2026-03-05 10:40:00 UTC — event 005

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Oska Vey, customer
- **To:** Iona Quill, Rivet Delivery Desk

I am at Copperfin Returns Counter now. Staff scanned DL032R and the screen says token not recognised. They say I can leave the parcel without a label and they will sort it out later. Should I?

<a id="event-006"></a>
## 2026-03-05 10:55:00 UTC — event 006

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Printer-free returns team, Tallowmere Goods

The customer is at Copperfin Returns Counter now. Staff scanned token DL032R, which you issued as valid for RT-032, and the screen says token not recognised. Please check the token's saved status and whether Copperfin can accept it. We are telling the customer to keep the parcel meanwhile and are not asking for a new token.

<a id="event-007"></a>
## 2026-03-05 11:20:00 UTC — event 007

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Printer-free returns team, Tallowmere Goods
- **To:** Iona Quill, Rivet Delivery Desk

DL032R is saved as valid for RT-032. Copperfin's scanner had not synced today's tokens; it has been refreshed and now accepts DL032R. The parcel is still with the customer. Acceptance at the counter is not a drop-off, carrier custody or refund.
