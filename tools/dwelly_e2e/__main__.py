"""Explicit opt-in command for bounded case-model HTTP runs."""
import argparse
import json

from .runner import run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("run")
    command.add_argument("--base-url", required=True)
    command.add_argument("--mode", choices=("live", "simulated"), required=True)
    command.add_argument("--profile", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--run-id", required=True)
    command.add_argument("--limit", type=int, default=16)
    command.add_argument("--poll-timeout", type=float, default=90)
    args = parser.parse_args(argv)
    try:
        report = run(args.base_url, args.mode, args.profile, args.output, args.run_id,
                     limit=args.limit, poll_timeout=args.poll_timeout)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    print(json.dumps({"status": report["status"], "mode": report["mode"],
                      "qualification": report["qualification"], "output": args.output,
                      "exit_code": report["exit_code"]}))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
