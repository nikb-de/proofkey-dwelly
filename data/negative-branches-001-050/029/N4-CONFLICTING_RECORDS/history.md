# Case 029-N4 history — Refrigerated food arrives outside the merchant's documented temperature conditions (Van log contradicts merchant logger)

All identities, records and communications are fictional. Total events: 6. Events 001–003 are retained from public case 029; events 004–006 are this branch.

<a id="event-001"></a>
## 2026-03-02 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** Email
- **From:** Brineleaf Pantry food-safety intake
- **To:** Iona Quill, Rivet Delivery Desk

Order BP-029 / DL-029 uses our documented chilled-delivery range of 0–5 °C at handover. Inline logger excerpt: sensor BL-29, handover capture 2026-03-02 08:50 UTC, 9.2 °C. This is outside our range; only food-safety staff may authorise disposition.

<a id="event-002"></a>
## 2026-03-02 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** Customer portal
- **From:** Enna Vosk, recipient
- **To:** Iona Quill, Rivet Delivery Desk

I have not eaten anything from this box. The logger shows 9.2 °C. Please get the merchant to tell me what to do and whether they will replace it.

<a id="event-003"></a>
## 2026-03-02 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Brineleaf Pantry food-safety lead

Please assess BP-029 using the recorded 9.2 °C handover reading against your 0–5 °C order condition. The customer has not consumed the contents. Please issue your disposition and order-specific remedy; I am not advising consumption.

<a id="event-004"></a>
## 2026-03-02 09:45:00 UTC — event 004

- **Stage:** Escalation
- **Channel:** Email
- **From:** Dispatch, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

For DL-029, our van chiller log shows 3.8 °C at the 08:50 UTC handover stop. We hold no record of the merchant's BL-29 sensor reading. Please note our log before any carrier fault is assumed.

<a id="event-005"></a>
## 2026-03-02 10:00:00 UTC — event 005

- **Stage:** Agent action
- **Channel:** Email
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** Brineleaf Pantry food-safety lead

For BP-029 / DL-029: Plover Arc Logistics dispatch reports a van chiller log of 3.8 °C at the 08:50 UTC handover stop and holds no record of your BL-29 reading of 9.2 °C. We are keeping both readings on record and making no finding. Please confirm you hold both for your assessment.

<a id="event-006"></a>
## 2026-03-02 10:25:00 UTC — event 006

- **Stage:** Follow-through / confirmation
- **Channel:** Email
- **From:** Brineleaf Pantry food-safety lead
- **To:** Iona Quill, Rivet Delivery Desk

We now hold both readings for BP-029: sensor BL-29 at 9.2 °C and the carrier's van chiller log at 3.8 °C, both at 08:50 UTC. Holding both decides neither the disposition nor who is at fault. Our disposition will follow separately.
