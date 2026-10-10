"""Run the local platform; production deployment requires a separate auth BFF."""
import argparse
import os
from tools.dwelly_platform.store import PlatformStore, migrate
from tools.dwelly_platform.models import ModelBridge
from tools.dwelly_platform.server import create_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['serve'])
    parser.add_argument('--port', type=int, default=8095)
    parser.add_argument('--database-url-env', default='PROOFKEY_PLATFORM_DATABASE_URL')
    parser.add_argument('--schema', default='proofkey_platform')
    parser.add_argument('--migrate', action='store_true')
    parser.add_argument('--allow-live', action='store_true')
    parser.add_argument('--allow-media', action='store_true', help='Explicitly enable paid photo analysis and ASR controls')
    parser.add_argument('--image-model', default='gpt-4.1')
    parser.add_argument('--asr-model', default='whisper-1')
    parser.add_argument('--model-config', default='tools/dwelly_analysis/model-profiles.example.json')
    parser.add_argument('--provider-env-file')
    parser.add_argument('--budget-scope', default='platform-development')
    args = parser.parse_args()
    dsn = os.environ.get(args.database_url_env)
    if not dsn: parser.error('database URL environment variable is not set')
    if args.provider_env_file:
        from tools.dwelly_analysis.__main__ import load_provider_env
        load_provider_env(args.provider_env_file)
    if args.migrate: migrate(dsn, schema=args.schema)
    store = PlatformStore(dsn, schema=args.schema)
    from tools.dwelly_analysis.jobs import AnalysisJobStore, migrate as migrate_jobs
    from tools.dwelly_analysis.model import load_profiles
    from tools.dwelly_analysis.worker import ModelRuntime
    from tools.dwelly_platform.media import MediaService, OpenAIMediaProvider, migrate_media
    schema = args.schema + '_models'
    if args.migrate:
        migrate_jobs(dsn, schema=schema)
        migrate_media(store)
    runtime = ModelRuntime(AnalysisJobStore(dsn,schema=schema), load_profiles(args.model_config),
                           args.budget_scope,allow_live=args.allow_live)
    runtime.start()
    provider = OpenAIMediaProvider(image_model=args.image_model,asr_model=args.asr_model) if args.allow_media else None
    media = MediaService(store,provider=provider,budget_scope=args.budget_scope,budget_schema=schema)
    server = create_server(store, port=args.port,bridge=ModelBridge(store,runtime),media=media)
    print(f'Local platform: http://127.0.0.1:{server.server_port}/', flush=True)
    print('Local operator trust only. External business effects: 0.', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        if runtime: runtime.close()
        store.close()


if __name__ == '__main__': main()
