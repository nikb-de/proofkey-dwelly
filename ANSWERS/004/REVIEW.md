# Human review correction — 004

This is a post-run proposed correction, not output of the frozen submitted system. The [original answer](ANSWER.md), [retained response/candidate](SOURCE_RESULT.json) and source records remain available. No customer message, routing change, refund or carrier action was executed.

Recovery can be opened (E05), but there is no recorded opening. A proposed customer reply must preserve that distinction.

## Corrected proposal

```json
{
  "state": "ready",
  "waiting_for": [],
  "next_action": {
    "type": "propose_forwarding",
    "target_actor_id": "actor-06",
    "description": "Propose opening recovery coordination via recovery@vellora.example using token NB-04 through the carrier liaison. Tell Orin only that recovery coordination is being requested; do not say it has started until an actual opening is recorded. Do not share neighbour contact details or unrestricted handover records."
  },
  "evidence_event_ids": [
    "E02",
    "E03",
    "E04",
    "E05",
    "E06"
  ],
  "uncertainty": [
    "No permission to share third-party contact details or unrestricted handover records with Orin is recorded; E02 and E05 indicate separate permission is needed.",
    "No outgoing request to the carrier liaison or recovery contact is visible, so it is unknown whether recovery has been opened.",
    "Delivery to the neighbouring address is only reported; physical recovery of the parcel is not confirmed.",
    "Actor identities and authority are source-declared and unverified.",
    "The restricted carrier record contents are not in the packet; only the minimised excerpt is available."
  ]
}
```
