"""Case-only PostgreSQL API. No model worker, uploads, or operational effects."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
import re
import sys

from tools.dwelly_cases.runner import strict_json
from .cases import CaseError, MAX_CASES, MAX_EVENTS, MAX_REQUEST_BYTES


_ROUTE = re.compile(r"/v1/cases/([A-Za-z0-9][A-Za-z0-9_-]{0,63})(/events|/analysis-jobs)?")
_AUTHORITY = re.compile(r"(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?):([0-9]{1,5})")
_CLOUD_AUTHORITY = re.compile(r"([A-Za-z0-9.-]+)(?::([0-9]{1,5}))?")
_DNS_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
_CLOUD_PROFILE = "cloud-run-case-v1"
_STATUS = {"invalid_case_request": 400, "case_not_found": 404, "revision_not_found": 404,
           "idempotency_conflict": 409, "revision_conflict": 409, "event_conflict": 409,
           "case_capacity": 429, "case_storage_error": 503}


class CaseServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Never log headers, case content, credentials or database exception text.
        pass

    def server_close(self):
        super().server_close()
        if getattr(self, "cases", None) is not None:
            self.cases.close()


class CaseHandler(BaseHTTPRequestHandler):
    server_version = "ProofKeyCases"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args):
        pass

    def _send(self, status, value):
        data = json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def _guard(self):
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or hosts[0].lower() not in self.server.accepted_hosts or self.headers.get("Origin") is not None:
            self._send(403, {"error": "forbidden"})
            return False
        if self.command == "GET" and self.path in ("/healthz", "/readyz"):
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
        if size > MAX_REQUEST_BYTES:
            raise OverflowError("request_too_large")
        if self.headers.get_content_type() != "application/json":
            raise TypeError("unsupported_media_type")
        data = self.rfile.read(size)
        if len(data) != size:
            raise ValueError("invalid_request")
        return strict_json(data)

    def _case_error(self, error):
        code = error.code if error.code in _STATUS else "case_storage_error"
        self._send(_STATUS[code], {"error": code})

    def do_GET(self):
        if not self._guard():
            return
        try:
            if self.path == "/healthz":
                return self._send(200, {"status": "ok"})
            if self.path == "/readyz":
                try:
                    self.server.cases.check_ready()
                except (CaseError, OSError):
                    return self._send(503, {"error": "storage_unavailable"})
                return self._send(200, {"status": "ready"})
            if self.path == "/v1/capabilities":
                return self._send(200, {"storage": "postgresql", "operational_effects": 0,
                    "max_cases": MAX_CASES, "max_events_per_case": MAX_EVENTS,
                    "media_upload": False, "analysis_outbox": True,
                    "deployment_profile": self.server.deployment_profile,
                    "managed_cloud_enabled": self.server.deployment_profile == _CLOUD_PROFILE,
                    "case_intake": {"enabled": True, "source_mode": "local_fixture",
                        "analysis_status": "pending_not_started", "automated_analysis": False,
                        "runtime_binding": None, "authorization": "unverified", "operational_effects": 0}})
            path, query_marker, query = self.path.partition("?")
            route = _ROUTE.fullmatch(path)
            if route is None or route[2] == "/events":
                return self._send(404, {"error": "not_found"})
            if route[2] == "/analysis-jobs":
                if query_marker:
                    raise CaseError("invalid_case_request")
                return self._send(200, {"case_id": route[1], "jobs": self.server.cases.analysis_jobs(route[1]),
                                        "operational_effects": 0})
            revision = None
            if query_marker:
                if re.fullmatch(r"revision=(0|[1-9][0-9]*)", query) is None:
                    raise CaseError("invalid_case_request")
                try:
                    revision = int(query[len("revision="):])
                except ValueError:
                    raise CaseError("invalid_case_request") from None
            self._send(200, self.server.cases.get(route[1], revision))
        except CaseError as error:
            self._case_error(error)
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
            self._send(503, {"error": "case_storage_error"})

    def do_POST(self):
        if not self._guard():
            return
        try:
            route = _ROUTE.fullmatch(self.path)
            if self.path != "/v1/cases" and not (route and route[2] == "/events"):
                return self._send(404, {"error": "not_found"})
            body = self._body()
            keys = self.headers.get_all("Idempotency-Key", [])
            if len(keys) != 1 or re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", keys[0]) is None:
                raise CaseError("invalid_case_request")
            if route:
                snapshot, created = self.server.cases.append(route[1], keys[0], body)
            else:
                snapshot, created = self.server.cases.create(keys[0], body)
            self._send(201 if created else 200, snapshot)
        except CaseError as error:
            self._case_error(error)
        except OverflowError:
            self._send(413, {"error": "request_too_large"})
        except TypeError:
            self._send(415, {"error": "unsupported_media_type"})
        except (ValueError, UnicodeError, RecursionError):
            self._send(400, {"error": "invalid_case_request"})
        except OSError:
            self._send(503, {"error": "case_storage_error"})


def _check_deployment_profile(profile, command):
    if type(profile) is not str or profile not in ("local", _CLOUD_PROFILE):
        raise ValueError("invalid_deployment_profile")
    cloud = profile == _CLOUD_PROFILE
    forbidden_markers = (("CLOUD_RUN_JOB",) if command == "serve" else ("K_SERVICE",)) if cloud else ("K_SERVICE", "CLOUD_RUN_JOB")
    if any(marker in os.environ for marker in forbidden_markers):
        raise ValueError("managed_cloud_unsupported")
    return cloud


def _check_service_token(token, cloud):
    minimum = 32 if cloud else 16
    if type(token) is not str or not minimum <= len(token) <= 4096 or re.fullmatch(r"[!-~]+", token) is None:
        raise ValueError("invalid_service_token")


def _validated_hosts(allowed_hosts, cloud):
    extras = [] if allowed_hosts is None else allowed_hosts
    if not isinstance(extras, (list, tuple)) or (cloud and not extras):
        raise ValueError("invalid_allowed_hosts")
    for value in extras:
        if cloud:
            match = _CLOUD_AUTHORITY.fullmatch(value) if type(value) is str else None
            if (match is None or len(match[1]) > 253
                    or any(_DNS_LABEL.fullmatch(label) is None for label in match[1].split("."))
                    or (match[2] is not None and not 1 <= int(match[2]) <= 65535)):
                raise ValueError("invalid_allowed_hosts")
        else:
            match = _AUTHORITY.fullmatch(value) if type(value) is str else None
            if match is None or not 1 <= int(match[1]) <= 65535:
                raise ValueError("invalid_allowed_hosts")
    return extras


def create_case_server(store, *, token, host="127.0.0.1", port=8080, allowed_hosts=None,
                       deployment_profile="local"):
    """Own the supplied store after successful construction; closing closes its pool."""
    cloud = _check_deployment_profile(deployment_profile, "serve")
    _check_service_token(token, cloud)
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("invalid_service_config")
    try:
        ipaddress.IPv4Address(host)
    except (ValueError, TypeError):
        raise ValueError("invalid_bind_address") from None
    extras = _validated_hosts(allowed_hosts, cloud)
    store.check_ready()
    server = CaseServer((host, port), CaseHandler)
    server.cases, server.token = store, token
    server.deployment_profile = deployment_profile
    actual_port = server.server_address[1]
    server.accepted_hosts = {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"} | {value.lower() for value in extras}
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "serve"))
    args = parser.parse_args(argv)
    store = server = None
    try:
        profile = os.environ.get("PROOFKEY_DEPLOYMENT_PROFILE", "local")
        cloud = _check_deployment_profile(profile, args.command)
        url = os.environ.get("PROOFKEY_DATABASE_URL")
        if not url:
            raise ValueError("database_url_required")
        schema = os.environ.get("PROOFKEY_DATABASE_SCHEMA", "public")
        pool_max = int(os.environ.get("PROOFKEY_DB_POOL_MAX", "4"))
        if not 1 <= pool_max <= 128:
            raise ValueError("invalid_database_pool")
        if args.command == "migrate":
            from .postgres import migrate
            migrate(url, schema=schema)
            print(json.dumps({"status": "migrated", "operational_effects": 0}))
            return 0
        token = os.environ.get("PROOFKEY_SERVICE_TOKEN", "")
        _check_service_token(token, cloud)
        port = int(os.environ.get("PORT", "8080"))
        raw_hosts = os.environ.get("PROOFKEY_ALLOWED_HOSTS", "").split(",")
        hosts = raw_hosts if cloud else [value.strip() for value in raw_hosts if value.strip()]
        _validated_hosts(hosts, cloud)
        from .postgres import PostgresCaseStore
        store = PostgresCaseStore(url, schema=schema, max_size=pool_max)
        server = create_case_server(store, token=token, host=os.environ.get("HOST", "0.0.0.0" if cloud else "127.0.0.1"),
                                    port=port, allowed_hosts=hosts, deployment_profile=profile)
        server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, ImportError):
        print(json.dumps({"error": "case_service_start_failed"}), file=sys.stderr)
        return 2
    finally:
        if server is not None:
            server.server_close()
        elif store is not None:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
