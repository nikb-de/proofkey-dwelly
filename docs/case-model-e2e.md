# Case model E2E: state and work controls

The platform now has an external HTTP replay harness for the existing authored
case histories, plus read-only model-job monitoring in the operator UI. A green
scripted run verifies the harness and platform plumbing, **not live model quality**.

## What is measured

| Layer | Assertions |
|---|---|
| Source replay | Visible messages, direction, original body, goal/roles; no future actors or answer labels |
| Coordination proposal | State, proposed action and target, waiting party, visible evidence, no premature completion |
| Durable job | Case/revision/hash/profile binding, retained result, same-key replay, one dispatch, no automatic retry |
| State freshness | New evidence makes the older analysis stale; old-revision submissions are rejected |
| Business authority | No decisions, approvals, bookings or external effects are created by a model run |
| Operator UI | Queued/running/terminal state, coordination details, current/stale binding, counters, reload without resubmission |
| Recovery | A queued job can continue; a saved response can be parsed without another provider call; an expired dispatched job without a saved response becomes `outcome_unknown` |

Transport states (`queued`, `running`, `response_received`, `succeeded`, `failed`,
`outcome_unknown`) are separate from model coordination states (`unknown`, `ready`,
`acting`, `waiting`, `completed`) and from case lifecycle/decision/action states.
Model `completed` does not mean physical delivery or an executed business action.

## Source and label limits

The source set contains 16 cutoffs: six from `case-002`, eight from its channel-failure
variant `case-002-n4`, and two from the `minimal` UI control. These are **one logistics
family and one control**, not 16 independent cases or a held-out benchmark.

Each cutoff becomes a separate canonical case because v1 participants are immutable.
Declaring the union of future participants would leak information. A clearly identified
internal context event carries only the original goal and currently visible actor
names/roles. Unsupported channels and missing timestamps are recorded as input
transformations. Original source hashes and event mappings stay in the run artifacts.

`tools/dwelly_e2e/cases.py` contains the manually specified expectation ledger.
It remains development-only and requires team validation. The separate
`tests/fixtures/good-candidates.json` contains scripted candidate bodies for harness
testing; it is never used as a live model response. Mutated negative controls verify
that the checker rejects wrong targets, invented evidence and premature completion.

## Run a live provider experiment

In the private, ignored worktree `.env`, set only the providers you will use:

```dotenv
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
```

The current example Claude profile also names `ANTHROPIC_WORKSPACE_ID` as a required
configuration field. It needs a valid configured workspace ID for that profile.
For a key already scoped to one workspace, the existing provider configuration
supports omitting that profile's `workspace_id_env` when the explicit header is
unnecessary; this run does not change account configuration automatically.
Do not put actual keys in documentation, Git, case messages, screenshots or reports.
`load_provider_env` reads allowlisted values as data, without sourcing shell code.

Start the existing platform explicitly with live dispatch enabled. Use an existing
configured database environment variable and a stable experiment budget scope:

```sh
PYTHONPATH=.:tools:runtime/src python -m tools.dwelly_platform serve \
  --port 8095 --schema proofkey_platform_local --migrate \
  --provider-env-file .env --allow-live \
  --budget-scope authored-case-e2e-20261010
```

The command expects `PROOFKEY_PLATFORM_DATABASE_URL` to be configured privately.
Do not start a second server on an occupied port. The default profile file caps
reserved spend at USD25 per model in the stable scope; changing run IDs must not
be used to reset the scope or bypass that cap.

Start with one cutoff, then use a **new output directory** for a bounded full run:

```sh
PYTHONPATH=.:tools:runtime/src python -m tools.dwelly_e2e run \
  --base-url http://127.0.0.1:8095 --mode live \
  --profile openai-gpt-4-1-mini --run-id openai-canary --limit 1 \
  --output outputs/openai-canary-NEW
```

Profiles currently available in the example configuration are `openai-gpt-4-1-mini`,
`anthropic-claude-sonnet-4-6`, and `gemini-2-5-flash`. Select one per command. The default
limit is 16. Use unique run IDs for distinct experiments. The harness does not tune
prompts or silently repeat provider requests. It stops on authentication/budget errors,
uncertain dispatch, or invalid binding. A semantic mismatch is retained and the bounded
run continues so failure coverage is visible.

Exit status: `0` checks passed in the declared mode; `1` failed checks; `2` unavailable.
`0` with `mode=simulated` is never live acceptance.

## Artifacts and interpretation

Each run saves `report.json`, `report.md`, per-cutoff source/expectation/job/check records,
individual HTTP exchanges, preflight availability and the stale/idempotency probe.
References are stored locally but never sent as inference input. The probe appends an
explicit synthetic event after semantic checks and is excluded from their evidence.

Read the mode, requested/observed model, source qualification and unavailable rows
before interpreting totals. Semantic assertions and operational assertions are counted
separately; assertion counts are not case-level accuracy. This suite does not yet prove
live-model quality, production identity/auth, real courier integration, cloud failover,
or multimodal model quality. Existing media tests exercise separate upload/validation/
review controls; they are not silently included in this text-case semantic score.

## Reproduce the no-provider integration test

```sh
PROOFKEY_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:63119/proofkey \
PYTHONPATH=.:tools:runtime/src node platform-ui/tests/case-model-e2e.mjs
```

This creates and removes a unique test schema; it does not modify the normal platform
schema. HTTP, PostgreSQL, worker admission/parsing and browser UI are real. Only the
external request is replaced by a clearly identified `SIMULATED` transport. The script
reports its artifact directory and verifies cleanup, source-cutoff coverage and per-case
dispatch counts. Use `PROOFKEY_TEST_PYTHON`, `PROOFKEY_PLAYWRIGHT_MODULE` and
`PROOFKEY_CHROME_PATH` to override the local test runtimes when needed.
