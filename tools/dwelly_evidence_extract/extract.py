"""Extract source attachment text without treating it as trusted evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote


MAX_BYTES = 25 * 1024 * 1024
MAX_OUTPUT = 4 * 1024 * 1024
PDFTOTEXT = '/opt/homebrew/bin/pdftotext'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_path(root, relative, *, source=False):
    root = Path(root)
    path = root / relative
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError('linked_source' if source else 'linked_output')
        if component == root:
            break
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('path_escape')
    return path


def run_tool(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        return None, 'extractor_timeout'
    except OSError:
        return None, 'extractor_unavailable'
    if result.returncode:
        return None, 'extractor_nonzero_exit'
    if len(result.stdout) > MAX_OUTPUT:
        return None, 'extraction_too_large'
    try:
        return result.stdout.decode('utf-8'), None
    except UnicodeError:
        return None, 'invalid_utf8_output'


def extract_attachment(source_root, output_root, case_id, filename, *, ocr_binary=None):
    if re.fullmatch(r'[0-9]{3}', case_id) is None:
        raise ValueError('unsafe_case_id')
    if not filename or filename in {'.', '..'} or '/' in filename or '\\' in filename or '\x00' in filename:
        raise ValueError('unsafe_attachment_name')
    relative = Path(case_id) / 'attachments' / filename
    source = checked_path(source_root, relative, source=True)
    target = checked_path(output_root, str(relative) + '.txt')
    ocr_path = checked_path(output_root, str(relative) + '.ocr.json')
    if target.exists() or ocr_path.exists():
        raise ValueError('output_exists')
    raw = source.read_bytes()
    entry = {'case_id': case_id, 'filename': filename, 'source_path': str(source.absolute()),
             'source_relative_path': relative.as_posix(), 'source_sha256': digest(raw),
             'source_bytes': len(raw), 'sidecar_path': None, 'sidecar_sha256': None,
             'qualification': 'unverified_extracted_source_text', 'status': 'failed',
             'extractor': None, 'raw_source_unchanged': None}
    text, error, ocr = None, None, None
    if len(raw) > MAX_BYTES:
        error = 'source_too_large'
    elif source.suffix.lower() == '.pdf':
        entry['extractor'] = 'poppler_pdftotext_layout_utf8'
        text, error = run_tool([PDFTOTEXT, '-layout', '-enc', 'UTF-8', str(source), '-'])
    elif source.suffix.lower() == '.png':
        entry['extractor'] = 'macos_vision_accurate_no_language_correction'
        if ocr_binary is None:
            error = 'ocr_extractor_unavailable'
        else:
            payload, error = run_tool([str(ocr_binary), str(source)])
            if error is None:
                try:
                    ocr = json.loads(payload)
                    text = ocr['text']
                    if not isinstance(text, str) or not isinstance(ocr['observations'], list):
                        raise ValueError
                except (ValueError, KeyError, TypeError):
                    error = 'invalid_ocr_output'
    else:
        entry['status'] = 'unsupported'
        error = 'unsupported_attachment_type'
    entry['raw_source_unchanged'] = digest(source.read_bytes()) == entry['source_sha256']
    if not entry['raw_source_unchanged']:
        error = 'source_changed_during_extraction'
    if error:
        entry['error'] = error
        return entry
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(text.encode('utf-8'))
    entry.update(sidecar_path=str(target.absolute()), sidecar_sha256=digest(target.read_bytes()),
                 text_characters=len(text), status='extracted_unverified' if text.strip() else 'empty_extraction')
    if ocr is not None:
        encoded = json.dumps(ocr, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8') + b'\n'
        with ocr_path.open('xb') as stream:
            stream.write(encoded)
        confidences = [item['confidence'] for item in ocr['observations']]
        entry.update(ocr_path=str(ocr_path.absolute()), ocr_sha256=digest(encoded),
                     ocr_observations=len(confidences),
                     minimum_ocr_confidence=min(confidences) if confidences else None,
                     note='OCR extracts visible text only; image content and source truth remain unverified.')
    return entry


def extract_all(source_root, output_root, *, ocr_binary=None):
    source_root, output_root = Path(source_root), Path(output_root)
    if output_root.exists():
        raise ValueError('output_root_exists')
    entries, missing, cases = [], [], []
    for case in sorted(source_root.iterdir()):
        if not case.is_dir() or re.fullmatch(r'[0-9]{3}', case.name) is None:
            continue
        cases.append(case.name)
        attachments = checked_path(source_root, Path(case.name) / 'attachments', source=True)
        if attachments.exists():
            for source in sorted(attachments.iterdir()):
                if not source.is_file():
                    raise ValueError('unexpected_attachment_entry')
                entries.append(extract_attachment(source_root, output_root, case.name, source.name,
                                                  ocr_binary=ocr_binary))
        for name in ('index.md', 'history.md'):
            path = checked_path(source_root, Path(case.name) / name, source=True)
            if path.is_file():
                for match in re.findall(r'\]\(<?(attachments/[^)>]+)>?\)', path.read_text()):
                    reference = unquote(match)
                    if '..' in Path(reference).parts or not (case / reference).is_file():
                        missing.append({'case_id': case.name, 'document': name, 'reference': reference})
    summary = {'schema_version': 'proofkey-attachment-extraction-v1',
               'source_root': str(source_root.absolute()), 'output_root': str(output_root.absolute()),
               'qualification': 'unverified_extraction_not_model_inference_or_source_truth',
               'cases': cases, 'case_count': len(cases), 'attachment_count': len(entries),
               'status_counts': dict(Counter(item['status'] for item in entries)),
               'missing_referenced_attachments': missing, 'attachments': entries,
               'live_calls': 0, 'operational_effects': 0}
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / 'manifest.json').open('x') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return summary


def complete_pending(source_root, output_root, *, ocr_binary):
    """Explicit local extraction retry; preserve the first manifest and complete only missing text."""
    source_root, output_root = Path(source_root), Path(output_root)
    manifest_path = checked_path(output_root, 'manifest.json')
    initial = manifest_path.read_bytes()
    summary = json.loads(initial)
    if (summary['source_root'] != str(source_root.absolute())
            or summary['output_root'] != str(output_root.absolute())):
        raise ValueError('manifest_root_mismatch')
    for entry in summary['attachments']:
        source = checked_path(source_root, entry['source_relative_path'], source=True)
        if digest(source.read_bytes()) != entry['source_sha256']:
            raise ValueError('source_hash_changed')
    updated = []
    for entry in summary['attachments']:
        if entry['status'] == 'failed' and entry.get('sidecar_path') is None:
            entry = extract_attachment(source_root, output_root, entry['case_id'], entry['filename'],
                                       ocr_binary=ocr_binary)
        updated.append(entry)
    summary['attachments'] = updated
    summary['status_counts'] = dict(Counter(item['status'] for item in updated))
    backup = checked_path(output_root, 'manifest.initial.json')
    if not backup.exists():
        with backup.open('xb') as stream:
            stream.write(initial)
    temporary = checked_path(output_root, 'manifest.completed.json')
    with temporary.open('x') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    temporary.replace(manifest_path)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ocr-binary', type=Path)
    parser.add_argument('--complete-pending', action='store_true',
                        help='Explicitly retry failed local extraction only; preserve initial manifest')
    args = parser.parse_args()
    operation = complete_pending if args.complete_pending else extract_all
    result = operation(args.source, args.output, ocr_binary=args.ocr_binary)
    print(json.dumps({key: result[key] for key in ('case_count', 'attachment_count', 'status_counts',
                                                   'missing_referenced_attachments', 'output_root')}))
    return 0 if all(x['status'] == 'extracted_unverified' for x in result['attachments']) else 2
