# Hackathon submission packaging plan

> For agentic workers: execute the independent documentation, evidence-export and cleanup reviews in parallel; root coordinates publication and final verification.

**Goal:** Package the existing main branch under the supplied A–G rules without inventing test outcomes.

**Architecture:** Keep the product and existing contracts intact. Separate retained development evidence from official challenge results; publish the supplied demo bytes and remove only reviewed obsolete artifacts.

**Tech Stack:** Python, PostgreSQL, browser JavaScript, Git and existing offline export/test tooling.

**Spec:** `openspec/specs/submission-packaging/spec.md`.

## Constraints and verification
- Preserve source cases, failed model outputs and actual receipt hashes.
- Publish no keys or credentials. Record the owner's visibility and dataset-publication confirmations separately from independently verified facts.
- Do not create launch posts or claim official answers without their actual records.
- Test the exporter with retained/null/error outputs, duplicate exports and unsafe identity rejection.
- Verify clean-environment setup, product health and scripted workflow; distinguish these from live-model quality.

## Execution
- [x] Documentation worker: refresh README, checklist and rights notices; smoke-test commands.
- [x] Evidence worker: add and test the offline retained-record packager without paid calls.
- [x] Audit worker: enumerate removable files, check source dependencies and repair documentation links.
- [x] Root: verify/copy the supplied video, remove only enumerated paths from the index and preserve local copies.
- [x] Root: complete final validation and archive the specification; prepare the verified package for publication to main.
