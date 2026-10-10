"""Explicit offline/live entrypoint. Credentials are read only by providers."""
import argparse
import json
from pathlib import Path
import sys


def load_config(path):
    from tools.dwelly_cases.runner import strict_json
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 65536:
        raise ValueError("invalid_config_file")
    value = strict_json(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("config_must_be_object")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Experimental Dwelly model proposals and three API judges; no operational effects")
    commands = parser.add_subparsers(dest="command", required=True)
    pre = commands.add_parser("preflight", help="Validate configuration and report credential presence; no API calls")
    pre.add_argument("--config", required=True, type=Path)
    for name in ("dry-run", "run"):
        command = commands.add_parser(name, help="Offline bundle check" if name == "dry-run" else "Explicit live API experiment")
        command.add_argument("--config", required=True, type=Path)
        command.add_argument("--bundle", required=True, type=Path)
        command.add_argument("--output", required=True, type=Path)
        command.add_argument("--limit", type=int, default=50)
        command.add_argument("--no-reference", action="store_true")
        command.add_argument("--no-baseline", action="store_true")
        command.add_argument("--repeat-judges", type=int, default=0)
        command.add_argument("--max-parallel-requests", type=int, default=1)
        command.add_argument("--per-provider-limit", type=int, default=1)
        command.add_argument("--proposals-only", action="store_true")
        if name == "run":
            command.add_argument("--live", action="store_true", required=True,
                                 help="Required acknowledgement of external API calls and configured spend")
    args = parser.parse_args(argv)
    try:
        from .runner import preflight, run_experiment
        config = load_config(args.config)
        if args.command == "preflight":
            result = preflight(config)
            print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
            return 0 if result["ready"] else 2
        if not 1 <= args.limit <= 50 or not 0 <= args.repeat_judges <= 2:
            raise ValueError("invalid_run_bounds")
        result = run_experiment(args.bundle, args.output, config, live=args.command == "run",
                                limit=args.limit, include_reference=not args.no_reference,
                                compare_baseline=not args.no_baseline, repeat_judges=args.repeat_judges,
                                max_parallel_requests=args.max_parallel_requests,
                                per_provider_limit=args.per_provider_limit,
                                proposals_only=args.proposals_only)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError, RuntimeError) as error:
        print(json.dumps({"error": "invalid_input_or_run_failed", "type": type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
