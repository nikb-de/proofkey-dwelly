# Safe Evidence Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing offline receipts understandable without exposing case content or inventing execution evidence.

**Architecture:** A pure, bounded receipt projector and formatter produces immutable content-free snapshots. A separate stdin-only module adapter renders them without opening a runtime. A short guide is exercised against fresh existing synthetic cases.

**Tech Stack:** Python, existing pinned Pydantic, unittest; no new dependencies.

**Spec:** `openspec/changes/safe-evidence-trace/specs/safe-evidence-trace/spec.md`; design in the sibling `design.md`.

## Global Constraints

- Only exact `CliReceiptV1` input, or bounded JSON bytes parsed into it. No raw run/readback join API in this version.
- Input bytes <= 1,048,576; depth <= 64; visited nodes <= 50,000; batch positions <= 128; effects per position <= 256; total effects <= 4,096; rendered UTF-8 bytes <= 262,144. Reject, never silently truncate.
- Emit only fixed schema keys, closed status enums, finite nonnegative durations, counts, ordinals, booleans and trace-local alias tokens. No raw arbitrary IDs, operation names, hashes, paths, timestamps, request arguments, rationale, references, postconditions or free-text failures.
- Always show provenance `unverified_receipt_projection`, transport dispatch `unknown`, original readback observation `not_observed` and publication files checked `false`.
- Input admission, host start, returned access status, reported effect verification, publication/export and shutdown remain distinct. Host start is not authorization; verified effect is not physical receipt/payment.
- No runtime authority, provider/network calls, collector, persisted schema change, existing CLI change, migrations or new dependencies. No merges/push/publication. Preserve all old evidence and untracked outputs.
- Use existing source interpreter `.superpowers/sdd/2026-10-08-proofkey-runtime/api-env.GEsSnS/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=runtime/src:runtime/tests` from worktree root. Run a frozen full suite once after both task checkpoints; they are not completion claims until that suite and final review pass.

## Review Focus

1. A forged `model_construct`/nested mutated model must fail instead of being cleaned by a serializer (Task 1).
2. Authorized verified effects with credential-shaped IDs must not leak into JSON or Markdown (Task 1).
3. Started-but-denied, unresolved ordinal and absent shutdown must not become successful execution (Task 1).
4. Deep/duplicate-key/oversized input and stdin streams must stop at exact bounds with safe errors (Tasks 1–2).
5. Fresh real receipts, including multiple batch positions, must retain denominator/correlation without giving the renderer state authority (Tasks 1–2).

## File Map

- `runtime/src/proofkey/execution_trace.py`: finite output contracts, detached input validation, projection and rendering.
- `runtime/tests/test_execution_trace.py`: pure hostile-input and real-receipt projection tests; shared test fixture helpers only here.
- `runtime/src/proofkey/trace.py`: minimal module adapter, stdin-only.
- `runtime/tests/test_trace_cli.py`: actual subprocess and bounded stream tests.
- `runtime/QUICKSTART.md`: short supported route and interpretation.
- `runtime/README.md`: one link near the opening, no unrelated rewrite.
- `docs/verification/2026-10-10-safe-evidence-trace.md`: controller-authored retained execution/review evidence and exact limits.

## Task 1: Bounded content-free projection

**Files:** create `runtime/src/proofkey/execution_trace.py`, `runtime/tests/test_execution_trace.py`.

**Interfaces:**

```python
class TraceError(ValueError):
    # str(error) is one of invalid_receipt, trace_limit_exceeded
    ...

def parse_cli_receipt(data: bytes) -> CliReceiptV1: ...
def build_execution_trace(receipt: CliReceiptV1) -> ExecutionTraceV1: ...
def render_trace_json(trace: ExecutionTraceV1) -> str: ...
def render_trace_markdown(trace: ExecutionTraceV1) -> str: ...
```

`ExecutionTraceV1` and nested output records are frozen strict extra-forbid contracts. Exact field names beyond the fixed epistemic markers are an implementation choice, but the following content is mandatory: optional run/release aliases and finite mode/clock enums; raw closed bootstrap/run/input/publication outcome enums; unresolved ordinal list and pending-command aliases; every command/batch ordinal with case/command aliases, input join status, host outcome/start fact, result-access status, per-effect alias/status with `receipt_reported` basis, result historical/wait/handoff/media/stop facts; independent export outcome; and optional shutdown booleans/counts/durations with unknown absence. Unknown and not-attempted must remain distinct. No raw source object or arbitrary dictionary survives in output. Sort effect keys only for deterministic traversal; never emit them. Tokens use namespace counters such as `case-1`, not hashes.

- [ ] **Step 1: Write RED tests.** Start with these literal expectations, then add the matrix below:

```python
def test_bootstrap_failure_is_not_execution(self):
    trace = build_execution_trace(CliReceiptV1(failure="invalid_input"))
    wire = json.loads(render_trace_json(trace))
    self.assertEqual(wire["provenance"], "unverified_receipt_projection")
    self.assertEqual(wire["transport_dispatch"], "unknown")
    self.assertEqual(wire["original_readback_observation"], "not_observed")
    self.assertIs(wire["publication_files_checked"], False)
    self.assertEqual(wire["positions"], [])

def test_duplicate_keys_are_rejected_without_echo(self):
    with self.assertRaises(TraceError) as caught:
        parse_cli_receipt(b'{"failure":"invalid_input","failure":"SECRET"}')
    self.assertEqual(str(caught.exception), "invalid_receipt")
```

Use literal or independently hand-derived expected statuses, not projector helpers. Obtain real typed command, batch, denied and pending fixtures through existing contract/test fixtures or the actual offline CLI, without depending on an existing TestCase lifecycle. Assert exact denominator and correlation behavior. Test secret canaries in every open field: IDs, operation names, rationale, evidence/policy refs, postconditions, output names and shutdown IDs. Assert whole JSON and Markdown omit them, not just selected keys. Cover hostile nested construct bypasses, wrong exact types, nonfinite/bool duration, cycles, UTF-8, duplicate keys, depth, input size and per-position/total counts. At each numeric boundary test accepted vs next rejected where feasible; if output limit binds first, assert the correct limit failure rather than pretending it succeeds.

- [ ] **Step 2: Verify RED.** Run the new module test with the stated source interpreter. Retain expected assertion/import failure before implementation in the private report.
- [ ] **Step 3: Implement.** Enforce bytes before decode; scan JSON nesting before parse; reject duplicate keys/nonfinite using stdlib hooks; validate `CliReceiptV1`. For typed input walk declared fields without `model_dump` (which can hide unauthorized fields), reject unknown model subclasses/cycles/bounds, and revalidate detached fields. Validate run/command release, mode, clock and unique command IDs. Check bounds before collecting projection rows. Use explicit allowlist construction, local token dictionaries and fixed Markdown table/diagram labels; never `repr(error)`, `default=str`, arbitrary recursive output or input-derived URLs.

```python
# Core semantics; do not infer any transport call from this branch.
host_started = command.started_at is not None
access_status = command.result.status if command.result is not None else "unknown"
effects = tuple(project_effect(key, value) for key, value in sorted(result.effects.items()))
```

Use output contract validation for renderer inputs too; forged traces cannot bypass the content-free invariant. Fail before emitting any oversized rendering. The parser may re-encode a prevalidated JSON tree for the existing JSON tuple bridge, but must not discard extra/invalid fields. Never create RuntimeFactory, read inventories, import providers or modify journals.
- [ ] **Step 4: Verify GREEN and compatibility.** Run new tests plus `test_batch_contracts`, `test_cli`, `test_cli_parity`, `test_host_contracts`; retain full commands/output/exit. Read own diff for omissions and mock-only assertions.
- [ ] **Step 5: Commit scoped files and report.** A checkpoint commit, not final completion. Report RED/GREEN, exact fields/limits, tests, self-review and concerns to the task report; independent task reviewer must approve before Task 2.

## Task 2: Stdin renderer and exercised quickstart

**Files:** create `runtime/src/proofkey/trace.py`, `runtime/tests/test_trace_cli.py`, `runtime/QUICKSTART.md`; modify opening of `runtime/README.md` only.

**Interfaces consumed:** Task 1's four functions, `TraceError`, frozen `ExecutionTraceV1`; no changes to their signatures. **Produced:** `python -m proofkey.trace [--format json|markdown]` (default JSON), stdout rendering and exit 0; invalid input/usage exit 2 with one fixed safe error object/line. No arbitrary input filenames or output path flags.

- [ ] **Step 1: Write RED tests.** Execute a real subprocess with valid CLI failure envelope and JSON format; assert fixed markers and exit 0. Add Markdown format, invalid options, malformed/oversize/deep/duplicate input, no traceback or secret echo. Test exact bounded stdin read:

```python
class ObservedStream(io.BytesIO):
    def read(self, size=-1):
        self.observed_size = size
        return super().read(size)
# main must request exactly 1_048_577 bytes, reject overflow, and not read again.
```

Run subprocesses from a fresh empty directory, snapshot files before/after and assert the renderer creates none. Validate the existing CLI still emits its own one-line envelope, not trace output. Include actual command and multi-position batch projection using Task 1 helpers or fresh CLI execution; assert host/result/publication/closure facts independently.
- [ ] **Step 2: Verify RED** with new adapter absent, retaining output.
- [ ] **Step 3: Implement minimal adapter.** Use a closed argument parse (no argparse error echo), one limit-plus-one stdin read, projector and chosen formatter. Catch only expected safe validation/IO errors; write fixed safe error, never content/paths/traceback. No imports of runtime ownership modules beyond those already needed by the typed receipt contract.

```python
def main(argv=None):
    # validate closed argv before reading; invalid usage returns 2
    data = sys.stdin.buffer.read(1_048_577)
    trace = build_execution_trace(parse_cli_receipt(data))
    output = render_trace_json(trace) if format_name == "json" else render_trace_markdown(trace)
    sys.stdout.write(output + "\n")
    return 0
```

Write a concise English quickstart (target <= 150 prose words excluding literal commands/diagram) with the exact existing rescheduling JSON from README, fresh `mktemp -d` state, captured receipt, and `python -m proofkey.trace --format markdown < receipt.json`. Derive source path before `cd`, preserve absolute source/interpreter paths. Include the equivalent refusal run or link to its existing instructions. Explain synthetic fixtures, exit 0 versus verified business effect, retained state, no retry/new key for unknown work, and no physical receipt/payment implication. Static Mermaid: receipt -> reported host/result -> reported verification -> publication and closure; dispatch unknown labelled separately. Link guide from README opening.
- [ ] **Step 4: Verify GREEN.** Run new adapter tests and Task 1 tests. Execute fresh rescheduling and goods-refusal guide captures; preserve source receipt, JSON/Markdown trace, command/exit/duration, actual exports and readback/closure facts in a newly allocated private evidence directory. Do not regenerate effects merely to regenerate an export. Controller runs final full regression under frozen source and checks the documentation against these retained results.
- [ ] **Step 5: Commit scoped files/report and obtain task review.** Controller performs broad leaf review, one grouped fix wave if needed, strict OpenSpec validation, final evidence/status updates and child archive only after all gates pass.

## Self-Review and Coverage

All four spec requirements map to Task 1 (bounds, semantics, redaction) or Task 2 (public adapter and guide). The five review-focus risks are explicit tests above. Both tasks share only the defined function/type boundary; no concurrent source implementers. Exact output field names are deliberately delegated, while values, authority limits and required information are binding. Fresh recorded execution is not independent human onboarding. J08/J07 and all external gates remain open.
