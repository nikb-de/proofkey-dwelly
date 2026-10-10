# Synthetic cases 051–100 (Delivery & Logistics)

Fifty invented cases in the exact format of the organisers' public set (`index.md` + `history.md`, 4–5 events, status "Completed — specific coordination task only"). Same world: carrier Plover Arc Logistics, coordinator Iona Quill at Rivet Delivery Desk. Numbers 051–100 do not collide with the public 001–050. No real people, places or companies.

Kept in its own folder so it never mixes with the organisers' data in `../dwelly-public-cases/`.

## Why these exist

The public 001–050 all end well and show only "pass it on" or "ask back". These 50 add the branches the hidden test cases are likely to ask for: unknown outcome of an earlier action, waiting with a deadline, declining, stopping, refusal, duplicates, authority gaps, conflicting records, escalation to a human.

| Decision type | Cases | What the coordinator does at event 003 | Sheet in the v5 workflow |
|---|---|---|---|
| ASK_CUSTOMER | 051–058 | asks the customer for exactly one missing input (a choice, a field, a confirmation, an action now) | A / B |
| REQUEST_ACTION | 059–066 | asks the team or operator that holds the authority to perform a permitted action | C |
| GET_OPTIONS | 067–070 | asks for availability and price before any change; the customer accepts in the verified thread | B |
| VERIFY_FIRST | 071–074 | an earlier request has an unknown outcome (timeout, bounce, error, silence): check the saved state, no second change | R |
| ESCALATE_OPERATOR | 075–078 | no policy option or a human decision is needed: register facts, sources, the exact question | E |
| WAIT_WITH_DEADLINE | 079–081 | a reply is missing: one reminder with the deadline and consequence, no booking | B |
| DECLINE_EXPLAIN | 082–085 | the request is outside policy: decline citing the policy, offer the permitted alternative | A |
| RECORD_STOP | 086–088 | the requester cancels: record the stop, forbid new actions, ask what was already executed | F |
| RECORD_REFUSAL | 089–092 | goods refused: record the refusal; return authorisation is a separate step; refusal is not a refund | D |
| RESOLVE_DUPLICATE | 093–094 | the same request twice: link to the first, one change only | F |
| SEPARATE_AUTHORITY | 095–097 | the requester lacks the recorded authority: go to the authorised party, disclose nothing | A |
| RECONCILE_CONFLICT | 098–100 | two sources disagree: keep both, request evidence, no finding | A / E |

## Files

| Path | Content |
|---|---|
| `Delivery & Logistics/0NN/index.md`, `history.md` | the cases |
| `_spec/labels.csv` | one row per case: decision type, sheet, scenario, stage, action addressee, channel, next action, boundary, outcome |
| `_spec/manifest.json` | the design of each case (what it tests) |
| `_spec/SPEC.md` | the generator specification (format, world, style, decision-type rules) |
| `_spec/validate.py` | format and consistency checks; regenerates `labels.csv` |

## Decision point for testing

Give the system events 001–002 only (plus `Context` and `Initial request` from `index.md`), hide event 003 and later, and compare its proposal with event 003 on four things: who it addresses, through which channel, what it asks, and what it claims. `labels.csv` carries the expected decision type for scoring.

## Check

```sh
cd _spec
python3 validate.py --public "<path to HackatonPublicCases>/Delivery & Logistics"
```

Exits non-zero on any error and prints the case and the reason. Last run: 50 cases, 0 errors.
