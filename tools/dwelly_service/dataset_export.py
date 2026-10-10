"""Export one explicitly pinned model-visible input; no labels or evaluation run."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys

from .cases import HASH, IDENTIFIER, _canonical


_PROVENANCE_KEYS = {'source_kind', 'source_id', 'collected_at'}
_SOURCE_KINDS = ('local_fixture', 'synthetic', 'human_authored', 'imported')
_RFC3339 = re.compile(r'\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})', re.ASCII)


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _aware_datetime(value, code, *, rfc3339=False):
    try:
        if type(value) is str:
            if rfc3339:
                _require(_RFC3339.fullmatch(value) is not None, code)
            parsed = datetime.fromisoformat(value.replace('z', '+00:00').replace('Z', '+00:00'))
        else:
            _require(isinstance(value, datetime) and not rfc3339, code)
            parsed = value
        _require(parsed.tzinfo is not None and parsed.utcoffset() is not None, code)
        return parsed
    except (ValueError, TypeError, OverflowError):
        raise ValueError(code) from None


def export_decision_input(store, *, case_id, revision, expected_snapshot_hash, input_id, provenance, as_of):
    """Read a specific revision through CaseStore.get's full-history validation.

    Both SQLite CaseStore and PostgresCaseStore provide this contract. The
    supplied provenance is operator-authored metadata, not a verified origin
    claim. The cutoff checks occurrence time; v1 has no observed_at field.
    """
    _require(type(revision) is int and revision >= 0, 'explicit_revision_required')
    _require(type(expected_snapshot_hash) is str and HASH.fullmatch(expected_snapshot_hash) is not None,
             'expected_snapshot_hash_required')
    _require(type(case_id) is str and IDENTIFIER.fullmatch(case_id) is not None, 'invalid_case_id')
    _require(type(input_id) is str and IDENTIFIER.fullmatch(input_id) is not None, 'invalid_input_id')
    _require(type(provenance) is dict and set(provenance) == _PROVENANCE_KEYS, 'invalid_provenance')
    _require(type(provenance['source_kind']) is str and provenance['source_kind'] in _SOURCE_KINDS,
             'invalid_provenance')
    _require(type(provenance['source_id']) is str and len(provenance['source_id']) >= 1, 'invalid_provenance')
    _aware_datetime(provenance['collected_at'], 'invalid_provenance', rfc3339=True)
    cutoff = _aware_datetime(as_of, 'invalid_as_of')
    # Store.get validates every stored revision and the immutable hash chain;
    # an explicit revision avoids accidentally exporting a later case head.
    snapshot = store.get(case_id, revision)
    _require(snapshot['case_id'] == case_id and snapshot['revision'] == revision, 'source_mismatch')
    _require(snapshot['snapshot_hash'] == expected_snapshot_hash, 'snapshot_hash_mismatch')
    for event in snapshot['events']:
        _require(_aware_datetime(event['occurred_at'], 'invalid_event_time') <= cutoff, 'evidence_after_as_of')
    # Build a closed envelope, and detach all nested data from caller/store.
    return json.loads(_canonical({
        'schema_version': 'proofkey-decision-input-v1', 'visibility': 'model_visible', 'input_id': input_id,
        'source': {'case_id': case_id, 'revision': revision, 'snapshot_hash': expected_snapshot_hash},
        'snapshot': snapshot, 'provenance': provenance,
    }))


def _write_exclusive(path, value):
    """Write private bytes once; remove an incomplete file only if still ours."""
    encoded = (_canonical(value) + '\n').encode('utf-8')
    path = Path(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    identity = os.fstat(descriptor)
    try:
        remaining = memoryview(encoded)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError('incomplete write')
            remaining = remaining[written:]
        os.fsync(descriptor)
    except BaseException:
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                path.unlink()
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case-id', required=True)
    parser.add_argument('--revision', type=int, required=True)
    parser.add_argument('--expected-snapshot-hash', required=True)
    parser.add_argument('--input-id', required=True)
    parser.add_argument('--source-kind', choices=_SOURCE_KINDS, required=True)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--collected-at', required=True)
    parser.add_argument('--as-of', required=True)
    args = parser.parse_args(argv)
    owner = None
    try:
        # The CLI opens only PostgreSQL. Opening a SQLite JobStore would run
        # benchmark recovery; callers reuse their existing CaseStore instead.
        _require(bool(os.environ.get('PROOFKEY_DATABASE_URL')), 'database_url_required')
        from .postgres import PostgresCaseStore
        store = PostgresCaseStore(os.environ['PROOFKEY_DATABASE_URL'],
            schema=os.environ.get('PROOFKEY_DATABASE_SCHEMA', 'public'), max_size=1)
        owner = store
        value = export_decision_input(store, case_id=args.case_id, revision=args.revision,
            expected_snapshot_hash=args.expected_snapshot_hash, input_id=args.input_id,
            provenance={'source_kind': args.source_kind, 'source_id': args.source_id, 'collected_at': args.collected_at},
            as_of=args.as_of)
        _write_exclusive(args.output, value)
        print(json.dumps({'exported': True, 'input_id': args.input_id, 'revision': args.revision}))
        return 0
    except FileExistsError:
        print(json.dumps({'exported': False, 'error': 'output_exists'}), file=sys.stderr)
        return 1
    except (ValueError, OSError, ImportError):
        print(json.dumps({'exported': False, 'error': 'dataset_export_failed'}), file=sys.stderr)
        return 1
    finally:
        if owner is not None:
            owner.close()


if __name__ == '__main__':
    sys.exit(main())
