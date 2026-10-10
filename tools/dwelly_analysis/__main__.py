"""Run the local state-analysis workbench or export separated development data."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex


def load_provider_env(path):
    """Read explicit local credentials as data; never source or expand a file."""
    allowed = {'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_WORKSPACE_ID', 'GEMINI_API_KEY'}
    try:
        path = Path(path)
        if path.is_symlink():
            raise ValueError
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError
        pending = {}
        for line in raw.decode('utf-8').splitlines():
            stripped = line.strip()
            if stripped.startswith('export '):
                stripped = stripped[7:]
            name, separator, value = stripped.partition('=')
            name = name.strip()
            if not separator or name not in allowed:
                continue
            if name in pending or '$' in value or '`' in value:
                raise ValueError
            tokens = shlex.split(value, comments=True)
            if len(tokens) > 1 or (tokens and any(char.isspace() or ord(char) < 32 for char in tokens[0])):
                raise ValueError
            pending[name] = tokens[0] if tokens else ''
        for name, value in pending.items():
            if value:
                os.environ.setdefault(name, value)
    except (OSError, ValueError, UnicodeError):
        raise ValueError('invalid_provider_env') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    serve = commands.add_parser('serve')
    serve.add_argument('--port', type=int, default=8093)
    serve.add_argument('--runs-dir', type=Path)
    serve.add_argument('--allow-live', action='store_true', help='Explicitly enable paid model job dispatch')
    serve.add_argument('--model-config', type=Path)
    serve.add_argument('--database-url-env', help='Environment variable name, never a literal credential')
    serve.add_argument('--database-schema', default='proofkey_analysis')
    serve.add_argument('--budget-scope', help='Stable experiment ID; reuse across restarts')
    serve.add_argument('--migrate-model-jobs', action='store_true', help='Explicitly migrate selected PostgreSQL schema')
    serve.add_argument('--provider-env-file', type=Path, help='Read only four provider credential names; no shell expansion')
    export = commands.add_parser('export')
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--group', choices=('legacy', 'team', 'all'), default='legacy',
                        help='Pinned catalog group; legacy preserves the original 16-cutoff export')
    args = parser.parse_args(argv)
    from .server import create_server, export_dataset
    app = None
    store = None
    try:
        if args.command == 'export':
            print(json.dumps(export_dataset(args.output, group=args.group)))
        else:
            configured = any((args.model_config, args.database_url_env, args.budget_scope,
                              args.migrate_model_jobs, args.provider_env_file))
            runtime = None
            if configured or args.allow_live:
                if (not args.allow_live or not args.model_config or not args.database_url_env or not args.budget_scope
                        or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', args.database_url_env) is None
                        or 'K_SERVICE' in os.environ or 'CLOUD_RUN_JOB' in os.environ):
                    raise ValueError('incomplete_model_options')
                if args.provider_env_file:
                    load_provider_env(args.provider_env_file)
                from . import jobs, model
                from .worker import ModelRuntime
                dsn = os.environ.get(args.database_url_env)
                if not dsn:
                    raise ValueError('missing_database_url')
                settings = model.load_profiles(args.model_config)
                if args.migrate_model_jobs:
                    jobs.migrate(dsn, args.database_schema)
                store = jobs.AnalysisJobStore(dsn, args.database_schema)
                runtime = ModelRuntime(store, settings, args.budget_scope, allow_live=True)
            app = create_server(port=args.port, runs_dir=args.runs_dir, model_runtime=runtime)
            print(json.dumps({'url': 'http://127.0.0.1:' + str(app.server_address[1]),
                              'mode': 'offline_default', 'model_execution': bool(runtime), 'operational_effects': 0,
                              'run_storage': 'explicit_local_directory' if args.runs_dir else 'temporary_session'}), flush=True)
            app.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError):
        print(json.dumps({'error': 'analysis_command_failed'}))
        return 1
    finally:
        if app:
            app.server_close()
        # A live worker may still be finishing an in-flight request at shutdown.
        # Process exit, not store invalidation, ends it; expired jobs recover safely.
        if store and not app:
            store.close()


if __name__ == '__main__':
    raise SystemExit(main())
