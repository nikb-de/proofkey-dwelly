# Negative branches for public cases 001–050

For each organisers' public case 001–050: the situation at escalation, the recorded next action, and 4–6 **alternative continuations where something goes wrong**, each with the decision the coordinator should take. The public histories all end well; these branches are the test points for the hard sheets of the v5 workflow (R unknown result, B waiting, D refusal, F stop and duplicates, E operator, A authority and conflicts).

Kept in its own folder so it never mixes with the organisers' data in `../dwelly-public-cases/`. The organisers' text is not copied here; each branch references the public case by number and adds only the new event.

## Shape of one branch

A branch is a new event inserted after a recorded one (`insert_after`: 002, 003 or 004). Everything before it stays as recorded in the public history. Fields:

| Field | Meaning |
|---|---|
| `failure_mode` | one of 12 codes (below) |
| `new_event` | timestamp, channel, from, to, text of the inserted event |
| `expected_decision` | one of the 12 decision types used in `../synthetic-cases-051-100/` |
| `sheet` | the v5 workflow sheet the branch exercises |
| `expected_action` | who the coordinator addresses, through which channel, asking what |
| `must_not` | the tempting wrong move in that branch |
| `done_means` | the confirmation that closes the branch and what it still does not prove |

## Failure-mode codes

| Code | What goes wrong |
|---|---|
| NO_REPLY | the party asked does not answer; a deadline or consequence exists |
| AMBIGUOUS_REPLY | the reply does not answer the question, answers partially, or picks an option not offered |
| UNAUTHORISED_REPLY | the reply or a new instruction comes from someone not authorised or via an unverified channel |
| CHANNEL_FAILURE | the coordinator's request bounced, timed out, errored or was never acknowledged |
| STALE_STATE | between request and execution the state changed: slot taken, parcel departed, window expired |
| CUSTOMER_CANCELS | the requester withdraws or asks to stop while the action is pending or just done |
| DUPLICATE_REQUEST | the same request arrives again by another channel |
| CONFLICTING_RECORDS | a confirmation contradicts another record or the customer |
| OUT_OF_POLICY_ASK | the reply contains a new request the policy forbids |
| PHYSICAL_FAILURE | the physical step fails: driver cannot reach, damage, refused at door, wrong item |
| NEEDS_HUMAN | the team cannot act without a supervisor, or a safety, compliance or identity issue appears |
| SNAPSHOT_CONFLICT | inside events 001–002 themselves: request contradicts context, identity unverified, policy does not cover it (inserted after 002) |

## Files

| Path | Content |
|---|---|
| `negatives/0NN.json` | source of truth, one file per public case |
| `negatives/0NN.md` | readable rendering |
| `negatives/README.md` | index and totals per failure mode, decision and sheet (generated) |
| `_spec/SPEC-NEGATIVES.md` | the generator specification and rules |
| `_spec/negatives_tool.py` | validation and rendering |

## Decision point for testing

Give the system the recorded public events up to and including `insert_after`, then the `new_event`, hide everything else, and compare its proposal with `expected_decision`, `expected_action`, `must_not` and `done_means`.

## Check

```sh
cd _spec
python3 negatives_tool.py --public "<path to HackatonPublicCases>/Delivery & Logistics"
```

Validates every JSON, renders the `.md` files and `negatives/README.md`, exits non-zero on any error.
