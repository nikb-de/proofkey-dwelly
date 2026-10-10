# Right onTime UX v4 — remediation re-audit

**Disposition: accepted for the defined offline prototype.** All eight prior findings are closed within the selected case and interaction scope. Final enlarged-team visual verification is recorded below. This does not certify real integration, identity enforcement, accessibility conformance or target-user acceptance.

Reviewer: separate nonauthor agent `/root/ux_full_audit`, 10 October 2026. Target: original workflow v6, interface-map-v2, v4 REPAIR-CONTRACT and approved Forward Fold / Forest identity. The reviewer did not author or edit the prototype. Writes were confined to `v4/audit`.

## Scope and revision

[Coverage](COVERAGE.md) and [machine coverage](coverage.json) account for all **38 frames and 24 drawn edges**, including the six workspace overview nodes. The five supplied snapshots 001/008/024/031/033 and synthetic SIM remain the selected scope. The design can represent mapped negative paths without real providers; those simulated transitions were exercised. All 50 organizer cases, actual authorization and delivery/return effects remain outside scope.

Reviewed behavioral SHA-256: `assets/app.js` = `48826d256ea130b7bcb8111c09f6c841e3c4566223727bea7fbce09dc983efc5`. The final manifest is `frozen-hashes.json`. No v3 or v3.1 brand-only acceptance was reused as behavioral evidence.

## Findings resolved

| Prior finding | Fresh evidence and conclusion |
|---|---|
| F1 — refusal recovery | Reload during refusal Sending → UNKNOWN → confirmed response now gives `refusal_saved`. Stop during refusal plus late confirmation retains both recorded refusal and stop; no new collection action appears. |
| F2 — operator dead end | Two failed date searches → help → operator clarification → customer answer → queue → reviewed continuation with explicit extra search allowance → date form opens. Shared command/check counts are retained, and consent remains absent until customer action. Stale version rejects the decision while keeping the form. |
| F3 — case navigation | Customer 008 → Team loads 008. The first probe required a page-load synchronization correction; the corrected assertion passed. This was a test timing issue, not a product defect. |
| F4 — date/consent | 2020 collection date is rejected against the virtual scenario date. Valid date, address, object, time, price, revision and explicit agreement are retained in the request and confirmed result. 033 reuses source-supported time/price consent; unavailable address is `null` and explicitly labeled unavailable, rather than fabricated. |
| F5 — bounded waiting | Team pending view exposes owner, next check, deadline, command/check limits and fallback. At three allowed checks, the pending request remains and responsibility moves to the operator, without sending a duplicate or resetting counts. Customer receives a concise support/update message. |
| F6 — current evidence | Quote and later booking records remain separately inspectable, with exact bodies, object/revision, recipient, channel, expected evidence and attributed responses. Wrong-object/stale replies reject; acknowledgement does not finish the task. The denied alternate-date quote is resumed with its original kind and requested date, not an invitation. |
| F7 — preparation lifecycle | Wrong configuration and intentionally incorrect local outcome produce failed status and expected/actual trace with enable disabled. Normal rehearsal reaches ready, explicit enable reaches launching/running, and editing configuration visibly invalidates that draft without changing the active run. |
| F8 — focus/style | Change selection restores focus to the slot task. Case/tab navigation preserves meaningful focus; native modal behavior remains usable. Form-boundary contrast was strengthened. Forest layout and approved vector mark were inspected at desktop/mobile widths; enlarged-layout verification is supplemented below. |

Additional mapped details checked: refusal reason; permission denial retains unsent intent without consuming a dispatch/date attempt; stop requested/failed/verified states; expired label read and recovery without a new return/request; close/reopen saved result; customer-only versus team evidence presentation; current-run source hashes and no historical answer replay. Investigation 024 now retains a clearly simulated investigation reference, next update and owner while explicitly leaving the delivery dispute open. Delivery 001 still preserves the second selected slot and separates booking from physical delivery.

## Repairs prompted during this review

The initial v4 pass found three remaining material issues, all repaired and rechecked:

1. 033 claimed an invented approved address, and an alternate-date quote body could contain the initial date. Both now preserve the available source truth and exact current intent.
2. Denied alternate-date submission lost its command kind; restoring permission sent an invitation. The explicit unsent-kind record now resumes the quote, and failed pre-send checks consume no date round or command.
3. The customer waiting page exposed team budgets/internal ownership in a nested card, while preparation lacked a scenario discrepancy trace and retained stale “passed” display after edits. Customer feedback is now role-appropriate; preparation has a bounded shared-transition rehearsal and visibly invalidates edited configuration.

The stop-acknowledgement failure and investigation next-update evidence were also made reachable/visible and checked. No unresolved P1/P2 behavioral finding remains within this finite scope. These fixes do not imply that a real provider integration or all possible concurrent event orderings have been proven.

## Independent evidence

`recheck.mjs` and `final-probe.mjs` drove visible UI controls in a separate temporary headless Chromium profile. HTTP(S) requests were blocked and only local files were opened. No user-browser session, listener, external action or publication was used. Workflow states were not assigned by tests: only fresh local demo resets, actual form inputs, visible simulator controls and read-only state observation were used. The failure option in the preparation UI is itself a disclosed test fixture, not an injected application-stage shortcut.

`independent-observations.json` and `final-observations.json` record the final broad and narrow runs with **no page errors**. `targeted-observations.json` preserves the earlier failing permission-recovery reproduction; it is superseded by the final successful “permission restored original quote” observation, not current acceptance evidence. Preliminary screenshots likewise preserve review history; final named captures and final hashes take precedence.

Actual rendered inspections included desktop team, both 360/430px customer layouts, 360px team, retained request history, operator decision/rejection, collection result, customer waiting, preparation failure, and enlarged customer result. Forest colors, local Manrope/Inter, approved Forward Fold geometry, modest corners, restrained brass and clear primary-action emphasis remain coherent. Large request IDs and evidence payloads wrap. Customer waiting no longer nests a card or displays internal budgets. The local “next update” is a simulator schedule, not a real service promise.

The preparation rehearsal checks the shared outcome transition/evidence guard against a separate small expected fixture and shows intentional mismatch. It is sufficient to demonstrate the mapped check/fail/ready UX; it is not an independent comprehensive evaluation engine or proof of all-case simulator correctness. Real source records remain separate from newly simulated evidence. Server-side permissions, authenticated roles, transport durability and physical effects remain declared boundaries.

## Visual supplement and final disposition

Final CSS SHA-256: `cf8333335f9d69a6ad78fedc489f3e29bd5b1b966f08485a14605a732ec0af9c`. The additional container-based reflow was read and the producer-generated `evidence/team-zoom200.png` and `client-zoom200.png` were visually inspected by this reviewer. Content and controls remain readable, the team details stack into the actual available workspace width, and no visible clipping was found. The producer performed the final no-horizontal-overflow measurement; the reviewer did not independently repeat that final CSS-only measurement. Independent enlarged-customer evidence is also in `final-client-200pct.png`. All four bundled Forward Fold SVGs were independently compared byte-for-byte with the approved logo package and match. Behavioral hash remains unchanged.

Per-part disposition: case workspace, customer task flows, operator exception flow, request/recovery evidence and simulation preparation are accepted within the selected offline scope; visual identity and inspected desktop/mobile/enlarged layouts are accepted. Human usability and production effect/authorization acceptance remain pending and are not inferred from this review.

## Evidence limits and trace

No human user testing, screen-reader session, full WCAG assessment, real carrier/API, multi-user transaction test, or claim of zero possible bugs. Browser file-storage behavior is only observed in the audit environment. Safe operator ownership/pending exits are valid endpoints where authority or outcome remains unknown; the prototype does not invent consent to force completion.

Route: discovery_review_mode / bounded nonauthor remediation review. Guides applied: local harness, review/model-consistency, original map/workflow, UX design-checks and brand handoff. Sensors: source/contract comparison, fresh UI transitions, negative paths, rendered inspection and frozen hashes. Acceptance is limited to the authorized offline UX; real consumer acceptance remains separate.

Trace: UX-V4-REMEDIATION-AUDIT-2026-10-10 → `interfaces/right-ontime-ux-v4/audit/REVIEW.md`.
