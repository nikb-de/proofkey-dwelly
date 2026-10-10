# Generator spec: synthetic Delivery & Logistics cases 051–100

Goal: produce cases indistinguishable in format and tone from the public set `DwellyOrg/HackatonPublicCases / Delivery & Logistics / 001–050`. Each case is a folder `0NN/` with exactly two files: `index.md` and `history.md`. No attachments folder.

Read these three public cases before writing anything (format reference, do not copy text):
- `.../Delivery & Logistics/001/` (simple: ask customer to choose)
- `.../Delivery & Logistics/024/` (conflict: register investigation, no finding)
- `.../Delivery & Logistics/042/` (authority limit, business consignee)

The assignment for each case (title, decision type, stage, who the action goes to, channel, boundary, outcome, date) is in `manifest.json`. Follow it exactly. Invent everything else.

## Fixed world

- Carrier: **Plover Arc Logistics**. Teams used in `From`/`To`: Dispatch; Routing; Scheduling; Address desk; Recipient services; Parcel trace team; Delivery investigations; Tracking support; Freight planner; Freight account services; Collections desk; Returns desk; Depot operations; Notification services; Business billing; Compliance queue; Safety incident queue; Operations supervisor queue; Account verification; Route driver <Name>; Furniture delivery team. Write them as `Dispatch, Plover Arc Logistics`, `Route driver Fen Orlo, Plover Arc Logistics`.
- Coordinator (the agent): **Iona Quill, Rivet Delivery Desk**. Always the `To` of events 001 and 002, always the `From` of event 003.
- Pickup points: `<Word> Counter` with a `supervisor` (e.g. `Sedgeglass Counter supervisor`). Merchants and business consignees: invented two-word company names (`Mossline Press`, `Fenwick Spur`).
- People: invented two-word names with no real-world match (pattern like `Vessa Lorne`, `Tarin Mave`, `Oren Sile`). Never reuse a name from the public cases. Never reuse a person's name across your cases.
- Places: invented (`18 Copperfin Court, Merrow Quay`, `7 Sedgeglass Mews`). Fictional geography only. Currency GBP with two decimals.
- Shipment ID: `DL-0NN` where NN is the case number. Case 092 uses `TG-092` as primary task reference with parcels `DL-092-A`, `DL-092-B`, `DL-092-C`.
- All times UTC. Event 001 at `<date> 09:00:00`, event 002 at `09:10:00`, event 003 at `09:25:00`, later events at `09:35`–`10:05` on the same day, or the next day for physical events (arrival, collection, scan). Timestamps strictly increase.
- Channels (exact spelling): `Email`, `Customer portal`, `Business portal`, `Dispatch chat`, `Call transcript`, `Pickup-point portal`, `Depot work queue`, `Freight portal`, `Safety incident queue`. The agent writes to customers via `Customer portal` or `Call transcript`, to business contacts via `Business portal` or `Email`, to carrier teams via `Email` or `Dispatch chat`.

## index.md (exact skeleton; keep every heading and field in this order)

```
# Case 0NN: <Title from manifest>

## Case details

- **Source role:** <Name, role>            e.g. `Vessa Lorne, recipient` or `Dispatch, Plover Arc Logistics`
- **Status:** Completed — specific coordination task only
- **Created:** <date> 09:00:00 UTC
- **Escalated:** <date> 09:10:00 UTC
- **Updated:** <timestamp of the last event>
- **Completed:** <timestamp of the last event>
- **Primary shipment:** DL-0NN            (case 092: `- **Primary task reference:** TG-092`)
- **Coordinator:** Iona Quill, Rivet Delivery Desk
- **Data:** Entirely synthetic; English; fictional geography; all times UTC

## Context

<Two sentences: the state of the shipment and who holds the authority to act.>

## Initial request

<The text of event 002, verbatim.>

## Overview

The escalation snapshot comprises history events 001–002. Event 003 records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

<One imperative sentence, generic, no names: e.g. "Ask the recipient to choose from dispatcher-confirmed alternative slots.">

- **Recipient:** <party the agent addresses in event 003, e.g. `Tarin Mave, recipient` or `Dispatch, Plover Arc Logistics`>
- **Channel:** <channel of event 003>
- **Recorded action:** [History event 003](history.md#event-003)

## Outcome

<One sentence: what was confirmed, and what remains pending.>

## Boundaries and remaining work

<One or two sentences. Must contain an explicit "X is not Y" style limit, e.g. "A booking confirmation is not a completed delivery." Use the boundary from the manifest.>

## History

[Read the complete dated history](history.md).

## Attachments

None. Any documentary record is an explicitly inline excerpt in the history, not a separate file.
```

## history.md (exact skeleton)

```
# Case 0NN history — <Title from manifest>

All identities, records and communications are fictional. Total events: <N>.

<a id="event-001"></a>
## <date> 09:00:00 UTC — event 001

- **Stage:** Context
- **Channel:** <channel>
- **From:** <carrier team or operator>, Plover Arc Logistics
- **To:** Iona Quill, Rivet Delivery Desk

<Text: current state + the rule or policy that applies + what has been verified. 2–4 sentences.>

<a id="event-002"></a>
## <date> 09:10:00 UTC — event 002

- **Stage:** Escalation
- **Channel:** <channel>
- **From:** <requester>
- **To:** Iona Quill, Rivet Delivery Desk

<Text: the request, in the requester's voice. 1–3 sentences. Identical to "Initial request" in index.md.>

<a id="event-003"></a>
## <date> 09:25:00 UTC — event 003

- **Stage:** Agent action
- **Channel:** <channel from manifest action_channel>
- **From:** Iona Quill, Rivet Delivery Desk
- **To:** <party from manifest action_to, with name/team>

<Text: the agent's message. 1–3 sentences. See decision-type rules below.>

<a id="event-004"></a>
## <timestamp> — event 004

- **Stage:** Follow-through / confirmation
- **Channel:** ...
- **From:** ...
- **To:** ...

<Text.>

(optional event 005, same stage)
```

Total events: 4 or 5. Event 001 is always from the carrier side (a team, an operator, a driver) and always contains the policy that makes the decision determinable. Event 002 is the escalation (customer, business contact, dispatch, driver). Event 003 is the agent's single next action. Events 004–005 are confirmations from the parties who actually did something; the last event states explicitly what is confirmed and what is not.

## Style

- British spelling (authorised, organisation). Short declarative sentences. Every sentence carries a fact; no filler, no apologies, no pleasantries.
- Each confirmation names the limit of what it proves: "This is a booking confirmation, not a completed delivery." "Ready for collection is not collected." "Registration is not a finding."
- The agent never claims results it has not received. The agent never performs the action itself; it asks the party that holds the authority. The agent never shares credentials, personal contact details, or data beyond what the task needs, and says so when relevant ("We do not need entry codes").
- The agent uses only verified channels and says so: "in the verified order thread", "on the verified order callback route".
- Numbers only where the scenario needs them (slot times, charges, limits, dimensions). Every amount has GBP and two decimals.
- No em-dashes inside prose. The only em-dashes are in the two fixed strings `Completed — specific coordination task only` and `# Case 0NN history — <Title>` and in the event heading `UTC — event 00N`.
- Do not mention AI, models, agents as software, hackathons, or this spec.

## Decision-type rules for event 003 and the follow-through

- **ASK_CUSTOMER**: event 001 gives the policy and the options or the missing field; event 002 lacks one input (a choice, a field, a confirmation, an action right now). Event 003 asks for exactly that one input and nothing else, naming any restriction. Follow-through: the customer answers; the carrier side records it; the last line states what remains pending.
- **REQUEST_ACTION**: everything needed is present and within the policy in 001. Event 003 asks the owning team or operator to perform the permitted action, restating the key facts and any guard ("notify us only when..."). Follow-through: the team confirms the record changed and what it does not prove.
- **GET_OPTIONS**: availability or price is unknown and only one team can quote. Event 003 asks that team for the options and total charge and says not to change the booking until the customer accepts. Follow-through (two events): the quote reaches the customer in the verified thread; the customer accepts; the team confirms the booking.
- **VERIFY_FIRST**: an earlier request has an unknown outcome (timeout, bounce, portal error, no acknowledgement). Event 003 asks the record owner what its saved state shows and explicitly says not to create a second change until that is known. Follow-through: the state is reported; if absent, one resubmission follows and is confirmed once; if present, no further action.
- **ESCALATE_OPERATOR**: no policy option covers the request, or a human decision is required. Event 003 registers the case with the right queue: facts, sources, the exact question, what is pending. Follow-through: the queue accepts with a reference and a next-update time; nothing is decided; the customer, if told anything, is told only that.
- **WAIT_WITH_DEADLINE**: a required reply is missing. Event 003 is one reminder or chase on the verified channel that states the deadline and the consequence stated in 001; it creates no booking. Follow-through: the reply arrives before the deadline and is recorded, or dispatch records the deadline.
- **DECLINE_EXPLAIN**: the request is outside the policy in 001. Event 003 tells the requester what is not permitted and why (citing the policy, not opinion) and offers the permitted alternative. Follow-through: the requester chooses the alternative or acknowledges; the alternative is recorded; the declined action is never performed.
- **RECORD_STOP**: the requester withdraws or cancels. Event 003 records the stop with the owning team, forbids new actions, and asks what was already executed. Follow-through: the team reports the actual state (nothing changed, or an action already applied and what remains); no reversal is started by the desk.
- **RECORD_REFUSAL**: goods are refused. Event 003 records the refusal with the stated reason and asks for the driver's record; it treats return authorisation as a separate step owned by the merchant or returns desk. Follow-through: refusal recorded; parcel returned to depot or held; return authorisation pending or granted; the last line separates refusal, return and refund.
- **RESOLVE_DUPLICATE**: the same request exists twice. Event 003 links the second to the first and asks for exactly one change. Follow-through: the duplicate is closed; the single change is confirmed.
- **SEPARATE_AUTHORITY**: the requester lacks the authority recorded in 001. Event 003 goes to the authorised party through the verified channel (or tells the requester who must act), without acting on the unauthorised request and without disclosing details to the unauthorised party. Follow-through: the authorised party acts; the record is updated.
- **RECONCILE_CONFLICT**: two sources disagree. Event 003 records both statements, asks the record owner for the evidence or a verification step, and states that neither source is overwritten. Follow-through: the evidence request or scan is registered; the result is reported without a finding beyond what the evidence shows.

## Output

Write the two files directly to `~/dwelly-hackathon/generated-cases/Delivery & Logistics/0NN/`. Create the folder. Do not write anything else. Do not run any script from the public cases repository; only read its files.
