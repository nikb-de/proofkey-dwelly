"""Run a local, single-operator queue using an environment-only bearer token."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import threading

from .server import create_server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local authenticated draft-proposal jobs; zero business effects")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--allow-live", action="store_true", help="Allow explicit live jobs with shared conservative budget")
    args = parser.parse_args(argv)
    server = None
    previous = {}
    try:
        server = create_server(args.bundle, args.config, args.state_dir,
                               token=os.environ.get("PROOFKEY_SERVICE_TOKEN"), host=args.host,
                               port=args.port, allow_live=args.allow_live)
        def stop(_signum, _frame):
            threading.Thread(target=server.shutdown, daemon=True).start()
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, stop)
        print(json.dumps({"status": "listening", "host": args.host, "port": server.server_address[1],
                          "live_enabled": args.allow_live, "operational_effects": 0}), flush=True)
        server.serve_forever()
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        print(json.dumps({"error": "service_start_failed"}), file=sys.stderr)
        return 2
    finally:
        if server is not None:
            server.server_close()
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
