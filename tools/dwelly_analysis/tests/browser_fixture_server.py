"""Explicit test server: real PostgreSQL, simulated transport, never providers.

PROOFKEY_TEST_DATABASE_URL=... python -m tools.dwelly_analysis.tests.browser_fixture_server
Serve only during postgres-browser-qa.mjs; do not deploy or use as a model result.
"""
import json
import os

from tools.dwelly_analysis import jobs, model, server
from tools.dwelly_analysis.worker import ModelRuntime


def main():
    dsn = os.environ['PROOFKEY_TEST_DATABASE_URL']
    os.environ['PROOFKEY_BROWSER_FIXTURE_KEY'] = 'SIMULATED-NOT-A-KEY'
    settings = model.load_profiles(model.__file__.replace('model.py', 'model-profiles.example.json'))
    settings['profiles'] = [settings['profiles'][0]]
    profile = settings['profiles'][0]
    profile.update(id='browser-fixture', label='SIMULATED transport · real PostgreSQL')
    profile['config'].update(api_key_env='PROOFKEY_BROWSER_FIXTURE_KEY', model='SIMULATED-NOT-A-PROVIDER')

    def fixture(evidence, profile, max_output_tokens, timeout):
        return {'text': json.dumps({'state': 'unknown', 'waiting_for': [],
            'next_action': {'type': 'operator_review', 'target_actor_id': None,
                            'description': 'SIMULATED transport: inspect evidence.'},
            'evidence_event_ids': [], 'uncertainty': ['Integration fixture; no provider called.']}),
            'provider': 'openai', 'requested_model': 'SIMULATED-NOT-A-PROVIDER',
            'observed_model': 'SIMULATED-NOT-A-PROVIDER', 'request_id': 'SIMULATED-BROWSER-POSTGRES',
            'latency_ms': 1, 'usage': {'input_tokens': 123, 'output_tokens': 45}}

    model.request = fixture
    schema = 'proofkey_browser_fixture_20261010'
    jobs.migrate(dsn, schema)
    store = jobs.AnalysisJobStore(dsn, schema)
    runtime = ModelRuntime(store, settings, 'browser-integration-20261010', allow_live=True)
    app = server.create_server(port=8094, model_runtime=runtime)
    print('SIMULATED transport only; real local PostgreSQL; http://127.0.0.1:8094', flush=True)
    try:
        app.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.server_close()


if __name__ == '__main__':
    main()
