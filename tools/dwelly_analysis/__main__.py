"""Run the local state-analysis workbench or export separated development data."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    serve = commands.add_parser('serve')
    serve.add_argument('--port', type=int, default=8093)
    serve.add_argument('--runs-dir', type=Path)
    export = commands.add_parser('export')
    export.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    from .server import create_server, export_dataset
    app = None
    try:
        if args.command == 'export':
            print(json.dumps(export_dataset(args.output)))
        else:
            app = create_server(port=args.port, runs_dir=args.runs_dir)
            print(json.dumps({'url': 'http://127.0.0.1:' + str(app.server_address[1]),
                              'mode': 'offline', 'live_calls': 0, 'operational_effects': 0,
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


if __name__ == '__main__':
    raise SystemExit(main())
