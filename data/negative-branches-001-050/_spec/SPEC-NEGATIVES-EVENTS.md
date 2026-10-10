# Addendum: agent and follow-through events for each negative branch

Each branch in `negatives/0NN.json` will become its own case folder in the public format (`index.md` + `history.md`): the recorded public events up to `insert_after`, then the branch's `new_event` (the new escalation), then **the coordinator's action** and **one confirmation**. The last two do not exist yet. Add them to every negative, in place, as two new keys. Change nothing else in the file.

```json
"agent_event": {
  "channel": "Customer portal",
  "to": "Vessa Lorne, recipient",
  "text": "<the message Iona Quill actually sends, 15-90 words>"
},
"followup_event": {
  "timestamp": "2026-02-02 10:40:00 UTC",
  "channel": "Email",
  "from": "Dispatch, Plover Arc Logistics",
  "to": "Iona Quill, Rivet Delivery Desk",
  "text": "<the reply or record that closes the branch, 15-90 words>"
}
```

Rules:

- `agent_event.to` is the addressee named in `expected_action`, written as in the public histories (`Vessa Lorne, recipient`, `Dispatch, Plover Arc Logistics`, `Sedgeglass Counter supervisor`). `agent_event.channel` matches: customers via `Customer portal` or `Call transcript`; business contacts via `Business portal` or `Email`; carrier teams via `Email` or `Dispatch chat`; pickup points via `Email` or `Pickup-point portal`.
- `agent_event.text` is the message itself, first person plural as in the public event 003 texts ("Please check...", "Which should I ask them to book?"). It does exactly what `expected_action` says and nothing `must_not` forbids: one question when asking; the policy cited when declining; "do not create a second change" when verifying; facts, sources and the exact question when escalating; the deadline and consequence when reminding. It claims no result.
- The agent event's timestamp is set by the build script to `new_event.timestamp + 15 minutes`. `followup_event.timestamp` must be later than that, on the same or the next day.
- `followup_event` comes from the party that can confirm the state in `done_means` (usually the addressee, sometimes the record owner). Its text states what is now confirmed and what it still does not prove, in the register of the public confirmations ("This is a booking record, not a delivery."). For NO_REPLY branches the follow-through may be dispatch recording the deadline, or the late reply arriving before it.
- British spelling, short factual sentences, no em-dashes, no mention of AI, models or the hackathon. Amounts in GBP with two decimals.

Write the updated JSON back to the same path. Re-open it afterwards and confirm it parses and that every negative has both keys.
