# Case JSON catalog for the viewer

This folder on `main` is the catalog of annotated cases that the viewer reads through the GitHub API. Add one self-contained JSON per case directly here. No redeploy is needed for new files.

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

| File | Case | Steps | Scenario |
|---|---|---|---|
| `001.json` | 001 | 5 | Recipient cannot attend the scheduled delivery window (positive) |
| `002.json` | 002 | 5 | Apartment number missing from the delivery address (positive) |
| `002-N4.json` | 002-N4 | 7 | Correction form session expired mid-submission (negative branch CHANNEL_FAILURE) |
