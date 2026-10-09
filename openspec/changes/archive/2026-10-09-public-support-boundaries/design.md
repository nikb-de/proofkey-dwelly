## Context

The existing matrix intentionally preserves a source-discovery snapshot. J13 installed evidence at `5bc38c8`, J06 installed trusted-case evidence at `80e0d6f`, and trace source evidence at `7b4c6e2` are distinct. An in-progress stop-v2 implementation must not inherit any of those qualifications.

## Goals / Non-Goals

Goals: make launch path, exact candidate, scenario and limitations scannable; link the evidence; preserve historical findings with dated addenda.

Non-goals: new examples, acceptance execution, automatic release verification, user research, live integration, public hosting or source security certification.

## Decisions

Use a seven-row table in the primary README rather than another competing guide. Rows cover fixed installed replay, trusted new cases, source trace, other command routing, registered v1 controls, pending stop-v2 and the six-interface boundary. Positive rows require an exact candidate and checked local evidence link. Describe unfinished stop-v2 as in development until its own verification document records completion; do not predict its result. Preserve all original denominators in their reports and keep the historical integration document body unchanged.

The documentation author reads current entrypoint declarations and evidence reports, but does not run provider/runtime acceptance merely to refresh documentation. The independent reviewer checks the exact docs delta against those sources. Controller closure updates the register only after checks pass.

## Risks / Trade-offs

A moving working tree can make "current" ambiguous. Mitigation: explicit candidate IDs and source/installed labels, pending status for unfinished work. Historical line numbers can drift. Mitigation: a dated preface identifies them as historical rather than silently recertifying them. A concise table omits details. Mitigation: link the retained long matrix and safe failure guidance.

## Migration Plan

Docs-only addition, no state migration. The new README table becomes the primary support link; the long matrix remains an audit reference. Future behavioral leaves update only their row from executed evidence.
