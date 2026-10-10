"""Wire-level rejection and explicit operator retry; real PostgreSQL, no providers."""
import json
import socket
from http.client import HTTPResponse

import pytest

from tools.dwelly_channels.tests.test_server import (
    SECRET, channels, config, envelope, launch, request, signed,
)


def raw_post(port, headers, body):
    """Keep duplicate header lines intact (urllib would collapse them)."""
    wire = ("POST /webhooks/chat-demo HTTP/1.1\r\n" +
            "\r\n".join(f"{key}: {value}" for key, value in headers) +
            "\r\n\r\n").encode("ascii") + body
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.sendall(wire)
        response = HTTPResponse(connection)
        response.begin()
        return response.status, json.loads(response.read())


@pytest.mark.parametrize("mutation,status,code", [
    ("duplicate_timestamp", 403, "invalid_signature"),
    ("duplicate_signature", 403, "invalid_signature"),
    ("duplicate_length", 400, "invalid_request"),
    ("conflicting_length", 400, "invalid_request"),
    ("transfer_encoding", 400, "invalid_request"),
    ("wrong_host", 403, "invalid_ingress_boundary"),
    ("duplicate_host", 403, "invalid_ingress_boundary"),
    ("oversize_body", 413, "request_too_large"),
])
def test_raw_ambiguous_headers_rejected_before_ingest(channels, mutation, status, code):
    from tools.dwelly_channels.contracts import MAX_ENVELOPE_BYTES
    from tools.dwelly_channels.server import create_server
    service, store = channels
    server = create_server(service, {"chat-demo": SECRET}, port=0)
    thread, _ = launch(server)
    try:
        body = json.dumps(envelope()).encode()
        headers = [("Host", f"127.0.0.1:{server.server_port}"),
                   ("Content-Length", str(len(body))), *signed(body).items()]
        if mutation.startswith("duplicate_"):
            field = {"duplicate_timestamp": "X-ProofKey-Timestamp",
                     "duplicate_signature": "X-ProofKey-Signature",
                     "duplicate_length": "Content-Length", "duplicate_host": "Host"}[mutation]
            headers.append(next(pair for pair in headers if pair[0] == field))
        elif mutation == "conflicting_length":
            headers.append(("Content-Length", str(len(body) + 1)))
        elif mutation == "transfer_encoding":
            headers.append(("Transfer-Encoding", "chunked"))
        elif mutation == "wrong_host":
            headers[0] = ("Host", "attacker.invalid")
        else:
            # No 40 MiB allocation: length rejection must precede body reading.
            headers[1] = ("Content-Length", str(MAX_ENVELOPE_BYTES + 1))
            body = b""
        observed, result = raw_post(server.server_port, headers, body)
        assert (observed, result) == (status, {"error": {"code": code}})
        assert service.list() == []
        assert store.get("case-1")["revision"] == 0
        detail = store.detail("case-1")
        assert detail["model_jobs"] == detail["actions"] == detail["decisions"] == []
        assert detail["external_effects"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def test_operator_retry_promotes_only_retained_source_after_config_correction(channels):
    from tools.dwelly_channels.service import ChannelService
    from tools.dwelly_platform.server import create_server
    service, store = channels
    server = create_server(store, channels=service, port=0)
    thread, origin = launch(server)
    headers = {"X-ProofKey-Request": "platform-v1", "Idempotency-Key": "retry-import"}
    try:
        code, result = request(origin, "/api/platform/communications/import", headers=headers,
                               body={"connector_id": "chat-demo", "envelope": envelope(conversation="new-thread")})
        receipt = result["receipt"]
        assert code == 200 and receipt["status"] == "quarantined"
        assert receipt["reason"] == "unknown_route"
        assert receipt["event_ids"] == [] and store.get("case-1")["revision"] == 0
        retry_path = "/api/platform/communications/" + receipt["receipt_id"] + "/retry"
        assert request(origin, retry_path, body={})[0] == 403
        assert service.list()[0] == receipt

        corrected = config()
        corrected["connectors"][0]["routes"]["new-thread"] = "case-1"
        server.channels = ChannelService(store, corrected)  # Trusted local operator config reload.
        headers["Idempotency-Key"] = "retry-corrected-route"
        code, result = request(origin, retry_path, body={}, headers=headers)
        accepted = result["receipt"]
        assert code == 200 and accepted["status"] == "accepted"
        assert accepted["reason"] is None
        for field in ("receipt_id", "raw_sha256", "received_at", "source", "delivery_id"):
            assert accepted[field] == receipt[field]
        assert accepted["revision"] == 1 and len(accepted["event_ids"]) == 1
        assert store.get("case-1")["events"][0]["text"] == envelope()["payload"]["text"]
        headers["Idempotency-Key"] = "retry-already-accepted"
        assert request(origin, retry_path, body={}, headers=headers) == (
            409, {"error": {"code": "receipt_not_quarantined"}})
        assert server.channels.list() == [accepted]
        assert store.get("case-1")["revision"] == 1
        detail = store.detail("case-1")
        assert detail["model_jobs"] == detail["decisions"] == detail["actions"] == []
        assert detail["external_effects"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)
