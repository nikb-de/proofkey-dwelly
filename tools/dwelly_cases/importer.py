"""Bounded, non-executing import of Dwelly's narrative logistics cases.

Only the snapshot crosses the proposed-agent boundary. Index text, reference
actions, full-source hashes and later evidence are deliberately evaluator-only.
"""
from datetime import datetime, timezone
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from urllib.parse import unquote, urlsplit

TRACK = "Delivery & Logistics"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
EVENT = re.compile(
    r'<a id="event-(\d{3})"></a>\s*\n'
    r'## (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC) — event (\d{3})\s*\n'
)
LINK = re.compile(r'\[[^\]\n]*\]\(([^)\n]+)\)')
STAGES = {"Context", "Escalation", "Agent action", "Follow-through / confirmation"}


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def read_bytes(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("source_not_regular_file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("source_file_too_large")
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("source_file_too_large")
    return data


def local_links(text, case):
    """Validate every local link; external references are never fetched."""
    if (re.search(r"^\s*\[[^\]\n]+\]:", text, re.M)
            or re.search(r"\[[^\]\n]*\]\s*\[[^\]\n]*\]", text)
            or re.search(r"<[^>]*\b(?:href|src)\s*=", text, re.I)):
        raise ValueError("unsupported_link_markup")
    found = []
    for raw in LINK.findall(text):
        target = urlsplit(raw.strip())
        if target.scheme or target.netloc:
            if target.scheme not in {"https", "http", "mailto"} or target.netloc and not target.scheme:
                raise ValueError("unsupported_link_scheme")
            continue
        name = unquote(target.path)
        if not name:
            continue
        relative = PurePosixPath(name)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in name
                or "\x00" in name or target.query):
            raise ValueError("unsafe_local_link")
        path = case.joinpath(*relative.parts)
        if any(part.is_symlink() for part in (path, *path.parents) if part != case.parent):
            raise ValueError("symlink_local_link")
        if not path.is_file() or not path.resolve().is_relative_to(case.resolve()):
            raise ValueError("missing_or_escaped_local_link")
        found.append(relative.as_posix())
    return found


def parse_events(text):
    matches = list(EVENT.finditer(text))
    if not 3 <= len(matches) <= 256 or len(re.findall(r"^## .*event ", text, re.M)) != len(matches):
        raise ValueError("invalid_event_headers")
    events = []
    for i, match in enumerate(matches):
        anchor, timestamp, number = match.groups()
        if anchor != number or int(number) != i + 1:
            raise ValueError("event_sequence_mismatch")
        try:
            occurred = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError("invalid_event_timestamp") from None
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[match.end():end].strip()
        metadata, separator, body = section.partition("\n\n")
        values = {}
        for line in metadata.splitlines():
            field = re.fullmatch(r"- \*\*(Stage|Channel|From|To):\*\* (.+)", line)
            if not field or field[1] in values:
                raise ValueError("invalid_event_metadata")
            values[field[1]] = field[2].strip()
            if not values[field[1]]:
                raise ValueError("blank_event_metadata")
        if set(values) != {"Stage", "Channel", "From", "To"} or not separator or not body.strip():
            raise ValueError("missing_event_metadata_or_body")
        if values["Stage"] not in STAGES:
            raise ValueError("unknown_event_stage")
        event = {"event_id": f"event-{number}", "occurred_at": occurred.isoformat(),
                 "stage": values["Stage"], "channel": values["Channel"],
                 "sender": values["From"], "recipients": values["To"], "body": body.strip()}
        if events and event["occurred_at"] < events[-1]["occurred_at"]:
            raise ValueError("nonchronological_events")
        events.append(event)
    actions = [i for i, event in enumerate(events) if event["stage"] == "Agent action"]
    if len(actions) != 1 or actions[0] < 2:
        raise ValueError("missing_or_ambiguous_decision_point")
    cutoff = actions[0]
    before, after = events[:cutoff], events[cutoff + 1:]
    if (any(e["stage"] not in {"Context", "Escalation"} for e in before)
            or not any(e["stage"] == "Context" for e in before)
            or before[-1]["stage"] != "Escalation"
            or any(e["stage"] != "Follow-through / confirmation" for e in after)):
        raise ValueError("invalid_stage_sequence")
    return events, cutoff


def case_files(case):
    """Bound traversal and bytes before reading any case payload."""
    files, pending, count, size = [], [(case, 0)], 0, 0
    while pending:
        directory, depth = pending.pop()
        for path in directory.iterdir():
            count += 1
            if count > 128 or path.is_symlink():
                raise ValueError("invalid_case_file_inventory")
            if path.is_dir():
                if depth >= 8:
                    raise ValueError("case_directory_depth_exceeded")
                pending.append((path, depth + 1))
            elif path.is_file():
                length = path.stat().st_size
                size += length
                if length > MAX_FILE_BYTES or size > MAX_TOTAL_BYTES or len(files) >= 64:
                    raise ValueError("case_file_budget_exceeded")
                files.append(path)
            else:
                raise ValueError("source_not_regular_file")
    if len(files) < 2:
        raise ValueError("invalid_case_file_inventory")
    return sorted(files)


def parse_case(case_dir):
    case = Path(case_dir)
    if case.is_symlink() or not case.is_dir() or not re.fullmatch(r"\d{3}", case.name):
        raise ValueError("invalid_case_directory")
    if case.parent.name != TRACK or case.parent.is_symlink():
        raise ValueError("unsupported_track")
    case = case.resolve()
    files = case_files(case)
    source_bytes = {path.relative_to(case).as_posix(): read_bytes(path) for path in files}
    if "history.md" not in source_bytes or "index.md" not in source_bytes:
        raise ValueError("missing_case_documents")
    try:
        history = source_bytes["history.md"].decode("utf-8")
        index = source_bytes["index.md"].decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("invalid_document_encoding") from None
    local_links(index, case)
    events, cutoff = parse_events(history)
    first_seen = {}
    prefix = f"{TRACK}/{case.name}"
    for event in events:
        event["source_ref"] = f'{prefix}/history.md#{event["event_id"]}'
        for name in local_links(event["body"], case):
            if name.startswith("attachments/"):
                first_seen.setdefault(name, event["event_id"])
    available_ids = {e["event_id"] for e in events[:cutoff]}
    attachments = [{"path": name, "sha256": sha256(source_bytes[name]).hexdigest(),
                    "size": len(source_bytes[name]), "first_seen_event": first_seen[name]}
                   for name in sorted(first_seen) if first_seen[name] in available_ids]
    snapshot = {"schema_version": "dwelly-snapshot-v1", "case_id": f"delivery-logistics-{case.name}",
                "track": TRACK, "cutoff_event": events[cutoff - 1]["event_id"],
                "events": events[:cutoff], "attachments": attachments}
    snapshot["input_hash"] = digest(snapshot)
    reference = {"schema_version": "dwelly-reference-v1", "case_id": snapshot["case_id"],
                 "input_hash": snapshot["input_hash"], "action": events[cutoff],
                 "later_events": events[cutoff + 1:], "index_source": f"{prefix}/index.md"}
    inventory = {"files": [{"path": f"{prefix}/{name}", "sha256": sha256(data).hexdigest(),
                             "size": len(data)} for name, data in sorted(source_bytes.items())],
                 "total_events": len(events), "total_attachments": sum(n.startswith("attachments/") for n in source_bytes)}
    return snapshot, reference, inventory


def prepare_destination(source, output):
    source, output = Path(source), Path(output)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("invalid_source_directory")
    source = source.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError("output_already_exists")
    output = output.resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("source_output_overlap")
    return source, output


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


@contextmanager
def new_output(output):
    """Reserve exclusively; publish a completed sibling tree in one rename.

    On abrupt process death an empty reservation/staging tree can remain, but
    no partial final bundle becomes readable. A subsequent run uses a fresh
    destination; automatic crash cleanup is intentionally not claimed.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(mode=0o700)
    identity = (output.stat().st_dev, output.stat().st_ino)
    staging = None
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.building-", dir=output.parent))
        yield staging
        if (output.is_symlink() or not output.is_dir()
                or (output.stat().st_dev, output.stat().st_ino) != identity or any(output.iterdir())):
            raise ValueError("output_reservation_changed")
        staging.replace(output)
        staging = None
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
        if (output.is_dir() and not output.is_symlink()
                and (output.stat().st_dev, output.stat().st_ino) == identity and not any(output.iterdir())):
            output.rmdir()


def import_cases(source, output, expected_cases=50):
    source, output = prepare_destination(source, output)
    track = source / TRACK
    if track.is_symlink() or not track.is_dir():
        raise ValueError("missing_logistics_track")
    if type(expected_cases) is not int or not 1 <= expected_cases <= 256:
        raise ValueError("invalid_expected_case_count")
    folders = sorted(p for p in track.iterdir() if re.fullmatch(r"\d{3}", p.name))
    if len(folders) != expected_cases:
        raise ValueError("case_count_mismatch")
    total_size = 0
    for folder in folders:
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("invalid_case_directory")
        total_size += sum(path.stat().st_size for path in case_files(folder))
        if total_size > MAX_TOTAL_BYTES:
            raise ValueError("dataset_too_large")
    parsed = [parse_case(folder) for folder in folders]
    inventory = [entry for _, _, item in parsed for entry in item["files"]]
    if sum(f["size"] for f in inventory) > MAX_TOTAL_BYTES:
        raise ValueError("dataset_too_large")
    manifest = {"schema_version": "dwelly-bundle-v1", "source_type": "local_untrusted_public_examples",
                "source_root": str(source), "track": TRACK, "case_count": len(parsed),
                "event_count": sum(i["total_events"] for _, _, i in parsed),
                "attachment_count": sum(i["total_attachments"] for _, _, i in parsed),
                "visible_attachment_count": sum(len(s["attachments"]) for s, _, _ in parsed),
                "files": inventory, "source_inventory_hash": digest(inventory),
                "case_ids": [s["case_id"] for s, _, _ in parsed],
                "qualification": "development_only_unqualified", "heldout_cases": 0}
    with new_output(output) as staging:
        for entry in inventory:
            data = read_bytes(source / entry["path"])
            if sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("source_changed_during_import")
            destination = staging / "raw" / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(data)
        ledger = []
        for snapshot, reference, _ in parsed:
            case_id = snapshot["case_id"]
            write_json(staging / "agent" / f"{case_id}.json", snapshot)
            write_json(staging / "evaluation" / f"{case_id}.json", reference)
            for attachment in snapshot["attachments"]:
                relative = attachment["path"]
                original = staging / "raw" / TRACK / case_id[-3:] / relative
                destination = staging / "agent/assets" / case_id / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
            ledger.append({"case_id": case_id, "origin": "local_public_synthetic",
                           "independence_group": "dwelly-logistics-template-family",
                           "split": "development", "input_hash": snapshot["input_hash"],
                           "reference_hash": digest(reference), "reference_provenance": reference["action"]["source_ref"],
                           "required_behavior": "source-grounded next communication; no operational effect",
                           "ambiguity": "recorded_action_is_not_unique_ground_truth",
                           "exclusion": "semantic_quality_unassessed", "tags": ["logistics", "synthetic"]})
        with (staging / "ledger.jsonl").open("xb") as stream:
            for row in ledger:
                stream.write(canonical_bytes(row) + b"\n")
        write_json(staging / "manifest.json", manifest)
    return manifest
