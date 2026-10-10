"""Isolated real HTTP/PostgreSQL E2E fixture. External model transport is SIMULATED.

Never use this module for a live-provider result. It exposes the ordinary platform
routes only and removes its own UUID-named test schema on a controlled shutdown.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import signal
import threading
import time
import uuid
from unittest.mock import patch

import psycopg
from psycopg import sql

from tools.dwelly_analysis import jobs, model
from tools.dwelly_analysis.worker import ModelRuntime
from tools.dwelly_platform.models import ModelBridge, project_snapshot
from tools.dwelly_platform.server import create_server
from tools.dwelly_platform.store import PlatformStore, migrate
from tools.dwelly_service.cases import _snapshot


class SimulatedTransport:
    def __init__(self, plans, candidates, *, delay_seconds=0.5, faults=None):
        self.plans = {p['case_id']: p for p in plans}
        self.candidates = candidates
        self.delay_seconds = delay_seconds
        self.faults = faults or {}
        self.calls = []
        self.lock = threading.Lock()

    def __call__(self, value, profile, **_limits):
        config = profile['config']
        if not config['model'].startswith('SIMULATED'):
            raise ValueError('fixture_profile_mismatch')
        plan = self.plans.get(value['case_id'])
        if plan is None or value != project_snapshot(_snapshot(plan['declaration'], plan['events'])):
            raise ValueError('fixture_input_mismatch')
        key = f"{plan['source']['source_id']}:{plan['source']['step_index']}"
        fault = self.faults.get(value['case_id'])
        with self.lock:
            number = len(self.calls) + 1
            self.calls.append({'case_id': value['case_id'], 'input_hash': value['input_hash'],
                               'fixture_key': key, 'fault': fault, 'live_provider_calls': 0})
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        if fault:
            raise ValueError(fault)
        return {'text': json.dumps(copy.deepcopy(self.candidates[key]), ensure_ascii=False),
                'provider': config['provider'], 'requested_model': config['model'],
                'observed_model': 'SIMULATED-authored-case-fixture',
                'request_id': 'SIMULATED-request-' + str(number), 'latency_ms': self.delay_seconds * 1000,
                'usage': {'input_tokens': 100, 'output_tokens': 50}}


def main():
    from tools.dwelly_e2e.cases import case_plans
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--run-id', action='append', required=True)
    parser.add_argument('--unknown-run-id', action='append', default=[])
    args = parser.parse_args()
    dsn = os.environ.get('PROOFKEY_TEST_DATABASE_URL')
    if not dsn:
        parser.error('PROOFKEY_TEST_DATABASE_URL is required')
    plans = [plan for run_id in args.run_id + args.unknown_run_id for plan in case_plans(run_id)]
    unknown_ids = {plan['case_id'] for run_id in args.unknown_run_id for plan in case_plans(run_id)}
    fixtures = json.loads(Path(__file__).with_name('fixtures').joinpath('good-candidates.json').read_text())
    transport = SimulatedTransport(plans, fixtures['candidates'], delay_seconds=0.8,
                                   faults={case_id: 'timeout' for case_id in unknown_ids})
    schema = 'case_e2e_test_' + uuid.uuid4().hex
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'plans.json').write_text(json.dumps(plans, indent=2), encoding='utf-8')
    report = {'mode': 'simulated', 'qualification': 'fixture_only_not_live_evidence',
              'schema': schema, 'live_provider_calls': 0}
    store = job_store = runtime = server = None
    settings = {'profiles': [{'id': 'simulated-case-fixture', 'label': 'SIMULATED case fixture',
        'config': {'provider': 'openai', 'model': 'SIMULATED-authored-case-fixture',
                   'api_key_env': 'PROOFKEY_SIMULATED_FIXTURE_TOKEN',
                   'input_usd_per_million': '0.01', 'output_usd_per_million': '0.01'}}],
        'budget_per_model_usd': 25, 'max_output_tokens': 2048, 'timeout_seconds': 5}
    try:
        migrate(dsn, schema=schema)
        jobs.migrate(dsn, schema=schema)
        store = PlatformStore(dsn, schema=schema)
        job_store = jobs.AnalysisJobStore(dsn, schema)
        with patch.dict(os.environ, {'PROOFKEY_SIMULATED_FIXTURE_TOKEN': 'fixture-only-never-a-secret'}), \
                patch.object(model, 'request', transport):
            runtime = ModelRuntime(job_store, settings, 'fixture-' + schema, allow_live=True)
            server = create_server(store, port=args.port, bridge=ModelBridge(store, runtime))
            def stop(_signal, _frame):
                threading.Thread(target=server.shutdown, daemon=True).start()
            signal.signal(signal.SIGINT, stop)
            signal.signal(signal.SIGTERM, stop)
            runtime.start()
            print(json.dumps({'ready': True, 'origin': f'http://127.0.0.1:{server.server_port}',
                              'mode': 'simulated', 'provider': 'SIMULATED', 'schema': schema}), flush=True)
            server.serve_forever(poll_interval=0.05)
            runtime.close()
            for thread in runtime.threads:
                thread.join(timeout=10)
            report['calls'] = transport.calls
            report['cases'] = []
            for case in store.list_cases():
                detail = store.detail(case['case_id'])
                detail['model_jobs'] = [runtime.get(link['job_id']) for link in detail['model_jobs']]
                report['cases'].append(detail)
    finally:
        if server:
            server.server_close()
        if runtime:
            runtime.close()
        if store:
            store.close()
        if job_store:
            job_store.close()
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
            report['schema_dropped'] = connection.execute(
                'SELECT NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name=%s)',
                (schema,)).fetchone()[0]
        (args.output_dir / 'database-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
