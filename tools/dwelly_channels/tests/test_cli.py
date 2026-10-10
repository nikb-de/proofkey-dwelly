"""Real CLI lifecycle with opt-in local ingress and paid execution disabled."""
import json
import os
from pathlib import Path
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid

import pytest

from tools.dwelly_channels.tests.test_server import SECRET, config, envelope, request, signed

ROOT = Path(__file__).resolve().parents[3]


def child_env(dsn):
    # Never inherit provider credentials, cloud deployment markers, or env-file paths.
    result = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TMPDIR") if key in os.environ}
    result.update(PYTHONPATH=str(ROOT) + ":" + str(ROOT / "tools") + ":" + str(ROOT / "runtime/src"),
                  PROOFKEY_PLATFORM_DATABASE_URL=dsn, PROOFKEY_CHAT_WEBHOOK_SECRET=SECRET)
    return result


def test_cli_migrates_starts_both_listeners_and_stops_without_provider_calls(tmp_path):
    dsn = os.environ.get("PROOFKEY_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("real PostgreSQL required")
    import psycopg
    from psycopg import sql
    schema = "channels_cli_" + uuid.uuid4().hex
    config_path = tmp_path / "channels.json"
    config_path.write_text(json.dumps(config()), encoding="utf-8")
    command = [sys.executable, "-m", "tools.dwelly_platform", "serve", "--port", "0",
               "--schema", schema, "--migrate", "--channel-config", str(config_path), "--channel-port", "0",
               "--budget-scope", schema]
    process = subprocess.Popen(command, cwd=ROOT, env=child_env(dsn), stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True)
    lines = queue.Queue()
    reader = threading.Thread(target=lambda: [lines.put(line) for line in process.stdout], daemon=True)
    reader.start()
    origins = {}
    try:
        deadline = time.monotonic() + 30
        while len(origins) < 2 and time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                line = lines.get(timeout=.2)
            except queue.Empty:
                continue
            found = re.fullmatch(r"(Signed local ingress|Local platform): (http://127\.0\.0\.1:[0-9]+)(?:/.*)?\n", line)
            if found:
                origins[found[1]] = found[2]
        assert len(origins) == 2, "CLI did not advertise both loopback listeners within 30 seconds"
        origin = origins["Local platform"]
        assert origin != origins["Signed local ingress"]
        code, caps = request(origin, "/api/platform/capabilities")
        assert code == 200 and caps["models"]["enabled"] is False
        assert caps["media"]["enabled"] is False
        assert caps["communications"]["provider_connections"] is False
        assert caps["communications"]["outbound_enabled"] is False
        assert caps["external_effects"] == 0
        headers = {"X-ProofKey-Request": "platform-v1", "Idempotency-Key": "cli-case"}
        code, _ = request(origin, "/api/platform/cases", headers=headers, body={
            "case_id": "case-1", "links": {"order_id": "order-1", "customer_id": "customer", "operator_id": "operator"},
            "participants": ["customer", "operator"], "language": "en"})
        assert code == 201
        raw = json.dumps(envelope()).encode()
        code, result = request(origins["Signed local ingress"], "/webhooks/chat-demo", raw=raw, headers=signed(raw))
        assert code == 200 and result["receipt"]["status"] == "accepted"
        code, result = request(origin, "/api/platform/cases/case-1")
        detail = result["case"]
        assert code == 200 and detail["snapshot"]["revision"] == 1
        assert len(detail["communications"]) == 1
        assert detail["model_jobs"] == detail["actions"] == detail["decisions"] == []
        assert detail["external_effects"] == 0
        with psycopg.connect(dsn) as connection:
            for name, table in ((schema, "platform_media_runs"), (schema + "_models", "model_jobs")):
                assert connection.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(
                    sql.Identifier(name), sql.Identifier(table))).fetchone()[0] == 0
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=10) == 0
        reader.join(2)
        for listener in origins.values():
            with socket.socket() as connection:
                connection.settimeout(2)
                assert connection.connect_ex(("127.0.0.1", int(listener.rsplit(":", 1)[1]))) != 0
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        process.stdout.close()
        reader.join(2)
        with psycopg.connect(dsn, autocommit=True) as connection:
            for name in (schema, schema + "_models"):
                connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(name)))


def test_cli_channel_port_requires_configuration_before_database_access():
    result = subprocess.run([sys.executable, "-m", "tools.dwelly_platform", "serve", "--channel-port", "0"],
                            cwd=ROOT, env=child_env("postgresql://localhost:1/not-a-database"),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
    assert result.returncode == 2
    assert "--channel-port requires --channel-config" in result.stderr
