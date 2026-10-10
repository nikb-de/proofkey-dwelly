"""Local-only shadow import command; no runtime plugins or binding input."""
import argparse
import json

from .bridge import import_shadow, _record


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("cli_arguments_invalid")


def main(argv=None):
    parser = _Parser(description="Read a completed local service job into inert shadow storage.",
                     allow_abbrev=False)
    parser.add_argument("--service-state", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--shadow-state", required=True)
    try:
        args = parser.parse_args(argv)
    except ValueError:
        result = {**_record("rejected", "cli_arguments_invalid"), "import_id": None}
    else:
        result = import_shadow(args.service_state, args.job_id, args.case_id, args.shadow_state)
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 1 if result["status"] == "rejected" else 0


if __name__ == "__main__":
    raise SystemExit(main())
