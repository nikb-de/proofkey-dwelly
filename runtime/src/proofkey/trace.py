"""Render an unverified CLI receipt from bounded stdin without runtime state."""
import sys

from .execution_trace import (MAX_INPUT_BYTES, TraceError, build_execution_trace,
    parse_cli_receipt, render_trace_json, render_trace_markdown)


_SAFE_ERROR = '{"error":"invalid_trace"}\n'


def _write(text, code):
    try:
        sys.stdout.write(text)
    except (OSError, UnicodeError):
        return 2
    return code


def main(argv=None):
    args = tuple(sys.argv[1:] if argv is None else argv)
    if not args:
        format_name = "json"
    elif len(args) == 2 and args[0] == "--format" and args[1] in ("json", "markdown"):
        format_name = args[1]
    else:
        return _write(_SAFE_ERROR, 2)
    try:
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        trace = build_execution_trace(parse_cli_receipt(data))
        output = render_trace_json(trace) if format_name == "json" else render_trace_markdown(trace)
    except (TraceError, OSError, UnicodeError):
        return _write(_SAFE_ERROR, 2)
    return _write(output + "\n", 0)


if __name__ == "__main__":
    sys.exit(main())
