# Two-case local demo

This is an **unexecuted operator recipe**, not a successful demo, release or reproduction receipt. It records two fixed synthetic replays from a source checkout in an already available environment. Read [README.md](README.md) for interfaces and [RIGHTS.md](RIGHTS.md) for unresolved source/dependency rights.

## Before execution

The project owner must separately authorize the two-position run, release the relevant source hold and supply a coherent frozen source scope plus the intended Python executable/environment. Record that scope's identifier and actual interpreter, platform and installed dependency versions privately. The scope must include the application bytes actually used, selected profiles/fixtures and `src/proofkey/schema.sql`; a partial hash list is not whole-candidate closure. Do not repin historical qualifications or change source to make this recipe succeed.

Start in the selected checkout's `runtime/` directory. Python >=3.11 is declared; the previously observed CPython 3.12/macOS-arm64 environment does not qualify other environments. Runtime dependencies must already be available to the selected interpreter. This guide does not install anything, activate an environment, create a virtualenv or qualify the installed console entrypoint. The first line below selects the `python3` currently resolved by your shell; confirm that it is the owner-approved interpreter before running.

No live provider, subscription/account, credentials, API server, network, paid call, publication or submission is authorized by this guide. The child environment below excludes inherited credential variables and user-site packages; it is not a network sandbox or proof of protected custody. Run only the frozen trusted offline code. Keep all output private and preserve both cases' separate runtime-created state.

## Record exactly two positions

The recorder itself uses only Python's standard library and does not import the product. Its children run the current CLI. It preserves each complete input, stdout, stderr, actual command, UTC start/end, monotonic wall time, return code or timeout/launch-error status and byte hashes. Negative return codes remain signal outcomes; a timeout or launch error has no invented normal exit.

The 150-second recorder timeout is not the runtime's active budget, a timed-drill pass or a hard-I/O cancellation guarantee. `subprocess.run` kills and waits for its direct child on timeout; the record stays partial. This is a finite trusted-code operator recipe, not a general untrusted-program runner. A recorder interruption or recording I/O failure may leave only partial files: the already-written plan retains both required positions.

```sh
PROOFKEY_PYTHON="$(command -v python3)"
"$PROOFKEY_PYTHON" -B - "$(pwd -P)" <<'PY'
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

runtime = Path(sys.argv[1]).resolve(strict=True)
source = runtime / "src"
if not (source / "proofkey" / "cli.py").is_file():
    raise SystemExit("Start in the selected runtime directory")
cases = (
    ("window", "host-window-replay-v1", {
        "case_id": "C1", "object_id": "O1", "principal_id": "U1",
        "request_id": "REQ1", "request_revision": "v1", "consent_revision": "v1",
        "kind": "reschedule_window", "consent_mode": "window",
        "arguments": {"window_start": "2026-10-08T10:00:00+00:00",
                      "window_end": "2026-10-08T12:00:00+00:00",
                      "inventory": {"item-1": 1}},
        "evidence_ids": [], "narrative": None}),
    ("goods", "host-goods-replay-v1", {
        "case_id": "C1", "object_id": "O1", "principal_id": "U1",
        "request_id": "REQ1", "request_revision": "v1", "consent_revision": "v1",
        "kind": "goods_refusal", "consent_mode": "unknown",
        "arguments": {"inventory": {"item-1": 1}},
        "evidence_ids": [], "narrative": None}),
)
root = Path(tempfile.mkdtemp(prefix="proofkey-observed-replay-")).resolve()
plan = {"planned_count": 2, "positions": [
    {"ordinal": i, "name": name, "release": release}
    for i, (name, release, _) in enumerate(cases)]}
(root / "PLAN.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
print("Retain this private observation root:", root, flush=True)

def digest_file(path):
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

for ordinal, (name, release, body) in enumerate(cases):
    parent = root / name
    parent.mkdir(mode=0o700)
    request = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    (parent / "request.json").write_bytes(request)
    argv = [sys.executable, "-B", "-m", "proofkey.cli", "run",
            "--release", release, "--input", "-"]
    env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONNOUSERSITE": "1", "PYTHONPATH": str(source)}
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    status, exit_code = "launch_error", None
    with (parent / "stdout.json").open("xb") as out:
        with (parent / "stderr.txt").open("xb") as err:
            try:
                result = subprocess.run(argv, cwd=parent, env=env, input=request,
                                        stdout=out, stderr=err, timeout=150, check=False)
                status, exit_code = "exited", result.returncode
            except subprocess.TimeoutExpired:
                status = "timed_out"
            except OSError:
                status = "launch_error"
    elapsed = time.monotonic() - started
    ended_at = datetime.now(timezone.utc).isoformat()
    names = ("request.json", "stdout.json", "stderr.txt")
    observation = {
        "kind": "same-environment-synthetic-replay-observation-v1",
        "ordinal": ordinal, "planned_count": 2, "release": release,
        "argv": argv, "cwd": str(parent), "source": str(source),
        "interpreter": sys.executable, "python_version": platform.python_version(),
        "platform": platform.platform(), "status": status, "exit_code": exit_code,
        "started_at": started_at, "ended_at": ended_at, "wall_seconds": elapsed,
        "artifact_hashes": {name: digest_file(parent / name) for name in names},
        "artifact_bytes": {name: (parent / name).stat().st_size for name in names},
        "business_review": "unreviewed", "source_closure": "not_certified",
        "rights": "not_certified", "clean_install": False,
        "mode": "synthetic_replay", "provider_participation": "none_requested",
    }
    (parent / "observation.json").write_text(
        json.dumps(observation, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print("Planned positions: 2. Review both; no success claim has been computed.")
PY
```

Keep the printed directory and `PLAN.json`, including any partial output. Each completed recording has `window/` or `goods/` with `request.json`, `stdout.json`, `stderr.txt`, `observation.json` and any `.proofkey/{resources,inventories,runs}` created by the child. Do not delete/reset state, rerun into it or replace failed rows. Any later authorized retry must have a new root and remain a separate attempt.

The dates and C1/O1/U1/REQ1 identities are fixed replay data, not current consent. Changing either request does not register a new case. The two requests contain no narrative or media. Their business fingerprints are fixed by kind, consent mode and arguments; request identity/revision are separately bound.

## Review both positions

Create a private `review.md` in each case directory. Do not modify the original inputs, raw output or observation. A process exit alone is not business success. Read no more than 16 MiB per JSON/text artifact in this manual recipe; preserve oversized bytes and mark the row unreviewed/failed instead of truncating it into a positive. Do not follow symlinks or arbitrary paths from output; unexpected files or paths require investigation. Inspect complete bounded stderr privately; any diagnostic must be explained, never hidden.

1. **Capture:** confirm original request/ordinal/release, actual argv/interpreter and UTC/wall measurements. Recompute SHA256 of request/stdout/stderr against `observation.json`. Require `status == "exited"`, `exit_code == 0` and exactly one complete JSON object in stdout for a possible positive. Keep nonzero/signal/timeout/launch-error/missing records as their observed outcomes. Do not display raw diagnostics publicly.
2. **CLI and command:** require `kind == "proofkey-cli-receipt-v1"`, `failure == null`, nonnull `run` and `shutdown`. Require `run.kind == "host-command-run-receipt-v1"`, `run.input_outcome == "admitted"`, `run.publication_status == "committed"`, `run.unresolved_admission == false`, no `run.pending_command_ids`, and `run.export_outcome == "written"` with no `run.export_failure`. The returned `run.command` must have `command_tag == "run"`, the requested `release_id`, `mode` in `{"synthetic_replay", "offline_synthetic"}`, `clock_mode == "synthetic_replay"`, `outcome == "result"`, `inventory_status == "committed"`, no command failure and a nonnull result. Mode/release/clock are command fields, not direct `run` fields.
3. **Business:** require `run.command.result.status == "authorized"`, the expected binding and request fingerprint, and inspect every effect's actual status/postcondition. Window requires verified `reschedule`; goods requires verified `register_goods_refusal` **and** verified `create_return`, separately. Record any unexpected effect or unresolved/waiting/unknown result. Return creation is not physical receipt. Neither case executes money: refund/coverage disposition is record-only.
4. **Publication and identity:** under the case's own `.proofkey/runs/`, locate the one run directory whose actual `FINAL-MANIFEST.json` has `run_id == run.run_id`; directory names are not assumed to equal run IDs. Require the final manifest's command, release, mode, clock and input to agree with the returned command/input. Verify `run.final_reference` names `FINAL-MANIFEST.json` and its hash matches the actual bytes. Read `INPUT-INVENTORY.json` and all named `run.references`, compare their actual byte hashes, and join the input/command IDs to the manifest. Require no unresolved/pending entries. Use only the fixed permitted reference filenames declared in [host_contracts.py](src/proofkey/host_contracts.py), not an arbitrary stdout path.
5. **Exports:** require `run.export.actual_receipt.status == "written"`, `supplied_case_id == "C1"`, `output_name == "C1"` and no receipt failure. `run.export.actual_file_hashes` must contain exactly `ANSWER.md` and `REASONING.md` in that order. Under the identified run directory, read `ANSWERS/C1/ANSWER.md` and `ANSWERS/C1/REASONING.md`, inspect both texts, and compare their actual SHA256 bytes to those two hashes. The export receipt's `output_hash` is the canonical fingerprint of that filename-to-hash mapping, not either individual file hash. Keep physical outcome assertions limited to the recorded synthetic postconditions.
6. **Shutdown:** require `shutdown.admission_closed == true`, `shutdown.owner_closed == true`, empty pending/cancelled command-ID lists and `shutdown.inventory_failure == false`. Record actual start/end/elapsed/overrun values. A timeout or missing shutdown never supplies a positive completed shutdown.

This is manual JSON/file readback, not execution of product readers or private SQL. Do not inspect world/journal databases or infer post-exit source-call telemetry from them. Existing [CLI parity source](tests/test_cli_parity.py) illustrates the interfaces; its assertions are not evidence that this run passed. Missing joins remain missing rather than being supplied from historical tests.

### Keep the denominator

Create a private `summary.md` at the observation root with the source-freeze identifier, actual environment/dependency observations, the two review paths and all discrepancies. Record these disjoint capture counts over the fixed two positions:

- `exited`, `timed_out`, `launch_error`, `interrupted`, `not_attempted_or_missing`; their sum is **2**. A partially started row without final observation is `interrupted` only if actual start evidence exists; otherwise keep it `not_attempted_or_missing` and explain uncertainty.
- `attempted` counts actual child-launch attempts, including launch errors; absent observation alone does not prove an attempt. Preserve uncertainty explicitly rather than inventing a number. `exited` includes zero, nonzero and signal return codes; report those separately.
- `positive_review`, `failed_review`, `unreviewed`; their sum is also **2**. Missing/partial/unreviewed rows never disappear from the business denominator.

Two separately reviewed positives are required before describing this tiny demo as usable **for these two synthetic cases in this observed environment**. Otherwise report the observed failure/partial state and stop for diagnosis; this recipe authorizes no source fixes, ad-hoc commands or retries. Recorder setup/recording failures and an interrupted second position do not become one-of-one success.

## Limits that remain open

Same-environment source-checkout observation is **not clean reproduction**. This recipe creates no `SourceReleaseContextV1`, `SourceReleaseReceipt` or `ReproductionReceipt`. `verify_release_static` checks static copied bytes; actual `verify_release` remains unavailable. Source hashes, mode declarations and local approvals do not establish authenticated origin, protected custody or complete candidate closure.

Current dependency/lock/notice metadata and source-ownership evidence do not support a cleared package. Eight unhashed version pins, nineteen historical wheel hashes, stale API-deferred metadata and a separately required build backend are different scopes. Actual third-party artifact/license/notice joins remain incomplete. No copyright holder or contributor/employer grant is inferred; private raw documents, recordings, archives, organizer/customer/provider originals and protected references stay excluded and unrelicensed. See [RIGHTS.md](RIGHTS.md).

This recipe does not demonstrate narrative/media/model processing, all six integration surfaces, an unfamiliar profile or reviewed process adaptation. It does not claim successful restart recovery: the default synthetic clock restarts, and retained-state recovery can be denied. Actual human approval, atomic activation, native/provider participation, calibration, protected isolation/custody, four timed drills, whole-candidate review, clean install/package, 60-second video/native playback, publication and event eligibility need separate evidence and authority. The broader [README](README.md) remains the current interface guide.
