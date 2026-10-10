"""Explicit case-only cloud configuration and real PostgreSQL/HTTP boundaries."""
import contextlib
import http.client
import io
import json
import os
import threading
import unittest
import uuid
from unittest.mock import patch

from tools.dwelly_service import case_api


DSN = os.environ.get("PROOFKEY_TEST_DATABASE_URL")
CLOUD_PROFILE = "cloud-run-case-v1"
TOKEN = "synthetic-cloud-test-token-32-chars"
CLOUD_HOST = "proofkey-case-123.europe-west2.run.app"


def create_server(test, store, **options):
    """Keep a removed profile argument an explanatory assertion failure."""
    try:
        return case_api.create_case_server(store, **options)
    except TypeError as error:
        test.fail(f"case-server profile contract rejected its arguments: {error}")


class CloudProfileConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def cloud_server(self, **options):
        return create_server(self, None, token=options.pop("token", TOKEN), port=0,
                             deployment_profile=options.pop("deployment_profile", CLOUD_PROFILE),
                             allowed_hosts=options.pop("allowed_hosts", [CLOUD_HOST]), **options)

    def test_default_local_profile_rejects_managed_markers_before_store_access(self):
        for markers in ({"K_SERVICE": ""}, {"CLOUD_RUN_JOB": "job"},
                        {"K_SERVICE": "service", "CLOUD_RUN_JOB": "job"}):
            with self.subTest(markers=markers), patch.dict(os.environ, markers, clear=True):
                with self.assertRaisesRegex(ValueError, "^managed_cloud_unsupported$"):
                    case_api.create_case_server(None, token=TOKEN, port=0)

    def test_factory_default_never_opts_in_from_environment(self):
        with patch.dict(os.environ, {"PROOFKEY_DEPLOYMENT_PROFILE": CLOUD_PROFILE, "K_SERVICE": "service"}):
            with self.assertRaisesRegex(ValueError, "^managed_cloud_unsupported$"):
                case_api.create_case_server(None, token=TOKEN, port=0)

    def test_unknown_profiles_fail_before_store_access(self):
        for profile in ("", "cloud", "CLOUD-RUN-CASE-V1", "local ", None, 1):
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(ValueError, "^invalid_deployment_profile$"):
                    self.cloud_server(deployment_profile=profile)

    def test_cloud_serve_rejects_job_marker_before_store_access(self):
        for markers in ({"CLOUD_RUN_JOB": ""}, {"K_SERVICE": "service", "CLOUD_RUN_JOB": "job"}):
            with self.subTest(markers=markers), patch.dict(os.environ, markers, clear=True):
                with self.assertRaisesRegex(ValueError, "^managed_cloud_unsupported$"):
                    self.cloud_server()

    def test_cloud_requires_explicit_nonempty_host_list(self):
        for hosts in (None, [], (), CLOUD_HOST, {CLOUD_HOST}, [None], [""]):
            with self.subTest(hosts=hosts):
                with self.assertRaisesRegex(ValueError, "^invalid_allowed_hosts$"):
                    self.cloud_server(allowed_hosts=hosts)

    def test_cloud_rejects_malformed_authorities_before_store_access(self):
        invalid = (
            "*.run.app", "*.run.app:443", "https://case.run.app", "case.run.app/path",
            "case.run.app?query=1", "case.run.app#fragment", "user@case.run.app", "case.run.app\\evil",
            " case.run.app", "case.run.app ", "case. run.app", "case.run.app\t", "case.run.app\n",
            "case..run.app", ".case.run.app", "case.run.app.", "-case.run.app", "case-.run.app",
            "case._run.app", "café.run.app", "a" * 64 + ".run.app", ".".join(["a" * 63] * 4),
            "case.run.app:", "case.run.app:0", "case.run.app:65536", "case.run.app:999999",
            "case.run.app:-1", "case.run.app:+443", "case.run.app:443:80", "[::1]", "[::1]:443",
        )
        for authority in invalid:
            with self.subTest(authority=authority):
                with self.assertRaisesRegex(ValueError, "^invalid_allowed_hosts$"):
                    self.cloud_server(allowed_hosts=[authority])

    def test_cloud_requires_a_strong_printable_ascii_token(self):
        for token in (None, 1, "", "a" * 31, "a" * 4097, "a" * 32 + "\n",
                      "a" * 32 + "\t", "a" * 32 + "é", "a" * 31 + " "):
            with self.subTest(token=token):
                with self.assertRaisesRegex(ValueError, "^invalid_service_token$"):
                    self.cloud_server(token=token)

    def test_local_keeps_explicit_port_requirement(self):
        with self.assertRaisesRegex(ValueError, "^invalid_allowed_hosts$"):
            case_api.create_case_server(None, token=TOKEN, port=0, allowed_hosts=[CLOUD_HOST])

    def test_cli_unknown_profile_is_sanitized_before_database_configuration(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"PROOFKEY_DEPLOYMENT_PROFILE": "private-invalid-profile"}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(case_api.main(["serve"]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(json.loads(err.getvalue()), {"error": "case_service_start_failed"})


@unittest.skipUnless(DSN, "set PROOFKEY_TEST_DATABASE_URL to a disposable PostgreSQL database")
class CloudProfilePostgresTests(unittest.TestCase):
    def setUp(self):
        from tools.dwelly_service.postgres import migrate
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.schema = "cloud_test_" + uuid.uuid4().hex
        self.addCleanup(self.drop_schema)
        migrate(DSN, schema=self.schema)

    def drop_schema(self):
        self.drop_named_schema(self.schema)

    @staticmethod
    def drop_named_schema(schema):
        import psycopg
        from psycopg import sql
        with psycopg.connect(DSN) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))

    def store(self):
        from tools.dwelly_service.postgres import PostgresCaseStore
        store = PostgresCaseStore(DSN, schema=self.schema, max_size=1)
        self.addCleanup(store.close)
        return store

    def start(self, *, deployment_profile=CLOUD_PROFILE, token=TOKEN, allowed_hosts=None):
        server = create_server(self, self.store(), token=token, port=0,
                               deployment_profile=deployment_profile,
                               allowed_hosts=[CLOUD_HOST] if allowed_hosts is None else allowed_hosts)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            server.server_close()
            thread.join(3)

        self.addCleanup(stop)
        return server

    def request(self, server, method="GET", path="/v1/capabilities", *, host=CLOUD_HOST,
                token=TOKEN, headers=(), body=None):
        payload = json.dumps(body).encode() if body is not None else b""
        client = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        try:
            client.putrequest(method, path, skip_host=True)
            client.putheader("Host", host)
            if token is not None:
                client.putheader("Authorization", "Bearer " + token)
            if body is not None:
                client.putheader("Content-Type", "application/json")
                client.putheader("Content-Length", str(len(payload)))
            for name, value in headers:
                client.putheader(name, value)
            client.endheaders(payload)
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()

    def test_cloud_serve_accepts_service_marker_and_local_simulation(self):
        for markers, token in (({}, "a" * 32), ({"K_SERVICE": "service"}, "a" * 4096)):
            with self.subTest(markers=markers), patch.dict(os.environ, markers, clear=True):
                server = self.start(token=token)
                status, capabilities = self.request(server, token=token)
                self.assertEqual(status, 200)
                self.assertEqual(capabilities["deployment_profile"], CLOUD_PROFILE)
                self.assertTrue(capabilities["managed_cloud_enabled"])
                self.assertFalse(capabilities["case_intake"]["automated_analysis"])
                self.assertIsNone(capabilities["case_intake"]["runtime_binding"])
                self.assertEqual(capabilities["operational_effects"], 0)

    def test_local_default_keeps_loopback_bind_and_short_token(self):
        server = self.start(deployment_profile="local", token="a" * 16, allowed_hosts=[])
        self.assertEqual(server.server_address[0], "127.0.0.1")
        status, capabilities = self.request(server, host=f"localhost:{server.server_address[1]}", token="a" * 16)
        self.assertEqual(status, 200)
        self.assertEqual(capabilities["deployment_profile"], "local")
        self.assertFalse(capabilities["managed_cloud_enabled"])

    def test_cloud_accepts_exact_dns_authorities_and_preserves_port_distinction(self):
        server = self.start(allowed_hosts=[CLOUD_HOST, "explicit-port.run.app:443", "MIXED.run.app",
                                           "a" * 63 + ".run.app", "boundary.run.app:65535"])
        for authority in (CLOUD_HOST, "explicit-port.run.app:443", "mixed.RUN.app",
                          "a" * 63 + ".run.app", "boundary.run.app:65535"):
            with self.subTest(authority=authority):
                self.assertEqual(self.request(server, host=authority)[0], 200)
        for authority in (CLOUD_HOST + ":443", "explicit-port.run.app", "other.run.app",
                          CLOUD_HOST + ".evil.example", "boundary.run.app:065535"):
            with self.subTest(authority=authority):
                self.assertEqual(self.request(server, host=authority), (403, {"error": "forbidden"}))

    def test_cloud_retains_literal_loopback_health_authorities(self):
        server = self.start()
        for hostname in ("127.0.0.1", "localhost"):
            for path, expected in (("/healthz", {"status": "ok"}), ("/readyz", {"status": "ready"})):
                with self.subTest(hostname=hostname, path=path):
                    self.assertEqual(self.request(server, path=path, host=f"{hostname}:{server.server_address[1]}",
                                                  token=None), (200, expected))

    def test_cloud_keeps_bearer_origin_and_duplicate_header_guards(self):
        server = self.start()
        self.assertEqual(self.request(server, token=None), (401, {"error": "unauthorized"}))
        self.assertEqual(self.request(server, token="wrong"), (401, {"error": "unauthorized"}))
        self.assertEqual(self.request(server, token=None, headers=(("X-Serverless-Authorization", "Bearer unverified"),)),
                         (401, {"error": "unauthorized"}))
        for origin in ("null", "https://" + CLOUD_HOST, "https://evil.example"):
            with self.subTest(origin=origin):
                self.assertEqual(self.request(server, headers=(("Origin", origin),)), (403, {"error": "forbidden"}))
        self.assertEqual(self.request(server, headers=(("Host", CLOUD_HOST),)), (403, {"error": "forbidden"}))
        self.assertEqual(self.request(server, headers=(("Authorization", "Bearer " + TOKEN),)),
                         (401, {"error": "unauthorized"}))

    def test_cloud_case_creation_remains_pending_with_no_worker_effect(self):
        server = self.start()
        body = {"case_id": "cloud-case", "links": {"order_id": "order", "customer_id": "customer",
                "operator_id": "operator"}, "participants": ["customer", "operator"], "language": "en"}
        status, snapshot = self.request(server, "POST", "/v1/cases", body=body,
                                        headers=(("Idempotency-Key", "cloud-create"),))
        self.assertEqual(status, 201)
        self.assertEqual(snapshot["analysis_status"], "pending_not_started")
        self.assertEqual(snapshot["authorization"], "unverified")
        self.assertEqual(snapshot["operational_effects"], 0)
        self.assertIsNone(snapshot["runtime_binding"])
        status, result = self.request(server, path="/v1/cases/cloud-case/analysis-jobs")
        self.assertEqual(status, 200)
        self.assertEqual([job["status"] for job in result["jobs"]], ["pending"])

    def cli_environment(self, **overrides):
        return {"PROOFKEY_DATABASE_URL": DSN, "PROOFKEY_DATABASE_SCHEMA": self.schema,
                "PROOFKEY_SERVICE_TOKEN": TOKEN, "PROOFKEY_DEPLOYMENT_PROFILE": CLOUD_PROFILE,
                "PROOFKEY_ALLOWED_HOSTS": CLOUD_HOST, "PORT": "0", **overrides}

    def test_cli_cloud_default_binds_all_ipv4_interfaces_and_local_stays_loopback(self):
        for profile, expected_host in ((CLOUD_PROFILE, "0.0.0.0"), ("local", "127.0.0.1")):
            bound_addresses = []

            def stop_after_bind(server):
                bound_addresses.append(server.server_address)
                raise KeyboardInterrupt

            env = self.cli_environment(PROOFKEY_DEPLOYMENT_PROFILE=profile,
                                       PROOFKEY_ALLOWED_HOSTS="localhost:8080")
            with self.subTest(profile=profile), patch.dict(os.environ, env, clear=True), \
                    patch.object(case_api.CaseServer, "serve_forever", stop_after_bind):
                self.assertEqual(case_api.main(["serve"]), 0)
            self.assertEqual(len(bound_addresses), 1)
            self.assertEqual(bound_addresses[0][0], expected_host)

    def test_cli_cloud_does_not_strip_invalid_host_whitespace_or_empty_entries(self):
        for hosts in (" " + CLOUD_HOST, CLOUD_HOST + " ", CLOUD_HOST + ",", "," + CLOUD_HOST, ""):
            def unexpected_serve(server):
                self.fail("invalid cloud host configuration reached serve_forever")

            err = io.StringIO()
            with self.subTest(hosts=hosts):
                with patch.dict(os.environ, self.cli_environment(PROOFKEY_ALLOWED_HOSTS=hosts), clear=True), \
                        patch.object(case_api.CaseServer, "serve_forever", unexpected_serve), contextlib.redirect_stderr(err):
                    self.assertEqual(case_api.main(["serve"]), 2)
                self.assertEqual(json.loads(err.getvalue()), {"error": "case_service_start_failed"})

    def test_cli_migrate_allows_only_job_marker_or_local_cloud_simulation(self):
        import psycopg
        for markers in ({}, {"CLOUD_RUN_JOB": "job"}):
            env = self.cli_environment(**markers)
            env.pop("PROOFKEY_SERVICE_TOKEN")
            env.pop("PROOFKEY_ALLOWED_HOSTS")
            with self.subTest(markers=markers):
                with patch.dict(os.environ, env, clear=True), \
                        contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(case_api.main(["migrate"]), 0)
                self.assertEqual(json.loads(output.getvalue()), {"status": "migrated", "operational_effects": 0})
        with psycopg.connect(DSN) as connection:
            self.assertEqual(connection.execute("SELECT version FROM " + self.schema + ".schema_migrations").fetchall(), [(1,)])

    def test_cli_rejected_profile_marker_combinations_never_migrate(self):
        import psycopg
        for profile, markers in ((None, {"K_SERVICE": "service"}), (None, {"CLOUD_RUN_JOB": "job"}),
                                 ("local", {"K_SERVICE": "service"}), ("local", {"CLOUD_RUN_JOB": "job"}),
                                 (CLOUD_PROFILE, {"K_SERVICE": "service"}),
                                 (CLOUD_PROFILE, {"K_SERVICE": "service", "CLOUD_RUN_JOB": "job"}),
                                 ("private-unknown-profile", {})):
            absent_schema = "denied_" + uuid.uuid4().hex
            self.addCleanup(self.drop_named_schema, absent_schema)
            env = self.cli_environment(PROOFKEY_DEPLOYMENT_PROFILE=profile,
                                       PROOFKEY_DATABASE_SCHEMA=absent_schema, **markers)
            if profile is None:
                env.pop("PROOFKEY_DEPLOYMENT_PROFILE")
            err = io.StringIO()
            with self.subTest(profile=profile, markers=markers):
                with patch.dict(os.environ, env, clear=True), contextlib.redirect_stderr(err), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(case_api.main(["migrate"]), 2)
                self.assertEqual(json.loads(err.getvalue()), {"error": "case_service_start_failed"})
                with psycopg.connect(DSN) as connection:
                    self.assertEqual(connection.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s",
                                                        (absent_schema,)).fetchall(), [])


if __name__ == "__main__":
    unittest.main()
