"""Export a retained platform record; never call a provider or execute actions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _section(title, value):
    # Indented JSON keeps supplied Markdown inert and preserves all selected fields.
    return "\n## " + title + "\n\n" + "\n".join("    " + line for line in _json_bytes(value).decode().splitlines()) + "\n"


def _read_record(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_000_000:
        raise ValueError("invalid_record_file")
    raw = path.read_bytes()

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    record = json.loads(raw, object_pairs_hook=unique,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid_json_constant")))
    if not isinstance(record, dict):
        raise ValueError("invalid_record")
    job = record.get("job", record)
    if not isinstance(job, dict) or job.get("schema_version") != "proofkey-model-job-v1":
        raise ValueError("retained_job_required")
    case_id = job.get("case_id")
    if not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", case_id):
        raise ValueError("unsafe_case_id")
    evidence = job.get("input")
    if not isinstance(evidence, dict) or evidence.get("case_id") != case_id:
        raise ValueError("input_identity_mismatch")
    if "input" in record and record is not job and record["input"] != evidence:
        raise ValueError("record_input_mismatch")
    if not isinstance(job.get("status"), str) or not job["status"]:
        raise ValueError("job_status_required")
    candidate = job.get("candidate")
    if candidate is not None and not isinstance(candidate, dict):
        raise ValueError("invalid_candidate")
    if candidate and "input_hash" in candidate and candidate["input_hash"] != job.get("input_hash"):
        raise ValueError("candidate_input_mismatch")
    return raw, record, job


def export_record(record_path, output_root, attachments=()):
    """Package development evidence without replacing failed or missing output.

    This adapter deliberately cannot assert official Reality Test provenance.
    The original record is retained byte for byte; INPUT.json is an extraction,
    not the provider's original wire request. A valid job is not a correct answer.
    """
    raw, record, job = _read_record(record_path)
    case_id = job["case_id"]
    candidate = job.get("candidate")
    evidence_class = "development"
    source_hash = hashlib.sha256(raw).hexdigest()
    artifacts = {}
    for index, path in enumerate(attachments, 1):
        path = Path(path)
        if (path.is_symlink() or not path.is_file() or path.stat().st_size > 8_000_000
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,160}", path.name)):
            raise ValueError("invalid_attachment")
        artifacts[f"ARTIFACT-{index:03d}-{path.name}"] = path.read_bytes()
    status = {
        "case_id": case_id, "evidence_class": evidence_class,
        "official_reality_test": False,
        "record_status": record.get("status"), "job_status": job["status"],
        "step_index": job.get("step_index"), "source": job.get("source", record.get("source")),
        "input_hash_as_recorded": job.get("input_hash"),
        "source_record_sha256": source_hash,
        "created_at": job.get("created_at"), "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }
    answer = (f"# Answer — {case_id}\n\n"
              "Evidence class: **development**. This is not an official unseen Reality Test result.\n\n"
              "Generated offline from a retained system record. No provider was called. "
              "No operational action was executed by this export. A succeeded model job only means "
              "the system retained an accepted proposal; it does not establish correctness or business completion.\n")
    if candidate is None:
        answer += "\nNo accepted model answer is present. The failure or no-output state below is retained without a substitute.\n"
    answer += _section("Received input and run identity", status)
    answer += "\nThe complete stored input field from the retained job is preserved in `INPUT.json`; this is not necessarily the provider wire request or system prompt. The original record is preserved byte for byte in `SOURCE_RECORD.json`.\n"
    answer += "\nA retained candidate is not the raw provider response. Raw response text is included only if present in the source record or a supplied supplemental artifact; missing text is not reconstructed.\n"
    if artifacts:
        answer += _section("Supplemental source artifacts (unmodified)", list(artifacts))
    answer += _section("Actual retained model output", {"candidate": candidate})
    answer += "\nAny next action or operator review above is a proposal unless an execution receipt below independently records it.\n"
    detail = record.get("detail") or {}
    if not isinstance(detail, dict):
        detail = {}
    answer += _section("Recorded attempts, actions and execution evidence", {
        "transaction": job.get("transaction"), "provider_receipt": job.get("receipt"),
        "recorded_actions": detail.get("actions"), "recorded_decisions": detail.get("decisions"),
        "recorded_reviews": detail.get("reviews"), "recorded_states": detail.get("states"),
        "detail_external_effects": detail.get("external_effects"),
    })
    answer += "\nA null field means that this record does not supply that evidence; it is not a confirmed zero. Physical delivery, operational acceptance and payment remain separate facts.\n"
    answer += _section("Failures and final observed result", {
        "record_status": record.get("status"), "job_status": job["status"],
        "error": job.get("error"), "record_error": record.get("error"),
        "evaluation": job.get("evaluation"), "checks": record.get("checks"),
        "state_agreement": record.get("state_agreement"),
        "wait_target_agreement": record.get("wait_target_agreement"),
    })
    public = {key: candidate[key] for key in ("evidence_event_ids", "evidence_refs", "rationale", "uncertainty", "missing_information", "required_approvals")
              if candidate is not None and key in candidate}
    reasoning = (f"# Public rationale and evidence — {case_id}\n\n"
                 "This file exposes only the recorded public evidence references, rationale, uncertainty and approval requirements. "
                 "It does not reconstruct hidden model reasoning or correct the model's answer.\n")
    if not public:
        reasoning += "\nNo public rationale was retained in an accepted candidate. Consult the preserved failure and source record.\n"
    reasoning += _section("Recorded public rationale", public)
    reasoning += _section("Evidence limits", {
        "evidence_class": evidence_class, "official_reality_test": False,
        "source_record_sha256": source_hash,
        "input_file": "INPUT.json", "source_record_file": "SOURCE_RECORD.json",
        "model_evaluation": job.get("evaluation"), "run_checks": record.get("checks"),
        "note": "Comparisons are retained observations, not independent human calibration. Absent execution receipts do not prove completion.",
    })
    contents = {"SOURCE_RECORD.json": raw, "INPUT.json": _json_bytes(job["input"]),
                "ANSWER.md": answer.encode("utf-8"), "REASONING.md": reasoning.encode("utf-8"), **artifacts}
    output_root = Path(output_root).absolute()
    if any(path.is_symlink() for path in (output_root, *output_root.parents)):
        raise ValueError("symlink_output_refused")
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / case_id
    directory.mkdir()  # exclusive: even a partial prior export is never replaced
    hashes = {}
    for name, payload in contents.items():
        with (directory / name).open("xb") as stream:
            stream.write(payload)
        if (directory / name).read_bytes() != payload:
            raise ValueError("export_readback_failed")
        hashes[name] = hashlib.sha256(payload).hexdigest()
    receipt = {"schema_version": "dwelly-submission-export-v1", "case_id": case_id,
               "evidence_class": evidence_class, "official_reality_test": False,
               "job_status": job["status"], "source_sha256": source_hash,
               "files": hashes, "network_calls": 0, "actions_executed_by_export": 0}
    with (directory / "EXPORT.json").open("xb") as stream:
        stream.write(_json_bytes(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path, help="Retained proofkey-model-job-v1 JSON or a record containing job")
    parser.add_argument("--output", required=True, type=Path, help="Parent directory for exclusive <case-id> output")
    parser.add_argument("--attachment", action="append", type=Path, default=[],
                        help="Optional raw response or log retained byte for byte; may be repeated")
    parser.add_argument("--evidence-class", choices=("development",), default="development",
                        help="Official challenge provenance is not available in this adapter")
    args = parser.parse_args(argv)
    try:
        receipt = export_record(args.record, args.output, args.attachment)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as error:
        code = str(error) if isinstance(error, ValueError) and re.fullmatch(r"[a-z_]+", str(error)) else type(error).__name__
        print(json.dumps({"exported": False, "error": code}), file=sys.stderr)
        return 1
    print(json.dumps({"exported": True, **receipt}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
