"""In-process API boundary tests; no service or native authentication."""
import asyncio
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import warnings
from unittest.mock import patch

from starlette.exceptions import StarletteDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient` is deprecated;.*",
                            category=StarletteDeprecationWarning)
    from fastapi.testclient import TestClient

from proofkey.api import create_app, serve_loopback
from proofkey.clock import SyntheticReplayClock
from proofkey.contracts import AuthContext, CanonicalRequest
from proofkey.host import AuthResolver, ProfileRegistry, RuntimeFactory
from proofkey.host_contracts import HostLimitsV1, InterfaceLimitsV1


def canonical(kind="reschedule_window"):
    return CanonicalRequest(case_id="C1", object_id="O1", principal_id="U1", request_id="REQ1",
        request_revision="v1", consent_revision="v1", kind=kind,
        consent_mode="window" if kind == "reschedule_window" else "unknown",
        arguments={"window_start": "2026-10-08T10:00:00+00:00", "window_end": "2026-10-08T12:00:00+00:00",
                   "inventory": {"item-1": 1}} if kind == "reschedule_window" else {"inventory": {"item-1": 1}},
        evidence_ids=[])


class ObservedFactory(RuntimeFactory):
    def __init__(self, *, entered=None, release=None):
        self.created, self.contexts, self.owners, self.snapshots, self.closed = [], [], [], [], []
        self.entered, self.release = entered, release

    def create(self, registered, clock):
        resource = super().create(registered, clock)
        self.created.append(resource)
        engine, original_close, observer = resource.engine, resource.close, self
        def close():
            observer.closed.append(threading.get_ident())
            return original_close()
        resource.close = close
        class Forward:
            def __getattr__(self, name):
                actual = getattr(engine, name)
                if not callable(actual):
                    return actual
                def invoke(*args, **kwargs):
                    observer.contexts.append(kwargs.get("execution"))
                    observer.owners.append(threading.get_ident())
                    if observer.entered is not None:
                        observer.entered.set()
                        if not observer.release.wait(3):
                            raise RuntimeError("test forwarding barrier not released")
                    result = actual(*args, **kwargs)
                    if resource.store.has_case("C1"):
                        observer.snapshots.append((resource.store.checkpoint("C1"), resource.store.intents("C1"),
                            tuple(resource.world.calls), {op: resource.world.effect_count(op) for op in
                                ("reschedule", "register_goods_refusal", "create_return")},
                            resource.store.original_request("C1", "G1")))
                    return result
                return invoke
        resource.engine = Forward()
        return resource


class ApiFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.output = self.base / "outputs"; self.output.mkdir()
        self.inventory = self.base / "inventories"; self.inventory.mkdir()
        self.clock = SyntheticReplayClock()
        self.registry = ProfileRegistry.builtin(self.base / "resources")
        self.resolver = AuthResolver({"user": AuthContext(caller_id="U1", proof_reference="synthetic-proof"),
            "wrong": AuthContext(caller_id="U1", proof_reference="wrong-proof")})
        self.factory = ObservedFactory()
        self.options = dict(runtime_factory=self.factory, auth_resolver=self.resolver,
            profile_registry=self.registry, host_limits=HostLimitsV1(), release_id="host-window-replay-v1",
            clock=self.clock, inventory_root=self.inventory, output_parent=self.output,
            interface_limits=InterfaceLimitsV1(), transport_proof_resolver=self.resolver.handle,
            total_seconds=5.0, export_reserve_seconds=1.0, shutdown_seconds=0.3)
        self.headers = {"x-proofkey-proof": "user"}

    def app(self, **changes):
        return create_app(**{**self.options, **changes})

    def command(self, **changes):
        return {"tag": "run", "release_id": "host-window-replay-v1", "request": canonical().model_dump(mode="json"), **changes}

    async def request(self, app, path, *, chunks=None, disconnect=None, before_chunk=None):
        chunks = list(chunks if chunks is not None else [json.dumps(self.command()).encode()])
        responses, reads = [], []
        never = asyncio.Event()
        async def receive():
            if chunks:
                if before_chunk is not None:
                    await before_chunk(len(reads))
                value = chunks.pop(0); reads.append(len(value))
                return {"type": "http.request", "body": value, "more_body": bool(chunks)}
            if disconnect is not None:
                await disconnect.wait()
                return {"type": "http.disconnect"}
            await never.wait()
        async def send(message):
            responses.append(message)
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": path, "raw_path": path.encode(),
            "query_string": b"", "headers": [(b"x-proofkey-proof", b"user")],
            "client": ("127.0.0.1", 1), "server": ("127.0.0.1", 2), "root_path": ""}
        await app(scope, receive, send)
        status = next(m["status"] for m in responses if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in responses if m["type"] == "http.response.body")
        return status, json.loads(body), reads

    async def until(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate():
            if time.monotonic() >= deadline:
                self.fail("actual forwarding/state barrier was not observed")
            await asyncio.sleep(0.002)


class ApiBoundaryTests(ApiFixture):
    def test_rejected_inventory_configuration_closes_successful_output_descriptors(self):
        import errno
        import proofkey.api as api
        opened, closed = [], []
        actual_open, actual_close = api.os.open, api.os.close

        def observe_open(*args, **kwargs):
            descriptor = actual_open(*args, **kwargs)
            opened.append(descriptor)
            return descriptor

        def observe_close(descriptor):
            result = actual_close(descriptor)
            closed.append(descriptor)
            return result

        try:
            with patch.object(api.os, "open", observe_open), patch.object(api.os, "close", observe_close):
                with self.assertRaisesRegex(ValueError, "Invalid trusted API configuration"):
                    self.app(inventory_root=Path("relative-inventory"))
            self.assertTrue(opened, "the real output parent must successfully open before inventory rejection")
            self.assertEqual(sorted(opened), sorted(closed), "all successfully acquired output descriptors must close")
            for descriptor in opened:
                with self.assertRaises(OSError) as rejected:
                    api.os.fstat(descriptor)
                self.assertEqual(rejected.exception.errno, errno.EBADF)
            self.assertEqual(self.factory.created, [])
            self.assertEqual(list(self.output.iterdir()), [])
        finally:
            # Clean up the actual leak on RED; production owns successful opens.
            for descriptor in opened:
                if descriptor not in closed:
                    actual_close(descriptor)

    def test_shutdown_atomically_prevents_valid_queued_wrapper_entry(self):
        import proofkey.api as api
        app = self.app(max_wrapper_jobs=1, max_wrapper_workers=1, total_seconds=10,
                       export_reserve_seconds=2)
        lifecycle = app.state.api_lifecycle
        boundary, resume, allow_worker, worker_done = (threading.Event() for _ in range(4))
        depths, public_entries, callback_depths, shutdown_errors = {}, [], [], []

        class BoundaryCondition(threading.Condition):
            def __enter__(condition):
                result = super().__enter__()
                ident = threading.get_ident()
                depths[ident] = depths.get(ident, 0) + 1
                return result

            def __exit__(condition, *args):
                ident = threading.get_ident()
                depths[ident] -= 1
                result = super().__exit__(*args)
                if (threading.current_thread().name == "api-fix1-shutdown" and lifecycle.closing
                        and not boundary.is_set()):
                    boundary.set()
                    if not resume.wait(5):
                        raise RuntimeError("test shutdown boundary not released")
                return result

            def wait_for(condition, predicate, timeout=None):
                if threading.current_thread().name.startswith("proofkey-api-worker"):
                    super().wait_for(allow_worker.is_set, timeout)
                return super().wait_for(predicate, timeout)

        lifecycle.condition = BoundaryCondition()
        original_worker, original_run = lifecycle.worker, api.run_command
        def worker():
            try:
                return original_worker()
            finally:
                worker_done.set()
        lifecycle.worker = worker
        def run(*args, **kwargs):
            public_entries.append(kwargs["execution"])
            return original_run(*args, **kwargs)

        async def exercise():
            manager = app.router.lifespan_context(app)
            await manager.__aenter__()
            request = asyncio.create_task(self.request(app, "/v1/commands"))
            await self.until(lambda: lifecycle.snapshot()["queued"] == 1)
            with lifecycle.condition:
                job = next(iter(lifecycle.jobs.values()))
            job.future.add_done_callback(lambda completed: callback_depths.append(depths.get(threading.get_ident(), 0)))
            def close():
                try:
                    asyncio.run(manager.__aexit__(None, None, None))
                except BaseException as error:
                    shutdown_errors.append(error)
            shutdown = threading.Thread(target=close, name="api-fix1-shutdown")
            shutdown.start()
            try:
                await self.until(boundary.is_set)
                self.assertTrue(job.execution.remaining_seconds(self.clock) > 0)
                allow_worker.set()
                with lifecycle.condition:
                    lifecycle.condition.notify_all()
                await self.until(worker_done.is_set)
                self.assertEqual(public_entries, [], "a queued-at-close wrapper must never enter the real common library")
                self.assertEqual(self.factory.created, [])
                self.assertEqual(list(self.output.iterdir()), [])
                self.assertEqual(lifecycle.snapshot(), {"admitted": 1, "queued": 0, "running": 0,
                    "completed": 1, "pending_wrapper_ids": ()})
            finally:
                resume.set()
                await self.until(lambda: not shutdown.is_alive())
                shutdown.join(0)
                status, facts, _ = await request
            self.assertEqual(shutdown_errors, [])
            self.assertEqual((status, facts["kind"], facts["wrapper_id"]),
                (409, "api-wrapper-not-started-v1", job.wrapper_id))
            self.assertEqual(callback_depths, [0], "future callbacks must run outside the state lock")
            self.assertEqual(lifecycle.shutdown_receipt.status, "closed")
            self.assertEqual(lifecycle.shutdown_receipt.completed, 1)
            self.assertTrue(lifecycle.shutdown_receipt.host_shutdown.owner_closed)
        with patch.object(api, "run_command", run):
            asyncio.run(exercise())

    def test_missing_transport_proof_denies_before_body_or_source_entry(self):
        app = self.app()
        with TestClient(app) as client:
            response = client.post("/v1/commands", json=self.command())
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"kind": "api-failure-v1", "failure": "scope_denied"})
            self.assertEqual(self.factory.created, [])
            self.assertEqual(list(self.output.iterdir()), [])

    def test_profile_uses_actual_public_receipt_and_closes_one_creator_owner(self):
        app = self.app()
        with TestClient(app) as client:
            response = client.get("/v1/profile", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            facts = response.json()
            self.assertEqual(facts["kind"], "host-command-run-receipt-v1")
            self.assertEqual(facts["command"]["outcome"], "inspection")
            self.assertEqual(facts["command"]["inspection"]["release_id"], "host-window-replay-v1")
            self.assertEqual(facts["export_outcome"], "not_attempted")
        shutdown = app.state.api_lifecycle.shutdown_receipt
        self.assertEqual(shutdown.status, "closed")
        self.assertTrue(shutdown.host_shutdown.owner_closed)
        self.assertEqual(shutdown.completed, 1)

    def test_invalid_foreign_proof_and_body_authority_never_construct_runtime(self):
        app = self.app(transport_proof_resolver=lambda value: object())
        with TestClient(app) as client:
            self.assertEqual(client.post("/v1/commands", json=self.command(), headers=self.headers).status_code, 401)
        app = self.app()
        with TestClient(app) as client:
            for key in ("auth", "proof_reference", "deadline", "output_root"):
                response = client.post("/v1/commands", json=self.command(**{key: "body-grant"}), headers=self.headers)
                self.assertEqual(response.status_code, 400)
            response = client.post("/v1/commands", json=self.command(release_id="unregistered"), headers=self.headers)
            self.assertEqual(response.status_code, 403)
            changed = self.command(); changed["request"]["arguments"]["inventory"]["item-1"] = 99
            self.assertEqual(client.post("/v1/commands", json=changed, headers=self.headers).status_code, 403)
        self.assertEqual(self.factory.created, [])

    def test_invalid_batch_documents_do_not_allocate_runs_or_source(self):
        with TestClient(self.app()) as client:
            for data in (b'{}', b'[{"case_id":"C1","case_id":"C2"}]', b'[NaN]', b'[' * 40 + b'0' + b']' * 40):
                with self.subTest(data=data):
                    response = client.post("/v1/batch", content=data, headers=self.headers)
                    self.assertEqual(response.status_code, 400)
        self.assertEqual(self.factory.created, [])
        self.assertEqual(list(self.output.iterdir()), [])

    def test_all_n_valid_document_keeps_invalid_rows_and_actual_positive(self):
        rows = [{}, {"case_id": 7}, 3, {"case_id": "../bad"}, canonical().model_dump(mode="json")]
        data = json.dumps(rows).encode()
        with TestClient(self.app()) as client:
            response = client.post("/v1/batch", content=data, headers=self.headers)
            self.assertEqual(response.status_code, 400)
            facts = response.json()
            self.assertEqual(facts["position_count"], 5)
            self.assertEqual([p["inventory"]["ordinal"] for p in facts["positions"]], [0, 1, 2, 3, 4])
            self.assertEqual([p["execution_outcome"] for p in facts["positions"]],
                ["invalid_request", "invalid_request", "invalid_request", "invalid_request", "result"])
            self.assertEqual(facts["input"]["input_hash"], sha256(data).hexdigest())
            self.assertEqual(facts["positions"][4]["command"]["result"]["status"], "authorized")

    def test_constructor_rejects_bad_trusted_bounds_and_paths(self):
        for changes in ({"total_seconds": float("nan")}, {"export_reserve_seconds": 0.0000001},
                {"total_seconds": True}, {"shutdown_seconds": 31}, {"max_wrapper_jobs": 9},
                {"max_wrapper_workers": 3}, {"max_wrapper_jobs": True}, {"release_id": "unknown"},
                {"inventory_root": "relative"}, {"output_parent": "relative"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.app(**changes)
        alias = self.base / "alias"; alias.symlink_to(self.output, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.app(output_parent=alias)
        self.assertEqual(self.factory.created, [])

    def test_no_public_polling_or_shutdown_routes(self):
        with TestClient(self.app()) as client:
            for route in ("/v1/results/test", "/v1/commands/test", "/v1/shutdown", "/docs", "/openapi.json"):
                self.assertEqual(client.get(route, headers=self.headers).status_code, 404)

    def test_loopback_helper_rejects_unsafe_values_without_server(self):
        app = self.app()
        for host in ("localhost", "0.0.0.0", "192.0.2.1", "::", "127.0.0.1.example"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                serve_loopback(app, host=host)
        for port in (True, 0, 65536, "8000"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                serve_loopback(app, port=port)
        with patch("uvicorn.run") as serving:
            serve_loopback(app, host="::1", port=8000)
            self.assertEqual(serving.call_args.kwargs, {"host": "::1", "port": 8000})

    def test_stream_limit_stops_before_later_chunks_and_body_time_consumes_original_window(self):
        async def exercise():
            app = self.app(interface_limits=InterfaceLimitsV1(max_input_bytes=256))
            async with app.router.lifespan_context(app):
                status, facts, reads = await self.request(app, "/v1/batch", chunks=[b"[" * 128, b" " * 129, b"never-read"])
                self.assertEqual(status, 400)
                self.assertEqual(reads, [128, 129])
                self.assertEqual(facts["failure"], "invalid_input")
            app = self.app(total_seconds=0.12, export_reserve_seconds=0.04)
            async def delay(index):
                await asyncio.sleep(0.10)
            async with app.router.lifespan_context(app):
                status, facts, reads = await self.request(app, "/v1/commands", before_chunk=delay)
                self.assertEqual(status, 408)
                self.assertEqual(facts["failure"], "deadline_exceeded")
            self.assertEqual(self.factory.created, [])
        asyncio.run(exercise())

    def test_real_queue_full_queued_disconnect_and_entered_pending_are_distinct(self):
        entered, release = threading.Event(), threading.Event()
        factory = ObservedFactory(entered=entered, release=release)
        app = self.app(runtime_factory=factory, max_wrapper_jobs=2, max_wrapper_workers=1,
                       total_seconds=1.0, export_reserve_seconds=0.3)
        async def exercise():
            first_disconnect, queued_disconnect = asyncio.Event(), asyncio.Event()
            try:
                async with app.router.lifespan_context(app):
                    first = asyncio.create_task(self.request(app, "/v1/commands", disconnect=first_disconnect))
                    await self.until(entered.is_set)
                    second = asyncio.create_task(self.request(app, "/v1/commands", disconnect=queued_disconnect))
                    await self.until(lambda: app.state.api_lifecycle.snapshot()["queued"] == 1)
                    status, facts, _ = await self.request(app, "/v1/commands")
                    self.assertEqual((status, facts["failure"]), (409, "queue_full"))
                    queued_disconnect.set()
                    status, facts, _ = await second
                    self.assertEqual(status, 409)
                    self.assertEqual(facts["kind"], "api-wrapper-not-started-v1")
                    self.assertEqual(facts["outcome"], "not_started")
                    queued_id = facts["wrapper_id"]
                    first_disconnect.set()
                    status, facts, _ = await first
                    self.assertEqual(status, 202)
                    self.assertEqual(facts["kind"], "api-wrapper-pending-v1")
                    self.assertEqual(facts["outcome"], "wrapper_pending")
                    self.assertIsNone(facts["failure"])
                    self.assertNotEqual(facts["wrapper_id"], queued_id)
                    self.assertEqual(len(factory.contexts), 1)
                    self.assertEqual(len(list(self.output.iterdir())), 1)
                    release.set()
                    await self.until(lambda: app.state.api_lifecycle.snapshot()["running"] == 0)
            finally:
                release.set()
        asyncio.run(exercise())
        self.assertEqual(app.state.api_lifecycle.shutdown_receipt.status, "closed")
        self.assertEqual(app.state.api_lifecycle.shutdown_receipt.admitted, 2)
        self.assertEqual(app.state.api_lifecycle.shutdown_receipt.completed, 2)

    def test_shutdown_is_bounded_retains_actual_pending_threads_and_eventual_terminal(self):
        entered, release = threading.Event(), threading.Event()
        factory = ObservedFactory(entered=entered, release=release)
        app = self.app(runtime_factory=factory, total_seconds=1, export_reserve_seconds=0.3, shutdown_seconds=0.03)
        async def exercise():
            disconnect = asyncio.Event()
            try:
                async with app.router.lifespan_context(app):
                    task = asyncio.create_task(self.request(app, "/v1/commands", disconnect=disconnect))
                    await self.until(entered.is_set)
                    disconnect.set()
                    status, facts, _ = await task
                    self.assertEqual(status, 202)
                    self.pending_id = facts["wrapper_id"]
                    started = time.monotonic()
                self.assertLess(time.monotonic() - started, 0.2)
                shutdown = app.state.api_lifecycle.shutdown_receipt
                self.assertEqual(shutdown.status, "pending")
                self.assertEqual(shutdown.running, 1)
                self.assertIn(self.pending_id, shutdown.pending_wrapper_ids)
                self.assertFalse(shutdown.host_shutdown.owner_closed)
                self.assertTrue(any(t.name == "proofkey-runtime-owner" and t.is_alive() for t in threading.enumerate()))
                self.assertTrue(any(t.name.startswith("proofkey-api-worker") and t.is_alive() for t in threading.enumerate()))
            finally:
                release.set()
                await self.until(lambda: app.state.api_lifecycle.snapshot()["running"] == 0)
        asyncio.run(exercise())
        self.assertEqual(len(factory.closed), 1)
        terminal = app.state.api_lifecycle.terminal_facts[-1]
        self.assertEqual(terminal.wrapper_id, self.pending_id)
        self.assertIsNotNone(terminal.receipt)

    def test_actual_publication_failure_preserves_common_receipt(self):
        with patch("proofkey.batch.RunPublisher.publish_final", side_effect=OSError("private-secret-path")):
            with TestClient(self.app()) as client:
                response = client.post("/v1/commands", json=self.command(), headers=self.headers)
                self.assertEqual(response.status_code, 503)
                facts = response.json()
                self.assertEqual(facts["kind"], "host-command-run-receipt-v1")
                self.assertEqual(facts["publication_status"], "partial")
                self.assertEqual(facts["command"]["result"]["status"], "authorized")
                self.assertNotIn("private-secret-path", response.text)
                self.assertIsNone(facts["final_reference"])

    def test_batch_disconnect_signals_original_event_and_prevents_next_ordinal(self):
        entered, release = threading.Event(), threading.Event()
        factory = ObservedFactory(entered=entered, release=release)
        app = self.app(runtime_factory=factory)
        async def exercise():
            disconnect = asyncio.Event()
            try:
                async with app.router.lifespan_context(app):
                    data = json.dumps([canonical().model_dump(mode="json")] * 2).encode()
                    task = asyncio.create_task(self.request(app, "/v1/batch", chunks=[data], disconnect=disconnect))
                    await self.until(entered.is_set)
                    disconnect.set()
                    status, facts, _ = await task
                    self.assertEqual(status, 202)
                    self.assertEqual(facts["kind"], "api-wrapper-pending-v1")
                    release.set()
                    await self.until(lambda: app.state.api_lifecycle.snapshot()["running"] == 0)
                    terminal = app.state.api_lifecycle.terminal_facts[-1].receipt
                    self.assertEqual(terminal.position_count, 2)
                    self.assertEqual(terminal.positions[0].execution_outcome, "result")
                    self.assertEqual(terminal.positions[1].execution_outcome, "not_started")
                    self.assertEqual(len(factory.contexts), 1)
                    self.assertEqual(factory.snapshots[-1][3]["reschedule"], 1)
            finally:
                release.set()
        asyncio.run(exercise())

    def test_default_pool_rejects_ninth_and_never_enters_more_than_two_wrappers(self):
        entered, release = threading.Event(), threading.Event()
        app = self.app(runtime_factory=ObservedFactory(entered=entered, release=release))
        async def exercise():
            disconnected = asyncio.Event()
            try:
                async with app.router.lifespan_context(app):
                    tasks = [asyncio.create_task(self.request(app, "/v1/commands", disconnect=disconnected)) for _ in range(8)]
                    await self.until(lambda: app.state.api_lifecycle.snapshot()["admitted"] == 8)
                    await self.until(lambda: app.state.api_lifecycle.snapshot()["running"] == 2)
                    self.assertEqual(app.state.api_lifecycle.snapshot()["queued"], 6)
                    status, facts, _ = await self.request(app, "/v1/commands")
                    self.assertEqual((status, facts["failure"]), (409, "queue_full"))
                    disconnected.set()
                    replies = await asyncio.gather(*tasks)
                    self.assertEqual(sum(facts["kind"] == "api-wrapper-not-started-v1" for _, facts, _ in replies), 6)
                    self.assertEqual(sum(facts["kind"] == "api-wrapper-pending-v1" for _, facts, _ in replies), 2)
                    release.set()
                    await self.until(lambda: app.state.api_lifecycle.snapshot()["running"] == 0)
                    self.assertEqual(len(list(self.output.iterdir())), 2)
            finally:
                release.set()
        asyncio.run(exercise())

    def test_cold_setup_retains_ingress_context_and_expiry_cannot_enter_engine(self):
        class SlowFactory(ObservedFactory):
            def create(observer, registered, clock):
                observer.setup_at = clock.now()
                time.sleep(0.10)
                return super().create(registered, clock)
        factory = SlowFactory()
        app = self.app(runtime_factory=factory, total_seconds=0.30, export_reserve_seconds=0.22)
        with TestClient(app) as client:
            response = client.post("/v1/commands", json=self.command(), headers=self.headers)
            self.assertIn(response.status_code, (202, 408))
        self.assertEqual(factory.contexts, [])
        self.assertEqual(len(factory.created), 1)
        self.assertEqual(tuple(factory.created[0].world.calls), ())

    def test_shutdown_clock_failure_records_no_false_owner_close_and_can_be_cleaned_publicly(self):
        class FailingClock(SyntheticReplayClock):
            failed = False
            def now(clock):
                if clock.failed:
                    raise ValueError("clock failed")
                return super().now()
        clock = FailingClock()
        app = self.app(clock=clock)
        try:
            with TestClient(app) as client:
                self.assertEqual(client.get("/v1/profile", headers=self.headers).status_code, 200)
                clock.failed = True
            receipt = app.state.api_lifecycle.shutdown_receipt
            self.assertEqual(receipt.status, "failed")
            self.assertIsNone(receipt.host_shutdown)
            self.assertIsNone(receipt.started_at)
            self.assertTrue(any(t.name == "proofkey-runtime-owner" and t.is_alive() for t in threading.enumerate()))
        finally:
            clock.failed = False
            actual = app.state.api_lifecycle.dispatcher.close(clock.now() + timedelta(seconds=0.3))
            self.assertTrue(actual.owner_closed)

    def test_shutdown_does_not_wait_for_entered_publication_io(self):
        entered, release = threading.Event(), threading.Event()
        from proofkey.batch_files import RunPublisher
        original = RunPublisher.publish_final
        def forward(publisher, *args, **kwargs):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("test publication barrier not released")
            return original(publisher, *args, **kwargs)
        app = self.app(shutdown_seconds=0.03)
        async def exercise():
            disconnect = asyncio.Event()
            try:
                async with app.router.lifespan_context(app):
                    task = asyncio.create_task(self.request(app, "/v1/commands", disconnect=disconnect))
                    await self.until(entered.is_set)
                    disconnect.set()
                    self.assertEqual((await task)[0], 202)
                    start = time.monotonic()
                self.assertLess(time.monotonic() - start, 0.2)
                receipt = app.state.api_lifecycle.shutdown_receipt
                self.assertEqual(receipt.status, "pending")
                self.assertTrue(receipt.host_shutdown.owner_closed)
                self.assertEqual(receipt.running, 1)
            finally:
                release.set()
                await self.until(lambda: app.state.api_lifecycle.snapshot()["running"] == 0)
        with patch.object(RunPublisher, "publish_final", forward):
            asyncio.run(exercise())

    def test_duplicate_proof_headers_and_pre_body_disconnect_have_no_entry(self):
        with TestClient(self.app()) as client:
            response = client.post("/v1/commands", json=self.command(), headers=[("x-proofkey-proof", "user"),
                ("x-proofkey-proof", "user")])
            self.assertEqual(response.status_code, 401)
        async def exercise():
            app = self.app()
            event = asyncio.Event(); event.set()
            async with app.router.lifespan_context(app):
                status, facts, reads = await self.request(app, "/v1/commands", chunks=[], disconnect=event)
                self.assertEqual(status, 409)
                self.assertEqual(facts["failure"], "unavailable")
                self.assertEqual(reads, [])
        asyncio.run(exercise())
        self.assertEqual(self.factory.created, [])

    def test_original_context_precedes_transport_mapping_and_is_forwarded_unchanged(self):
        observed = []
        def mapping(value):
            observed.append(self.clock.now())
            time.sleep(0.03)
            return self.resolver.handle(value)
        with TestClient(self.app(transport_proof_resolver=mapping)) as client:
            response = client.post("/v1/commands", json=self.command(), headers=self.headers)
            self.assertEqual(response.status_code, 200)
        context = self.factory.contexts[0]
        self.assertLessEqual(context.captured_at, observed[0])
        self.assertEqual((context.deadline - context.captured_at).total_seconds(), 4.0)
        self.assertEqual(context.monotonic_deadline, context.captured_monotonic + 4.0)
        self.assertEqual(response.json()["window"]["execution"]["captured_at"],
                         context.captured_at.isoformat().replace("+00:00", "Z"))

    def test_new_completed_response_cannot_extend_original_publication_deadline(self):
        import proofkey.api as api
        original = api._await_job
        async def delayed(*args):
            receipt = await original(*args)
            await asyncio.sleep(0.17)
            return receipt
        app = self.app(total_seconds=0.15, export_reserve_seconds=0.05)
        with patch.object(api, "_await_job", delayed), TestClient(app) as client:
            response = client.get("/v1/profile", headers=self.headers)
            self.assertEqual(response.status_code, 408)
            self.assertEqual(response.json(), {"kind": "api-failure-v1", "failure": "deadline_exceeded"})
        self.assertEqual(app.state.api_lifecycle.terminal_facts[-1].receipt.command.outcome, "inspection")

    def test_mixed_actual_pending_and_export_failure_keeps_503_and_every_position(self):
        entered, release = threading.Event(), threading.Event()
        class LaterFactory(ObservedFactory):
            def create(observer, registered, clock):
                resource = super().create(registered, clock)
                engine = resource.engine
                class Later:
                    count = 0
                    def __getattr__(self, name):
                        actual = getattr(engine, name)
                        if not callable(actual):
                            return actual
                        def invoke(*args, **kwargs):
                            self.count += 1
                            if self.count == 2:
                                entered.set()
                                if not release.wait(4):
                                    raise RuntimeError("test pending replay barrier not released")
                            return actual(*args, **kwargs)
                        return invoke
                resource.engine = Later()
                return resource
        from proofkey.exporter import ExportFailure
        factory = LaterFactory()
        app = self.app(runtime_factory=factory, total_seconds=3, export_reserve_seconds=1.2)
        try:
            with patch("proofkey.batch.export_case", side_effect=ExportFailure("output_conflict")):
                with TestClient(app) as client:
                    rows = [canonical().model_dump(mode="json")] * 2
                    response = client.post("/v1/batch", json=rows, headers=self.headers)
                    self.assertTrue(entered.is_set())
                    self.assertEqual(response.status_code, 503)
                    facts = response.json()
                    self.assertEqual(facts["publication_status"], "committed")
                    self.assertEqual(facts["position_count"], 2)
                    self.assertEqual(facts["positions"][0]["command"]["result"]["status"], "authorized")
                    self.assertEqual(facts["positions"][0]["export_outcome"], "failed")
                    self.assertIsNone(facts["positions"][0]["export"])
                    self.assertEqual(facts["positions"][1]["command"]["outcome"], "started_pending")
                    self.assertEqual(facts["pending_command_ids"], [facts["positions"][1]["command"]["command_id"]])
                    release.set()
        finally:
            release.set()
