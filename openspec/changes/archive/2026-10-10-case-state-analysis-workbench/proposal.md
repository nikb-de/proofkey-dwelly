# Case-state data and analysis workbench

## Why
The team supplied a step-by-step source viewer and two annotated variants of Dwelly case 002. They are not compatible with either the frozen case-intake schema or the legacy next-contact runner. The team needs a usable analysis interface without leaking authored answers into inference or weakening the private cloud API.

## What Changes
- Preserve the supplied widget/data at upstream commit `8fbcd1fb633efa248e4045765a7854138118127d`, with a hash-checked catalog.
- Add a separate versioned, step-bound transcript projection, evaluator-only references and development-dataset export.
- Add a deliberately limited offline state baseline and explicit mechanical comparisons to unreviewed references.
- Add a dedicated loopback analysis service and browser workbench, reusing and hardening the supplied timeline component.

## Non-goals
No live model calls, cloud deployment, actual customer operations, automatic gold labels, case-intake v1 schema changes, or claim that the legacy model runner accepts this new format.

## Authorization
The user requests integration and parallel implementation and previously explicitly authorized autonomous stages without repeated confirmation. Source/code changes and local checks continue under that instruction. New paid calls and cloud changes are excluded.
