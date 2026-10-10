# Decision episodes — team handoff draft

Status: **draft / synthetic / not human-validated / not a benchmark**. Version: 0.1, 10 October 2026.

This package gives teammates a format and a copy-ready prompt for generating training examples and evaluation cases for the logistics agent. The unit is a **decision at a specific time**, not an entire conversation with a known happy ending.

## Start here

1. Read [the team brief in Russian](TEAM_BRIEF_RU.md).
2. Give a generator [GENERATOR_PROMPT.md](GENERATOR_PROMPT.md), [CONTRACT.md](CONTRACT.md), the relevant JSON schemas and **only the source cases it is authorised to read**.
3. Inspect the [example index](examples/README.md). Agent inputs, reference labels and simulator futures are separate.
4. Separate [training from evaluation](TRAINING_AND_EVAL.md); review with [RUBRIC.md](RUBRIC.md) and [HUMAN_REVIEW.md](HUMAN_REVIEW.md).
5. Use [QA.md](QA.md) for the scope and limits of package checks.

## What this package contains

- 19 decision snapshots across 3 original synthetic families: damaged goods, rescheduling, return receipt.
- All 6 proposed stages: intake, decide, authorize, execute, verify, resume.
- Positive, insufficient-information and unsafe-action controls; multi-step continuations and counterfactual branches.
- Machine-readable input, private-label, manifest and simulator schemas.
- A plan for growing to 60 decision points and collecting independent team cases.

These are **seed examples**, not 19 independent business scenarios. All 19 belong to development. No held-out test set, model training, provider generation, multi-judge run or performance result is included.

## Isolation from the current service

This is a proposed dataset contract, not a change to the service contract. Current snapshots use `dwelly-snapshot-v1`; proposals use `dwelly-model-proposal-v1`. This package uses `logistics-decision-v0.1`. The existing runner cannot consume it without a separately designed adapter.

Every action in the examples is either an **unsent proposal** or a **simulation**. Authorisation, execution and readback fixtures are not real approvals, real integrations or proof that runtime enforcement exists.

The directories named `private_labels` and `simulator` are only a logical separation. A future harness must actually deny the agent access to them; merely putting them in another directory is not isolation.

## Provenance and distribution

The examples are newly authored fictional scenarios. Names, IDs, money, policies and times are synthetic, not statements of Dwelly policy. Labels were authored by the assistant and remain unvalidated. The discussion supplied by the user informed the design; private transcript text and unrelated personal details are not copied here.

A read-only check of public case 035 informed one distinction: absence of a file does not imply absence of evidence, because evidence can be inline. Its source text is not copied into this dataset. See [SOURCE_NOTES.md](SOURCE_NOTES.md).

Publishing this package for team review does not promote its labels to ground truth or authorise any business operation.
