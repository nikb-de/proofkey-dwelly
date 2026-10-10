"""Authenticated local HTTP boundary; never a managed-cloud work queue."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
import re
import socket
import sqlite3

from tools.dwelly_cases.importer import read_bytes
from tools.dwelly_cases.runner import strict_json
from tools.dwelly_model.__main__ import load_config
from tools.dwelly_model.runner import preflight
from .store import JobStore, MAX_PENDING_JOBS, safe_path
from .worker import Worker


DEFAULTS = {"mode": "dry_run", "limit": 1, "evaluate": False,
            "max_parallel_requests": 4, "per_provider_limit": 2}
ROUTE = re.compile(r"/v1/jobs/([a-f0-9]{32})(/summary|/proposals|/cancel)?")
BODY_LIMIT = 16384


def normalize(body, allow_live):
    if type(body) is not dict or set(body) - set(DEFAULTS):
        raise ValueError("invalid_request")
    spec = {**DEFAULTS, **body}
    if (spec["mode"] not in ("dry_run", "live") or type(spec["evaluate"]) is not bool
            or type(spec["limit"]) is not int or not 1 <= spec["limit"] <= 50
            or type(spec["max_parallel_requests"]) is not int or not 1 <= spec["max_parallel_requests"] <= 16
            or type(spec["per_provider_limit"]) is not int or not 1 <= spec["per_provider_limit"] <= 8):
        raise ValueError("invalid_request")
    if spec["mode"] == "live" and not allow_live:
        raise PermissionError("live_disabled")
    return spec


class ServiceServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = True

    def start_worker(self):
        if self.worker is None:
            self.worker = Worker(self.store, self.bundle, self.config, allow_live=self.allow_live)
            self.worker.start()

    def check_ready(self):
        self.store.check_ready()
        if self.worker is not None and (self.worker.failure or not self.worker.thread.is_alive()):
            raise OSError("worker_unavailable")

    def handle_error(self, request, client_address):
        # Request bodies, headers and exception text are deliberately not logged.
        pass

    def server_close(self):
        super().server_close()
        if getattr(self, "worker", None) is not None:
            self.worker.stop()
            self.worker = None
        if getattr(self, "store", None) is not None:
            self.store.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "DwellyLocal"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args):
        pass

    def _send(self, status, value):
        data = json.dumps(value, sort_keys=True, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def _guard(self):
        host_headers = self.headers.get_all("Host", [])
        if len(host_headers) != 1:
            self._send(403, {"error": "forbidden"})
            return False
        host = host_headers[0]
        if host not in self.server.accepted_hosts or self.headers.get("Origin") is not None:
            self._send(403, {"error": "forbidden"})
            return False
        if self.path == "/healthz" and self.command == "GET":
            return True
        auth = self.headers.get_all("Authorization", [])
        if len(auth) != 1 or not hmac.compare_digest(auth[0].encode(), ("Bearer " + self.server.token).encode()):
            self._send(401, {"error": "unauthorized"})
            return False
        return True

    def _body(self):
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]) or self.headers.get("Transfer-Encoding") is not None:
            raise ValueError("invalid_request")
        size = int(lengths[0])
        if size > BODY_LIMIT:
            raise OverflowError("request_too_large")
        if self.headers.get_content_type() != "application/json":
            raise TypeError("unsupported_media_type")
        data = self.rfile.read(size)
        if len(data) != size:
            raise ValueError("invalid_request")
        return strict_json(data)

    def _public(self, job):
        return {key: value for key, value in job.items() if key != "spec"} | {
            "progress": self.server.store.progress(job["job_id"]),
            "status_url": "/v1/jobs/" + job["job_id"], "operational_effects": 0}

    def do_GET(self):
        if not self._guard():
            return
        try:
            if self.path == "/healthz":
                self.server.check_ready()
                return self._send(200, {"status": "ok"})
            if self.path == "/v1/capabilities":
                return self._send(200, {"live_enabled": self.server.allow_live, "storage": "local_posix",
                                        "operational_effects": 0, "defaults": DEFAULTS,
                                        "max_pending_jobs": MAX_PENDING_JOBS,
                                        "recovery": "running_jobs_interrupted_without_replay"})
            route = ROUTE.fullmatch(self.path)
            if not route or route[2] == "/cancel":
                return self._send(404, {"error": "not_found"})
            if route[2] == "/summary":
                return self._send(200, self.server.store.summary(route[1]))
            if route[2] == "/proposals":
                return self._send(200, {"job_id": route[1], "proposals": self.server.store.proposals(route[1]),
                                        "operational_effects": 0})
            return self._send(200, self._public(self.server.store.get(route[1])))
        except KeyError:
            self._send(404, {"error": "not_found"})
        except ValueError:
            self._send(409, {"error": "summary_unavailable"})
        except (OSError, sqlite3.Error):
            self._send(503, {"error": "storage_unavailable"})

    def do_POST(self):
        if not self._guard():
            return
        try:
            route = ROUTE.fullmatch(self.path)
            if self.path != "/v1/jobs" and (not route or route[2] != "/cancel"):
                return self._send(404, {"error": "not_found"})
            body = self._body()
            if route:
                if body != {}:
                    raise ValueError("invalid_request")
                result = self.server.store.cancel(route[1])
                return self._send(200, self._public(result))
            keys = self.headers.get_all("Idempotency-Key", [])
            if len(keys) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", keys[0]):
                raise ValueError("invalid_request")
            spec = normalize(body, self.server.allow_live)
            self.server.check_ready()
            job, created = self.server.store.submit(keys[0], spec)
            if self.server.worker is not None:
                self.server.worker.wakeup.set()
            self._send(202 if created else 200, self._public(job))
        except KeyError:
            self._send(404, {"error": "not_found"})
        except PermissionError:
            self._send(403, {"error": "live_disabled"})
        except OverflowError:
            self._send(413, {"error": "request_too_large"})
        except TypeError:
            self._send(415, {"error": "unsupported_media_type"})
        except (ValueError, UnicodeError, RecursionError) as error:
            conflict = error.args == ("idempotency_conflict",)
            full = error.args == ("queue_full",)
            self._send(409 if conflict else 429 if full else 400,
                       {"error": "idempotency_conflict" if conflict else "queue_full" if full else "invalid_request"})
        except (OSError, sqlite3.Error):
            self._send(503, {"error": "storage_unavailable"})


def create_server(bundle, config, state_dir, *, token, host="127.0.0.1", port=8080,
                  allow_live=False, start_worker=True):
    if "K_SERVICE" in os.environ or "CLOUD_RUN_JOB" in os.environ:
        raise ValueError("managed_cloud_unsupported")
    if (type(token) is not str or not 16 <= len(token) <= 4096
            or not re.fullmatch(r"[!-~]+", token)):
        raise ValueError("invalid_service_token")
    if type(allow_live) is not bool or type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("invalid_service_config")
    try:
        ipaddress.IPv4Address(host)
    except (ValueError, TypeError):
        raise ValueError("invalid_bind_address") from None
    bundle, config, state = safe_path(bundle), safe_path(config), safe_path(state_dir)
    if (state.is_relative_to(bundle) or bundle.is_relative_to(state)
            or config.is_relative_to(state) or state == config):
        raise ValueError("path_overlap")
    if not bundle.is_dir():
        raise ValueError("invalid_bundle")
    value = load_config(config)
    preflight(value)
    identity = hashlib.sha256(json.dumps({"bundle": str(bundle), "config": value}, sort_keys=True).encode()
                              + read_bytes(bundle / "manifest.json") + read_bytes(bundle / "ledger.jsonl")).hexdigest()
    store = JobStore(state)
    server = None
    try:
        store.bind_inputs(identity)
        server = ServiceServer((host, port), Handler)
        server.store, server.bundle, server.config = store, bundle, value
        server.token, server.allow_live, server.worker = token, allow_live, None
        actual_port = server.server_address[1]
        accepted = {"127.0.0.1", "localhost", host}
        server.accepted_hosts = {name + ":" + str(actual_port) for name in accepted}
        if start_worker:
            server.start_worker()
        return server
    except BaseException:
        if server is not None:
            server.server_close()
        store.close()
        raise
