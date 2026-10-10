# Negative branches for public cases 001–050

For each organisers' public case 001–050: 4–6 **alternative continuations where something goes wrong**, each written as its own case folder in the public format. The public histories all end well; these branches are the test points for the hard sheets of the v5 workflow (R unknown result, B waiting, D refusal, F stop and duplicates, E operator, A authority and conflicts).

Kept in its own folder so it never mixes with the organisers' data in `../dwelly-public-cases/`.

## Layout

```text
001/
  N1-AMBIGUOUS_REPLY/
    index.md
    history.md
  N2-STALE_STATE/
  N3-CHANNEL_FAILURE/
  ...
002/
  ...
index.csv            one row per branch: case, branch id, folder, failure mode, expected decision, sheet, insert point, label
_source/0NN.json     the branches as data (source of truth for the folders)
_spec/               specification, validator, builder
```

## What one branch folder contains

`history.md`: the public case's events 001–00K retained verbatim (K is the insert point: 002, 003 or 004), then three new events: the branch's new escalation (what went wrong), the coordinator's action, and one confirmation that closes the branch. `index.md`: the same sections as a public case, plus two extra lines: `Derived from` (which public case and how many events are retained) and `Expected decision` (one of twelve decision codes and the v5 sheet). `Boundaries and remaining work` names the tempting wrong move for that branch.

Decision point for testing: give the system events 001 to 00(K+1) only, hide the rest, and compare its proposal with the recorded agent action on who it addresses, through which channel, what it asks, and what it claims. `index.csv` carries the expected decision for scoring.

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

Expected-decision codes are the same twelve used in `../synthetic-cases-051-100/`: ASK_CUSTOMER, REQUEST_ACTION, GET_OPTIONS, VERIFY_FIRST, ESCALATE_OPERATOR, WAIT_WITH_DEADLINE, DECLINE_EXPLAIN, RECORD_STOP, RECORD_REFUSAL, RESOLVE_DUPLICATE, SEPARATE_AUTHORITY, RECONCILE_CONFLICT.

## Rebuild

```sh
cd _spec
python3 negatives_tool.py  --public "<HackatonPublicCases>/Delivery & Logistics"            # validate the JSON
python3 negatives_build.py --public "<HackatonPublicCases>/Delivery & Logistics" --out ..   # write the folders and index.csv
```

Both exit non-zero on any error and print the case and the reason.
