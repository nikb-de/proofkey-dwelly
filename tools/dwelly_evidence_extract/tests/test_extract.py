import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('tools.dwelly_evidence_extract.extract'),
                             'attachment extraction implementation missing')
        self.module = importlib.import_module('tools.dwelly_evidence_extract.extract')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_case_path_escape_rejected_without_output(self):
        source = self.root / 'source'
        source.mkdir()
        with self.assertRaisesRegex(ValueError, 'unsafe_case_id'):
            self.module.extract_attachment(source, self.root / 'out', '../outside', 'x.pdf')
        self.assertFalse((self.root / 'out').exists())

    def test_attachment_path_escape_rejected_without_output(self):
        source = self.root / 'source'
        source.mkdir()
        with self.assertRaisesRegex(ValueError, 'unsafe_attachment_name'):
            self.module.extract_attachment(source, self.root / 'out', '001', '../x.pdf')
        self.assertFalse((self.root / 'out').exists())

    def test_source_symlink_rejected(self):
        attachments = self.root / 'source' / '001' / 'attachments'
        attachments.mkdir(parents=True)
        external = self.root / 'outside.pdf'
        external.write_bytes(b'outside')
        (attachments / 'x.pdf').symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'linked_source'):
            self.module.extract_attachment(self.root / 'source', self.root / 'out', '001', 'x.pdf')
        self.assertFalse((self.root / 'out').exists())

    def test_invalid_pdf_records_failure_and_preserves_source(self):
        attachments = self.root / 'source' / '001' / 'attachments'
        attachments.mkdir(parents=True)
        original = b'not a pdf\n'
        (attachments / 'bad.pdf').write_bytes(original)
        result = self.module.extract_attachment(self.root / 'source', self.root / 'out', '001', 'bad.pdf')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'extractor_nonzero_exit')
        self.assertEqual((attachments / 'bad.pdf').read_bytes(), original)
        self.assertFalse((self.root / 'out' / '001' / 'attachments' / 'bad.pdf.txt').exists())

    def test_existing_sidecar_is_not_overwritten(self):
        attachments = self.root / 'source' / '001' / 'attachments'
        attachments.mkdir(parents=True)
        (attachments / 'bad.pdf').write_bytes(b'not a pdf')
        target = self.root / 'out' / '001' / 'attachments' / 'bad.pdf.txt'
        target.parent.mkdir(parents=True)
        target.write_text('existing')
        with self.assertRaisesRegex(ValueError, 'output_exists'):
            self.module.extract_attachment(self.root / 'source', self.root / 'out', '001', 'bad.pdf')
        self.assertEqual(target.read_text(), 'existing')

    def test_pending_completion_rejects_changed_source(self):
        attachments = self.root / 'source' / '001' / 'attachments'
        attachments.mkdir(parents=True)
        raw = attachments / 'bad.png'
        raw.write_bytes(b'original')
        self.module.extract_all(self.root / 'source', self.root / 'out')
        raw.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'source_hash_changed'):
            self.module.complete_pending(self.root / 'source', self.root / 'out', ocr_binary='/missing')


if __name__ == '__main__':
    unittest.main()
