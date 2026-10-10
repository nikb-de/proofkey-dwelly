# Right onTime — design handoff

Final Forest UX 4.1 · 10 October 2026

## Open the design

Download and extract the complete folder, then open [prototype/index.html](prototype/index.html).
No server, account, installation or internet is needed to explore it.

- [Team workspace](prototype/team.html): case list, case detail, requests, operator queue and simulation preparation.
- [Customer experience](prototype/client.html): delivery choices, reviewed consent, outcomes and help.
- [Brand assets and usage](brand/USAGE.txt): selected Forward Fold vectors, palette and local font locations.
- [Detailed handoff and demo routes](prototype/README.txt).
- Workflow-to-screen coverage (historical worklog retained in Git history): 38 mapped frames and 24 transitions.
- Baseline semantic audit (historical worklog retained in Git history): all eight identified findings resolved in v4.
- Final brand review (historical worklog retained in Git history): latest refinement and unchanged behavior.
- Fresh check evidence (historical worklog retained in Git history): interaction, adverse-path and identity checks plus screenshots.

GitHub displays source files; download the folder to interact with the HTML prototype. This repository is not a deployed website.

## What changed in 4.1

The latest selected Math of Beauty lockup moves the wordmark 12 master units closer to the original Forward Fold symbol. Both workspaces and the entry screen use the exact selected SVG. The symbol remains unchanged. Light/dark favicon assets follow the selected four-file allowlist. Forest colors, Manrope/Inter and the repaired workflow behavior are retained.

## Three-minute review

1. Open Team, choose Delivery 001, then Customer. The selected case is preserved.
2. Select the second delivery window, review the terms and confirm. Sending and awaiting a response are distinct from success.
3. Open UX demo controls and choose Confirmed response received. Check that the exact selected slot remains in the result.
4. Try Delivery 008 to see quote requests, and the operator queue for exception handling. The detailed handoff lists recovery scenarios.

## Scope for implementation

This is an editable HTML/CSS/JavaScript UX prototype. It includes five organiser agent snapshots (001, 008, 024, 031, 033) and one labelled synthetic refusal scenario. Provider responses and all actions are simulated. It does not include live AI, carrier APIs, authentication or real bookings. The role switch is demo navigation. Browser file-storage behavior may vary.

The baseline audit covers workflow v6 and interface map v2. The final visual source is this HTML package; older exploratory Figma/brand boards are not the current implementation reference. Build real integration and authorisation separately, preserving consent, correlation, bounded waits and recovery semantics.

All supplied UI, comments and handoff copy are English. Native browser date controls can follow the viewer's locale.

## Files to edit

- `prototype/assets/app.js`: demonstrated behavior and English interface copy.
- `prototype/assets/style.css`: components, responsive layout and focus.
- `prototype/assets/tokens.css`: semantic Forest palette and local font bindings.
- `prototype/assets/brand/`: exact selected SVGs.
- `prototype/app-config.js`: names and local demo configuration.

## Optional developer checks

The prototype itself requires no packages. To run checks, use Node.js 22 or later and Playwright with Chromium. Install development dependencies in `prototype`, install Playwright Chromium, then run `npm run check`. Tests use isolated browser profiles and block HTTP(S). Existing installations can be selected with `PLAYWRIGHT_PACKAGE_JSON` and `CHROMIUM_EXECUTABLE_PATH`.

The producer environment used Playwright 1.62.1. Ordinary and repair tests passed (41 + 68), plus 23 identity/responsive checks. This is not human usability testing, full accessibility certification or a claim of zero possible defects.

## Provenance

Initial case data derives from the public Dwelly cases through the supplied teammate repository. New replies, prices, references and documents are explicitly demo fixtures. Font licences are bundled. See `manifest.json` for selected asset and package hashes. No internal engineering library, credentials or private project history is included.
