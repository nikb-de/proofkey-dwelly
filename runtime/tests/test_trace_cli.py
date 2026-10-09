"""Exercise the stdin-only renderer, including its process and I/O boundaries."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_execution_trace import real_receipt


SAFE_ERROR = '{"error":"invalid_trace"}\n'
FAILURE = b'{"failure":"invalid_input"}'


class ObservedStream(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


class TraceCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.command = real_receipt()
        cls.batch = real_receipt("batch")

    def process(self, payload=FAILURE, args=(), module="proofkey.trace"):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            before = tuple(root.rglob("*"))
            result = subprocess.run([sys.executable, "-m", module, *args],
                input=payload, cwd=folder, env=env, capture_output=True, timeout=20)
            self.assertEqual(tuple(root.rglob("*")), before, "renderer created files")
        return result

    def assert_safe_error(self, result):
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.decode(), SAFE_ERROR)
        self.assertEqual(result.stderr, b"")

    def test_default_and_explicit_json_preserve_failure_without_claiming_execution(self):
        for args in ((), ("--format", "json")):
            with self.subTest(args=args):
                result = self.process(args=args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, b"")
                self.assertEqual(len(result.stdout.splitlines()), 1)
                wire = json.loads(result.stdout)
                self.assertEqual(wire["kind"], "proofkey-execution-trace-v1")
                self.assertEqual(wire["provenance"], "unverified_receipt_projection")
                self.assertEqual(wire["transport_dispatch"], "unknown")
                self.assertEqual(wire["original_readback_observation"], "not_observed")
                self.assertIs(wire["publication_files_checked"], False)
                self.assertEqual(wire["bootstrap_failure"], "invalid_input")
                self.assertEqual(wire["positions"], [])
                self.assertIsNone(wire["shutdown"])

    def test_markdown_renders_fixed_unknown_markers(self):
        result = self.process(args=("--format", "markdown"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        text = result.stdout.decode()
        for marker in ("unverified_receipt_projection", "Transport dispatch: unknown",
                       "Original readback observation: not_observed", "Publication files checked: false"):
            self.assertIn(marker, text)
        self.assertTrue(text.endswith("\n"))

    def test_closed_arguments_do_not_echo_paths_secrets_or_usage_tracebacks(self):
        for args in (("--format",), ("--format", "SECRET"), ("--format=json",),
                     ("--input", "/SECRET/receipt.json"), ("--output", "/SECRET/out"),
                     ("--help",), ("SECRET",), ("--format", "json", "--format", "json")):
            with self.subTest(args=args):
                self.assert_safe_error(self.process(args=args))

    def test_malformed_duplicate_deep_oversized_and_nonfinite_input_are_safe(self):
        for data in (b"SECRET", b"\xffSECRET", b'{"failure":"invalid_input","failure":"SECRET"}',
                     b"[" * 65 + b"\"SECRET\"" + b"]" * 65,
                     FAILURE + b" " * (1_048_577 - len(FAILURE)),
                     b'{"SECRET":NaN}', b'{"SECRET":1e400}', b'{"SECRET":true}'):
            with self.subTest(length=len(data)):
                self.assert_safe_error(self.process(data))

    def test_input_at_exact_byte_limit_is_accepted(self):
        result = self.process(FAILURE + b" " * (1_048_576 - len(FAILURE)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["bootstrap_failure"], "invalid_input")

    def test_command_and_batch_processes_keep_independent_reported_facts(self):
        for receipt in (self.command, self.batch):
            with self.subTest(kind=receipt.run.kind):
                result = self.process(receipt.model_dump_json().encode())
                self.assertEqual(result.returncode, 0, result.stderr)
                wire = json.loads(result.stdout)
                first = wire["positions"][0]
                self.assertEqual((first["ordinal"], first["case"], first["command"]),
                                 (0, "case-1", "command-1"))
                self.assertIs(first["host_started"], True)
                self.assertEqual(first["host_outcome"], "result")
                self.assertEqual(first["access_status"], "authorized")
                self.assertEqual(first["effects"], [{"effect": "effect-1", "status": "verified", "basis": "receipt_reported"}])
                self.assertEqual(first["export_outcome"], "written")
                self.assertEqual(wire["publication_status"], "committed")
                self.assertIs(wire["shutdown"]["owner_closed"], True)
                self.assertEqual(wire["shutdown"]["pending_count"], 0)
                if receipt is self.batch:
                    self.assertEqual(wire["position_count"], 3)
                    self.assertEqual([row["ordinal"] for row in wire["positions"]], [0, 1, 2])
                    self.assertEqual([row["execution_outcome"] for row in wire["positions"]],
                                     ["result", "invalid_request", "invalid_request"])
                    self.assertEqual([row["access_status"] for row in wire["positions"]],
                                     ["authorized", "unknown", "unknown"])
                    self.assertEqual([row["export_outcome"] for row in wire["positions"]],
                                     ["written", "not_attempted", "not_attempted"])
                else:
                    self.assertEqual(wire["position_count"], 1)

    def test_valid_content_canary_does_not_survive_process_rendering(self):
        data = json.loads(self.command.model_dump_json())
        data["run"]["command"]["result"]["rationale"] = "SECRET-[click](https://secret.invalid)"
        for name in ("json", "markdown"):
            result = self.process(json.dumps(data).encode(), ("--format", name))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(b"SECRET", result.stdout + result.stderr)
            self.assertNotIn(b"https://", result.stdout + result.stderr)

    def test_original_cli_still_emits_its_own_one_line_envelope(self):
        result = self.process(args=("SECRET",), module="proofkey.cli")
        self.assertEqual(result.returncode, 64)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertEqual(json.loads(result.stdout), {"kind": "proofkey-cli-receipt-v1",
            "run": None, "shutdown": None, "failure": "invalid_usage"})

    def call_main(self, stream, args=()):
        from proofkey.trace import main
        output = io.StringIO()
        with patch("sys.stdin", SimpleNamespace(buffer=stream)), redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def test_main_reads_limit_plus_one_once_and_rejects_overflow(self):
        stream = ObservedStream(FAILURE + b" " * 1_048_577)
        code, output = self.call_main(stream)
        self.assertEqual((code, output), (2, SAFE_ERROR))
        self.assertEqual(stream.read_sizes, [1_048_577])
        self.assertEqual(stream.tell(), 1_048_577)

    def test_main_reads_valid_input_once_and_does_not_read_for_bad_usage(self):
        stream = ObservedStream(FAILURE)
        code, output = self.call_main(stream)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["bootstrap_failure"], "invalid_input")
        self.assertEqual(stream.read_sizes, [1_048_577])
        stream = ObservedStream(b"SECRET")
        self.assertEqual(self.call_main(stream, ("--input", "SECRET")), (2, SAFE_ERROR))
        self.assertEqual(stream.read_sizes, [])

    def test_stdin_io_failure_is_safe(self):
        class UnavailableStream:
            def read(self, size):
                raise OSError("SECRET /private/path")
        self.assertEqual(self.call_main(UnavailableStream()), (2, SAFE_ERROR))

    def test_stdout_io_failure_does_not_escape(self):
        from proofkey.trace import main
        class UnavailableOutput:
            def write(self, data):
                raise OSError("SECRET /private/path")
        with patch("sys.stdin", SimpleNamespace(buffer=ObservedStream(FAILURE))), \
                patch("sys.stdout", UnavailableOutput()):
            self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
