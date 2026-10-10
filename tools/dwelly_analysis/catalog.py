"""Fixed, source-hash-checked local catalog. No caller-selected filesystem paths."""
import hashlib
import json
from pathlib import Path

from .widget import MAX_BYTES, validate_document

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "datasets" / "case-state-widget-v1" / "manifest.json"
_PATHS = {
    "case-002": "case-state-widget/case-002.json",
    "case-002-n4": "case-state-widget/examples/case-002-channel-failure.json",
    "minimal": "case-state-widget/examples/minimal.json",
}
_LEGACY_IDS = tuple(_PATHS)
_TEAM_PATHS = {
    'team-001': 'case-state-widget/cases/001.json',
    'team-002': 'case-state-widget/cases/002.json',
    'team-002-n4': 'case-state-widget/cases/002-N4.json',
}
_PATHS.update(_TEAM_PATHS)


def _source_path(case_id):
    if type(case_id) is not str or case_id not in _PATHS:
        raise ValueError("Unknown catalog case")
    return ROOT / _PATHS[case_id]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _decode(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON byte limit exceeded")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise ValueError("Invalid source JSON") from exc


def _manifest(team=False):
    try:
        path = ROOT / 'datasets/team-widget-v1/manifest.json' if team else MANIFEST_PATH
        value = _decode(path.read_bytes())
        if value["schema_version"] != "proofkey-widget-manifest-v1" or value["split"] != "development" or value["qualification"] != "author_labels_unvalidated":
            raise ValueError("Invalid catalog manifest")
        rows = value["cases"]
        if type(rows) is not list or [row["id"] for row in rows] != list(_TEAM_PATHS if team else _LEGACY_IDS):
            raise ValueError("Invalid catalog entries")
        for row in rows:
            if row["path"] != _PATHS[row["id"]] or len(row["source_sha256"]) != 64:
                raise ValueError("Invalid catalog binding")
        return value
    except (OSError, KeyError, TypeError) as exc:
        raise ValueError("Catalog unavailable") from exc


def get_document(case_id):
    path = _source_path(case_id)
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("Source outside catalog root") from exc
    # Reject links both at the file and in its path within the checkout. Source
    # provenance is tied to the pinned checkout, never a linked external file.
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError("Linked catalog source is not allowed")
        if component == ROOT:
            break
    manifest = _manifest(True) if case_id in _TEAM_PATHS else _manifest()
    row = next(row for row in manifest["cases"] if row["id"] == case_id)
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ValueError("Source unavailable") from exc
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != row["source_sha256"]:
        raise ValueError("Source hash mismatch")
    return validate_document(_decode(raw))


def load_catalog(group=None):
    if group not in (None, 'legacy', 'team'):
        raise ValueError('Unknown catalog group')
    manifests = ([_manifest()] if group == 'legacy' else [_manifest(True)] if group == 'team'
                 else [_manifest(), _manifest(True)])
    rows = []
    for manifest in manifests:
        for entry in manifest["cases"]:
            document = get_document(entry["id"])
            rows.append({"id": entry["id"], "title": document["title"], "steps": len(document["steps"]),
                         "family_id": entry["family_id"], "qualification": manifest["qualification"],
                         "split": manifest["split"], "kind": entry["kind"],
                         "source_sha256": entry["source_sha256"], "source_commit": manifest["source_commit"]})
    return rows
