"""Exercise real loopback routes and private artifact persistence; no providers."""
import http.client
import contextlib
import io
import json
import re
from urllib.parse import urljoin
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools.dwelly_analysis import catalog, server, __main__ as cli


class AnalysisServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = server.create_server(port=0, runs_dir=Path(self.temp.name))
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.app.server_address[1]

    def tearDown(self):
        self.app.shutdown()
        self.app.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        request_headers = {'Content-Type': 'application/json', 'X-ProofKey-Request': 'analysis-v1'}
        request_headers.update(headers or {})
        connection.request(method, path, None if body is None else json.dumps(body), request_headers)
        response = connection.getresponse()
        raw = response.read()
        result = json.loads(raw) if response.getheader('Content-Type', '').startswith('application/json') else raw
        status, response_headers = response.status, dict(response.getheaders())
        connection.close()
        return status, result, response_headers

    def selector(self):
        status, step, _ = self.request('GET', '/api/cases/case-002/steps/3')
        self.assertEqual(status, 200)
        return {'case_id': 'case-002', 'step_index': 3, 'expected_input_hash': step['input']['input_hash'], 'mode': 'offline'}

    def test_catalog_and_step_keep_reference_separate_from_input(self):
        status, data, _ = self.request('GET', '/api/catalog')
        self.assertEqual(status, 200)
        self.assertEqual({item['id'] for item in data['cases']},
                         {'case-002', 'case-002-n4', 'minimal', 'team-002-n4'} |
                         {f'team-{i:03}' for i in range(1, 51)})
        self.assertEqual(len(data['cases']), 54)
        status, step, _ = self.request('GET', '/api/cases/case-002/steps/3')
        self.assertEqual(status, 200)
        self.assertEqual(step['reference']['state'], 'waiting')
        self.assertNotIn('reference', step['input'])
        self.assertNotIn('agent_state', step['input'])

    def test_source_viewer_default_json_is_served_without_double_encoding(self):
        status, document, headers = self.request('GET', '/case-002.json')
        self.assertEqual(status, 200)
        self.assertEqual(document, json.loads((server.ASSETS / 'case-002.json').read_text()))
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        status, html, _ = self.request('GET', '/source-viewer')
        self.assertEqual(status, 200)
        self.assertIn(b'app.js', html)

    def test_source_viewer_module_graph_is_served_completely(self):
        status, html, _ = self.request('GET', '/source-viewer')
        self.assertEqual(status, 200)
        scripts = re.findall(rb'<script[^>]+src="([^"]+)"', html)
        self.assertTrue(scripts)
        pending = [urljoin('/source-viewer', script.decode()) for script in scripts]
        seen = set()
        while pending:
            url = pending.pop()
            if url in seen:
                continue
            seen.add(url)
            status, content, headers = self.request('GET', url)
            self.assertEqual(status, 200, url)
            self.assertTrue(headers['Content-Type'].startswith('text/javascript'), url)
            for module in re.findall(rb'(?:import\s+(?:[^;]*?\s+from\s+)?)[\'\"]([^\'\"]+)[\'\"]', content):
                pending.append(urljoin(url, module.decode()))

    def test_run_roundtrip_is_persistent_and_has_zero_effects(self):
        with patch('tools.dwelly_model.providers.complete', side_effect=AssertionError('provider must not run')):
            status, run, _ = self.request('POST', '/api/runs', self.selector())
        self.assertEqual(status, 201)
        self.assertEqual(run['candidate']['state'], 'waiting')
        self.assertEqual(run['candidate']['waiting_for'], ['recipient'])
        self.assertEqual(run['live_calls'], 0)
        self.assertEqual(run['operational_effects'], 0)
        status, readback, _ = self.request('GET', '/api/runs/' + run['run_id'])
        self.assertEqual(status, 200)
        self.assertEqual(readback, run)
        reloaded = server.RunStore(Path(self.temp.name)).get(run['run_id'])
        self.assertEqual(reloaded, run)
        saved = Path(self.temp.name, run['run_id'] + '.json')
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)

    def test_wrong_hash_live_mode_extra_fields_rejected_without_artifact(self):
        selector = self.selector()
        for changes, expected in [({'expected_input_hash': '0' * 64}, 409), ({'mode': 'live'}, 400), ({'path': '/etc/passwd'}, 400), ({'step_index': True}, 400)]:
            with self.subTest(changes=changes):
                status, _, _ = self.request('POST', '/api/runs', dict(selector, **changes))
                self.assertEqual(status, expected)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_host_origin_and_write_header_guards(self):
        selector = self.selector()
        status, _, _ = self.request('GET', '/api/catalog', headers={'Host': 'evil.example'})
        self.assertEqual(status, 403)
        status, _, _ = self.request('POST', '/api/runs', selector, {'Origin': 'https://evil.example'})
        self.assertEqual(status, 403)
        status, _, _ = self.request('POST', '/api/runs', selector, {'X-ProofKey-Request': ''})
        self.assertEqual(status, 403)
        status, _, _ = self.request('POST', '/api/runs', selector, {'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(status, 403)
        status, _, headers = self.request('GET', '/api/catalog')
        self.assertEqual(status, 200)
        self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_path_traversal_and_unknown_routes_are_not_static_files(self):
        for path in ['/../README.md', '/%2e%2e/.env', '/api/cases/unknown', '/api/runs/../README', '/api/cases/case-002/steps/-1', '/api/cases/case-002/steps/9000']:
            with self.subTest(path=path):
                status, _, _ = self.request('GET', path)
                self.assertIn(status, (400, 404))

    def test_run_cap_and_modified_artifact_fail_closed(self):
        selector = self.selector()
        with patch.object(server, 'MAX_RUNS', 1):
            status, run, _ = self.request('POST', '/api/runs', selector)
            self.assertEqual(status, 201)
            status, _, _ = self.request('POST', '/api/runs', selector)
            self.assertEqual(status, 429)
        path = Path(self.temp.name, run['run_id'] + '.json')
        record = json.loads(path.read_text())
        record['operational_effects'] = 1
        path.write_text(json.dumps(record))
        status, _, _ = self.request('GET', '/api/runs/' + run['run_id'])
        self.assertEqual(status, 503)

    def test_cloud_marker_refused(self):
        with patch.dict('os.environ', {'K_SERVICE': 'not-a-cloud-service'}):
            with self.assertRaisesRegex(ValueError, 'managed_cloud_unsupported'):
                server.create_server(port=0, runs_dir=Path(self.temp.name))


class ExportTests(unittest.TestCase):
    def test_selected_case_ignores_unrelated_corruption_but_checks_own_source(self):
        original_path = catalog._source_path
        with tempfile.TemporaryDirectory(dir=catalog.ROOT) as temporary:
            corrupt = Path(temporary, 'corrupt.json')
            corrupt.write_text('{}')
            def source_path(case_id):
                return corrupt if case_id == 'team-050' else original_path(case_id)
            with patch.object(catalog, '_source_path', side_effect=source_path):
                self.assertEqual(server.step_record('minimal', 0)['input']['case_id'], 'minimal')
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    server.step_record('team-050', 0)
        with self.assertRaisesRegex(KeyError, 'case_not_found'):
            server.step_record('not-a-case', 0)

    def test_cli_exports_default_and_explicit_catalog_groups(self):
        for group, expected in [(None, 16), ('legacy', 16), ('team', 286), ('all', 302)]:
            with self.subTest(group=group), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary, 'export')
                args = ['export', '--output', str(output)]
                if group:
                    args += ['--group', group]
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    self.assertEqual(cli.main(args), 0)
                self.assertEqual(json.loads(stream.getvalue())['snapshots'], expected)
                rows = (output / 'manifest.jsonl').read_text().splitlines()
                self.assertEqual(len(rows), expected)

    def test_team_export_has_286_cutoffs_and_preserves_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary, 'team-export')
            summary = server.export_dataset(output, group='team')
            self.assertEqual(summary['snapshots'], 286)
            rows = [json.loads(line) for line in (output / 'manifest.jsonl').read_text().splitlines()]
            self.assertEqual({r['case_id'] for r in rows},
                             {'team-002-n4'} | {f'team-{i:03}' for i in range(1, 51)})
            self.assertTrue(all(r['eligible_for_training'] is False for r in rows))

    def test_export_has_16_separate_inputs_references_and_grouped_development_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary, 'export')
            summary = server.export_dataset(output)
            self.assertEqual(summary['snapshots'], 16)
            rows = [json.loads(line) for line in (output / 'manifest.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 16)
            families = {r['family_id'] for r in rows if r['case_id'] in ('case-002', 'case-002-n4')}
            self.assertEqual(len(families), 1)
            self.assertTrue(all(r['split'] == 'development' and r['eligible_for_training'] is False for r in rows))
            source = json.loads((output / rows[3]['input_path']).read_text())
            self.assertNotIn('reference', source)
            self.assertNotIn('agent_state', source)
            with self.assertRaises(FileExistsError):
                server.export_dataset(output)


if __name__ == '__main__':
    unittest.main()
