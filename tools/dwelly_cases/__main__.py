"""Run with Python >=3.11: python -m tools.dwelly_cases {import,run}."""
import argparse
import json
from pathlib import Path
import sys

from .importer import import_cases
from .runner import run_pilot


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline Dwelly logistics snapshots and next-action pilot")
    commands = parser.add_subparsers(dest="command", required=True)
    intake = commands.add_parser("import", help="Import local public examples; no network access")
    intake.add_argument("--source", type=Path, required=True)
    intake.add_argument("--output", type=Path, required=True)
    intake.add_argument("--expected-cases", type=int, default=50)
    run = commands.add_parser("run", help="Propose unsent next communications and assess routing proxy")
    run.add_argument("--bundle", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            result = import_cases(args.source, args.output, args.expected_cases)
            result = {k: v for k, v in result.items() if k not in {"files", "case_ids"}}
        else:
            result = run_pilot(args.bundle, args.output)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
        # Do not print customer text, unsafe input paths or arbitrary parser excerpts.
        print(json.dumps({"error": "invalid_input_or_io", "type": type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
