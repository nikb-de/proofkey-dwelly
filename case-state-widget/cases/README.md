# Case JSON catalog for the viewer

This folder on `main` is the catalog of annotated cases that the viewer reads through the GitHub API. Edit the compact source in `../annot/<id>.json`, then rebuild this folder with `../pipeline/compile.py`. No redeploy is needed for new files.

- Name: `<id>.json`, e.g. `003.json` for the public case or `003-N2.json` for a negative branch (branch ids follow `data/negative-branches-001-050/index.csv`). Ids: letters, digits, hyphen and underscore, up to 100 characters, starting with a letter or digit.
- Language: English. All human-readable text (goal, facts, requests, criteria, agent state, explanations) is in English; message bodies are the verbatim source history.
- Format: `schema_version: "case-step-viewer/1.0"`, `title`, `initial_state`, `steps[]` with full `state_after` snapshots. See the [structure guide and example](../README.md), the [annotation rules](../HANDOFF.md) and the [JSON Schema](../schema.json).
- Keep the source messages and the evidence references. Do not put future facts into earlier states, and do not close a wait on an executor before the executor replies.
- A new scenario branch is a separate file. Do not overwrite files you did not create.
- Files in this folder appear in the public library of the site. Do not add secrets or real, non-public data.

Check from the repository root (Node.js):

```sh
node --input-type=module -e 'import fs from "node:fs"; import {validateCase} from "./case-state-widget/viewer.js"; for (const name of fs.readdirSync("case-state-widget/cases").filter(x=>x.endsWith(".json"))) { validateCase(JSON.parse(fs.readFileSync("case-state-widget/cases/"+name,"utf8"))); console.log("OK",name); }'
```

The catalog refreshes when the page opens, on "Refresh list", and periodically while the tab stays open. New cases do not require changes to `index.html`, `app.js` or a manifest.

## Currently annotated

50 public cases (001–050) and all 275 negative branches listed in `data/negative-branches-001-050/index.csv`. Every file is built from a compact annotation by the pipeline and validated against `viewer.js`, `schema.json`, patch replay and a future-leak check before publishing. The negative branches retain the reviewed parent states before divergence and add their authored escalation, desk response and follow-through.

Branch completion covers the alternative coordination task. For example, an operator's registration is not its decision, and a customer's selection is not a booking. Unmet parent criteria at the scope change are archived in `prior_success_criteria` with their original status and retirement event; they are never marked met to force branch closure. The final source message states what is confirmed and what remains.

Rebuild and check from the repository root:

```sh
python3 case-state-widget/pipeline/compile.py --all
python3 case-state-widget/pipeline/test_negative.py
node case-state-widget/pipeline/validate.mjs case-state-widget/cases/*.json
npm test --prefix case-state-widget
```

The table below lists the public scenarios and the original channel-failure reference. The full negative branch inventory is in [NEGATIVE-REPORT.md](../pipeline/NEGATIVE-REPORT.md).

| File | Case | Steps | Scenario |
|---|---|---|---|
| `001.json` | 001 | 5 | Delivery window change |
| `002-N4.json` | 002-N4 | 7 | Form failure: did the correction save? |
| `002.json` | 002 | 5 | Missing apartment number |
| `003.json` | 003 | 5 | Driver locked out at a gated building |
| `004.json` | 004 | 4 | Call before arrival |
| `005.json` | 005 | 5 | Household member receives the parcel |
| `006.json` | 006 | 5 | Redirect to a pickup point |
| `007.json` | 007 | 5 | Pickup deadline extension |
| `008.json` | 008 | 5 | Two-hour slot instead of all-day delivery |
| `009.json` | 009 | 5 | Access route for a bulky delivery |
| `010.json` | 010 | 4 | Hold during a short absence |
| `011.json` | 011 | 4 | Tracking stuck after depot arrival |
| `012.json` | 012 | 5 | Replacement slot after a vehicle breakdown |
| `013.json` | 013 | 4 | Disputed failed delivery attempt |
| `014.json` | 014 | 5 | Receiving desk closed on arrival |
| `015.json` | 015 | 4 | Parcel at the wrong local depot |
| `016.json` | 016 | 5 | Pickup locker is full |
| `017.json` | 017 | 5 | Broken tracking link in notification |
| `018.json` | 018 | 5 | Return-to-sender cutoff |
| `019.json` | 019 | 5 | Weather suspends the route |
| `020.json` | 020 | 5 | One parcel of three missing |
| `021.json` | 021 | 5 | Dented carton evidence |
| `022.json` | 022 | 4 | Broken lamp replacement |
| `023.json` | 023 | 4 | Leaking parcel at the depot |
| `024.json` | 024 | 4 | Delivered scan, no parcel |
| `025.json` | 025 | 4 | Replacement for a lost parcel |
| `026.json` | 026 | 5 | Misdelivered parcel recovery |
| `027.json` | 027 | 4 | Another customer's parcel |
| `028.json` | 028 | 4 | Wrong item in a correctly addressed parcel |
| `029.json` | 029 | 4 | Chilled food outside the merchant's temperature range |
| `030.json` | 030 | 5 | Missing handover record for a high-value parcel |
| `031.json` | 031 | 5 | Approved return without a label |
| `032.json` | 032 | 5 | Return without a printer |
| `033.json` | 033 | 5 | Missed return collection |
| `034.json` | 034 | 4 | Return stuck at the carrier depot |
| `035.json` | 035 | 4 | Refund review not started |
| `036.json` | 036 | 4 | Collection of four labelled cartons |
| `037.json` | 037 | 4 | In-home collection of a heavy return |
| `038.json` | 038 | 4 | Reshipment after return to sender |
| `039.json` | 039 | 5 | Return of a duplicate floor light |
| `040.json` | 040 | 4 | Stopping dispatch of a cancelled order |
| `041.json` | 041 | 5 | Receiving-dock appointment for a pallet |
| `042.json` | 042 | 4 | Unloading a pallet without a forklift |
| `043.json` | 043 | 5 | Pallet dimensions and weight for freight collection |
| `044.json` | 044 | 5 | Missing pallet in a business consignment |
| `045.json` | 045 | 5 | Commercial invoice for an import broker |
| `046.json` | 046 | 5 | Broker mandate from the authorised director |
| `047.json` | 047 | 5 | Explaining a carrier import charge |
| `048.json` | 048 | 4 | Cleared parcel awaiting last-mile handover |
| `049.json` | 049 | 4 | Duplicate service charge on an invoice |
| `050.json` | 050 | 4 | Guaranteed-delivery surcharge after a delay |
