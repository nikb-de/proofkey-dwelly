"""Optional ASGI interface over one public owner; no native authentication."""
import asyncio
from collections import deque
from concurrent.futures import Future
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import math
import os
from pathlib import Path
import stat
import threading
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from pydantic import Field, model_validator
from starlette.responses import JSONResponse

from .batch import run_batch, run_command
from .contracts import NonnegativeFloat, Timestamp, WireModel
from .execution import ExecutionContext
from .host import HostDispatcher, ProfileRegistry, TransportProofHandle
from .host_contracts import (BatchRunReceiptV1, CommandRunReceiptV1, HostLimitsV1,
                            InspectProfileCommandV1, InterfaceLimitsV1, ShutdownReceiptV1, parse_command)

WrapperId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
Count = Annotated[int, Field(ge=0)]
FailureCode = Literal["invalid_input", "scope_denied", "queue_full", "unavailable",
                      "deadline_exceeded", "runtime_error", "publication_failed"]


class ApiFailureV1(WireModel):
    kind: Literal["api-failure-v1"] = "api-failure-v1"
    failure: FailureCode


class ApiWrapperPendingV1(WireModel):
    kind: Literal["api-wrapper-pending-v1"] = "api-wrapper-pending-v1"
    wrapper_id: WrapperId
    outcome: Literal["wrapper_pending"] = "wrapper_pending"
    failure: None = None


class ApiWrapperNotStartedV1(WireModel):
    kind: Literal["api-wrapper-not-started-v1"] = "api-wrapper-not-started-v1"
    wrapper_id: WrapperId
    outcome: Literal["not_started"] = "not_started"


class ApiShutdownReceiptV1(WireModel):
    kind: Literal["api-shutdown-receipt-v1"] = "api-shutdown-receipt-v1"
    admission_closed: bool
    admitted: Count
    queued: Count
    running: Count
    completed: Count
    pending_wrapper_ids: tuple[WrapperId, ...]
    host_shutdown: ShutdownReceiptV1 | None = None
    started_at: Timestamp | None
    finished_at: Timestamp | None
    elapsed_seconds: NonnegativeFloat | None
    overrun_seconds: NonnegativeFloat | None
    status: Literal["closed", "pending", "failed"]

    @model_validator(mode="before")
    @classmethod
    def json_tuples(cls, value, info):
        if info.mode == "json" and type(value) is dict:
            value = dict(value)
            if type(value.get("pending_wrapper_ids")) is list:
                value["pending_wrapper_ids"] = tuple(value["pending_wrapper_ids"])
            if type(value.get("host_shutdown")) is dict:
                host = dict(value["host_shutdown"])
                for name in ("pending_command_ids", "cancelled_command_ids"):
                    if type(host.get(name)) is list:
                        host[name] = tuple(host[name])
                value["host_shutdown"] = host
        return value

    @model_validator(mode="after")
    def factual_counts(self):
        if (self.admitted != self.completed + self.queued + self.running
                or len(self.pending_wrapper_ids) != self.queued + self.running
                or len(set(self.pending_wrapper_ids)) != len(self.pending_wrapper_ids)):
            raise ValueError("Inconsistent observed wrapper counts")
        if self.status == "closed" and (self.pending_wrapper_ids or self.host_shutdown is None
                                        or not self.host_shutdown.owner_closed):
            raise ValueError("Closed requires actual owner and wrapper completion")
        return self


def _seconds(value):
    if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
            or timedelta(seconds=value).total_seconds() != value):
        raise ValueError("Invalid trusted API configuration")
    return float(value)


def _sample(clock):
    mono, now = clock.monotonic(), clock.now()
    if (type(mono) not in (int, float) or not math.isfinite(mono)
            or not isinstance(now, datetime) or now.utcoffset() is None):
        raise ValueError("Unavailable API clock")
    return now.astimezone(timezone.utc), float(mono)


class _Parent:
    """API-owned no-follow ancestry; never a runtime/source handle."""
    def __init__(self, path):
        self.path, self.entries = Path(path), []
        if (not self.path.is_absolute() or ".." in self.path.parts or len(self.path.parts) > 64
                or len(str(self.path)) > 1024):
            raise ValueError("Invalid trusted API parent")
        try:
            parent = None
            for name in ("/", *self.path.parts[1:]):
                descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                observed = os.fstat(descriptor)
                self.entries.append((descriptor, parent, name, (observed.st_dev, observed.st_ino)))
                parent = descriptor
            self.check()
        except Exception:
            self.close()
            raise ValueError("Invalid trusted API parent") from None

    def check(self):
        for fd, parent, name, identity in self.entries:
            value = os.stat(name, dir_fd=parent, follow_symlinks=False)
            held = os.fstat(fd)
            if (not stat.S_ISDIR(value.st_mode) or (value.st_dev, value.st_ino) != identity
                    or (held.st_dev, held.st_ino) != identity):
                raise ValueError("Changed trusted API parent")

    def absent(self, name):
        self.check()
        try:
            os.stat(name, dir_fd=self.entries[-1][0], follow_symlinks=False)
        except FileNotFoundError:
            return self.path / name
        raise ValueError("API run output already exists")

    def close(self):
        for fd, _, _, _ in reversed(self.entries):
            os.close(fd)
        self.entries = []


@dataclass
class _Job:
    wrapper_id: str
    body: bytes
    batch: bool
    proof: object
    execution: ExecutionContext
    deadline: datetime
    output: Path
    cancellation: threading.Event = field(default_factory=threading.Event)
    future: Future = field(default_factory=Future)
    phase: str = "queued"
    terminal: object = None


@dataclass(frozen=True)
class _Terminal:
    wrapper_id: str
    receipt: object
    phase: str


class _Lifecycle:
    def __init__(self, clock, interface_limits, reserve, shutdown_seconds, jobs, workers, output, inventory):
        self.clock, self.limits, self.reserve, self.shutdown_seconds = clock, interface_limits, reserve, shutdown_seconds
        self.maximum, self.worker_count = jobs, workers
        self.output, self.inventory = output, inventory
        self.condition = threading.Condition()
        self.queue, self.jobs = deque(), {}
        self.terminal_facts = deque(maxlen=jobs)
        self.admitted = self.completed = self.live_workers = 0
        self.accepting, self.closing = False, False
        self.dispatcher = None
        self.workers = []
        self.shutdown_receipt = None

    def snapshot(self):
        with self.condition:
            queued = sum(job.phase == "queued" for job in self.jobs.values())
            running = sum(job.phase == "running" for job in self.jobs.values())
            return dict(admitted=self.admitted, completed=self.completed, queued=queued, running=running,
                        pending_wrapper_ids=tuple(self.jobs))

    def start(self, factory, resolver, registry, limits, release):
        try:
            self.output.check(); self.inventory.check()
            root = self.inventory.absent("HOST-" + uuid4().hex)
            self.dispatcher = HostDispatcher(factory, resolver, registry, self.clock, root, limits, release_id=release)
            for ordinal in range(self.worker_count):
                worker = threading.Thread(target=self.worker, name=f"proofkey-api-worker-{ordinal}", daemon=False)
                with self.condition:
                    self.live_workers += 1
                try:
                    worker.start()
                except Exception:
                    with self.condition:
                        self.live_workers -= 1
                    raise
                self.workers.append(worker)
            with self.condition:
                self.accepting = True
        except Exception:
            # Failed startup remains unavailable; lifespan still owns any started owner.
            self.accepting = False

    def admit(self, body, batch, proof, execution, deadline):
        if execution.remaining_seconds(self.clock) <= 0:
            return ApiFailureV1(failure="deadline_exceeded")
        with self.condition:
            if not self.accepting:
                return ApiFailureV1(failure="unavailable")
            if len(self.jobs) >= self.maximum:
                return ApiFailureV1(failure="queue_full")
            # A path name is reserved without filesystem I/O under the state lock.
            wrapper_id = uuid4().hex
            job = _Job(wrapper_id, body, batch, proof, execution, deadline,
                       self.output.path / ("RUN-" + uuid4().hex))
            self.jobs[wrapper_id] = job
            self.queue.append(job)
            self.admitted += 1
            self.condition.notify_all()
            return job

    def _retain_locked(self, job, receipt, phase):
        job.phase, job.terminal = phase, receipt
        self.terminal_facts.append(_Terminal(job.wrapper_id, receipt, phase))
        self.completed += 1
        self.jobs.pop(job.wrapper_id)
        job.proof, job.body = None, b""
        self.condition.notify_all()

    def cancel(self, job):
        job.cancellation.set()
        with self.condition:
            if job.phase == "queued":
                self.queue.remove(job)
                receipt = ApiWrapperNotStartedV1(wrapper_id=job.wrapper_id)
                self._retain_locked(job, receipt, "not_started")
            else:
                return job.terminal if job.terminal is not None else ApiWrapperPendingV1(wrapper_id=job.wrapper_id)
        job.future.set_result(receipt)
        return receipt

    def worker(self):
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.queue or self.closing)
                    if not self.queue:
                        return
                    job = self.queue.popleft()
                    job.phase = "running"
                try:
                    if job.cancellation.is_set() or job.execution.remaining_seconds(self.clock) <= 0:
                        receipt = ApiFailureV1(failure="deadline_exceeded")
                    else:
                        self.output.absent(job.output.name)
                        parameters = dict(dispatcher=self.dispatcher, proof_handle=job.proof, execution=job.execution,
                            publication_deadline=job.deadline, publication_reserve_seconds=self.reserve,
                            output_root=job.output, limits=self.limits, clock=self.clock)
                        receipt = (run_batch(job.body, cancellation=job.cancellation, **parameters) if job.batch
                                   else run_command(job.body, **parameters))
                except Exception:
                    receipt = ApiFailureV1(failure="runtime_error")
                with self.condition:
                    self._retain_locked(job, receipt, "completed")
                job.future.set_result(receipt)
        finally:
            with self.condition:
                self.live_workers -= 1
                last = self.live_workers == 0 and self.closing
                self.condition.notify_all()
            if last:
                self.output.close(); self.inventory.close()

    def shutdown(self):
        with self.condition:
            self.accepting, self.closing = False, True
            current = tuple(self.jobs.values())
            self.condition.notify_all()
        for job in current:
            self.cancel(job)
        started = finished = elapsed = overrun = host = None
        failed = False
        try:
            started, anchor = _sample(self.clock)
            cutoff, mono_cutoff = started + timedelta(seconds=self.shutdown_seconds), anchor + self.shutdown_seconds
            if self.dispatcher is not None:
                host = self.dispatcher.close(cutoff)
            else:
                failed = True
            while True:
                observed, mono = _sample(self.clock)
                remaining = max(0.0, min((cutoff - observed).total_seconds(), mono_cutoff - mono))
                with self.condition:
                    if not self.jobs or remaining <= 0:
                        break
                    self.condition.wait(remaining)
            finished, observed = _sample(self.clock)
            if observed < anchor or finished < started:
                raise ValueError("Invalid shutdown observation")
            elapsed = observed - anchor
            overrun = max(0.0, elapsed - self.shutdown_seconds, (finished - cutoff).total_seconds())
        except Exception:
            failed = True
        counts = self.snapshot()
        self.shutdown_receipt = ApiShutdownReceiptV1(admission_closed=True, **counts,
            host_shutdown=host, started_at=started, finished_at=finished, elapsed_seconds=elapsed,
            overrun_seconds=overrun, status="failed" if failed else (
                "closed" if host.owner_closed and not counts["pending_wrapper_ids"] else "pending"))
        if not self.workers:
            self.output.close(); self.inventory.close()


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON field")
        result[name] = value
    return result


def _document(body, limits):
    value = json.loads(body.decode("utf-8"), object_pairs_hook=_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    stack, nodes = [(value, 0)], 0
    while stack:
        item, depth = stack.pop(); nodes += 1
        if depth > limits.max_depth or nodes > limits.max_input_bytes:
            raise ValueError("Bounded JSON required")
        if type(item) in (list, dict):
            children = item.values() if type(item) is dict else item
            stack.extend((child, depth + 1) for child in children)
    return value


def _command_status(command):
    if command is None:
        return 408
    if command.inventory_status in ("partial", "unavailable") or command.outcome == "infrastructure_error":
        return 503
    if command.outcome == "started_pending":
        return 202
    if command.outcome == "expired":
        return 408
    if command.outcome in ("queue_full", "unavailable", "cancelled_before_start"):
        return 409
    if command.outcome == "denied":
        return 400 if command.failure == "invalid_command" else 403
    if command.result is not None:
        return {"authorized": 200, "denied": 403, "error": 503}[command.result.status]
    return 200


def _status(receipt):
    if type(receipt) is ApiFailureV1:
        return {"invalid_input": 400, "scope_denied": 403, "queue_full": 409, "unavailable": 409,
                "deadline_exceeded": 408, "runtime_error": 503, "publication_failed": 503}[receipt.failure]
    if type(receipt) is ApiWrapperPendingV1:
        return 202
    if type(receipt) is ApiWrapperNotStartedV1:
        return 409
    if receipt.input_outcome in ("invalid_command", "invalid_document"):
        return 400
    statuses = [200]
    if receipt.publication_status != "committed":
        statuses.append(503)
    if type(receipt) is CommandRunReceiptV1:
        statuses.append(_command_status(receipt.command))
        if receipt.unresolved_admission or receipt.export_outcome == "failed":
            statuses.append(503)
    else:
        if receipt.unresolved_admission_ordinals or receipt.outcome in ("runtime_error", "publication_failed"):
            statuses.append(503)
        if receipt.outcome == "deadline_exceeded":
            statuses.append(408)
        if receipt.pending_command_ids or receipt.outcome == "abandoned_pending":
            statuses.append(202)
        for position in receipt.positions:
            if position.command is not None:
                statuses.append(_command_status(position.command))
            if position.export_outcome == "failed" or position.execution_outcome == "runtime_error":
                statuses.append(503)
            elif position.execution_outcome == "deadline_exceeded":
                statuses.append(408)
            elif position.execution_outcome == "denied":
                statuses.append(403)
            elif position.execution_outcome == "invalid_request":
                statuses.append(400)
            elif position.execution_outcome == "not_started":
                statuses.append(409)
    ranks = {200: 0, 400: 1, 409: 2, 403: 3, 408: 4, 202: 5, 503: 6}
    return max(statuses, key=ranks.__getitem__)


def _response(receipt, status=None):
    return JSONResponse(receipt.model_dump(mode="json"), status_code=_status(receipt) if status is None else status)


async def _read(request, maximum, execution, clock):
    data = bytearray()
    while True:
        if execution.remaining_seconds(clock) <= 0:
            return ApiFailureV1(failure="deadline_exceeded")
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return ApiFailureV1(failure="unavailable")
        if message["type"] != "http.request" or type(message.get("body", b"")) is not bytes:
            return ApiFailureV1(failure="invalid_input")
        chunk = message.get("body", b"")
        before = len(data)
        data.extend(chunk[:maximum + 1 - before])
        if len(chunk) > maximum - before:
            return ApiFailureV1(failure="invalid_input")
        if not message.get("more_body", False):
            return bytes(data)


async def _disconnected(request):
    while True:
        if (await request.receive())["type"] == "http.disconnect":
            return


async def _await_job(request, lifecycle, job, remaining):
    result = asyncio.wrap_future(job.future)
    disconnect = asyncio.create_task(_disconnected(request))
    try:
        done, _ = await asyncio.wait((result, disconnect), timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
        if result in done:
            return result.result()
        return lifecycle.cancel(job)
    except asyncio.CancelledError:
        lifecycle.cancel(job)
        raise
    finally:
        disconnect.cancel()
        await asyncio.gather(disconnect, return_exceptions=True)
        # Do not cancel the Future representing actual running work.


def create_app(runtime_factory, auth_resolver, profile_registry, host_limits, *, release_id,
               clock, inventory_root, output_parent, interface_limits, transport_proof_resolver,
               total_seconds, export_reserve_seconds, shutdown_seconds,
               max_wrapper_jobs=8, max_wrapper_workers=2):
    output = inventory = None
    try:
        total, reserve, shutdown = map(_seconds, (total_seconds, export_reserve_seconds, shutdown_seconds))
        if (type(profile_registry) is not ProfileRegistry or type(host_limits) is not HostLimitsV1
                or type(interface_limits) is not InterfaceLimitsV1
                or not callable(getattr(runtime_factory, "create", None))
                or not callable(getattr(auth_resolver, "resolve", None)) or not callable(transport_proof_resolver)
                or not all(callable(getattr(clock, name, None)) for name in ("now", "monotonic"))
                or not 0 <= reserve < total or shutdown <= 0
                or total - reserve > host_limits.max_execution_seconds or shutdown > host_limits.shutdown_max_seconds
                or type(max_wrapper_jobs) is not int or not 1 <= max_wrapper_jobs <= 8
                or type(max_wrapper_workers) is not int or not 1 <= max_wrapper_workers <= min(2, max_wrapper_jobs)):
            raise ValueError
        host_limits = HostLimitsV1.model_validate(host_limits.model_dump())
        interface_limits = InterfaceLimitsV1.model_validate(interface_limits.model_dump())
        if any(type(getattr(host_limits, name)) not in (int, float) or not math.isfinite(getattr(host_limits, name))
               for name in HostLimitsV1.model_fields):
            raise ValueError
        registered = profile_registry.resolve(release_id)
        if getattr(clock, "mode", None) != registered.mode:
            raise ValueError
        output, inventory = _Parent(output_parent), _Parent(inventory_root)
    except Exception:
        if output is not None: output.close()
        if inventory is not None: inventory.close()
        raise ValueError("Invalid trusted API configuration") from None
    lifecycle = _Lifecycle(clock, interface_limits, reserve, shutdown, max_wrapper_jobs, max_wrapper_workers, output, inventory)

    @asynccontextmanager
    async def lifespan(app):
        lifecycle.start(runtime_factory, auth_resolver, profile_registry, host_limits, release_id)
        try:
            yield
        finally:
            lifecycle.shutdown()

    app = FastAPI(lifespan=lifespan, openapi_url=None, docs_url=None, redoc_url=None)
    app.state.api_lifecycle = lifecycle

    @app.middleware("http")
    async def ingress(request, call_next):
        try:
            now, mono = _sample(clock)
            execution = ExecutionContext(now + timedelta(seconds=total - reserve), now, mono, mono + (total - reserve))
            request.state.execution = execution
            request.state.publication_deadline = execution.deadline + timedelta(seconds=reserve)
        except Exception:
            return _response(ApiFailureV1(failure="unavailable"))
        return await call_next(request)

    async def route(request, *, batch=False, inspection=False):
        execution, deadline = request.state.execution, request.state.publication_deadline
        def respond(receipt, status=None):
            # An actual pending/not-started observation remains the bounded local
            # response when awaiting ends at D. New full common-receipt response
            # work must still enter within D; its eventual facts remain private.
            try:
                now, mono = _sample(clock)
                if (now < execution.captured_at or mono < execution.captured_monotonic
                        or now >= deadline or mono >= execution.monotonic_deadline + reserve):
                    if type(receipt) in (CommandRunReceiptV1, BatchRunReceiptV1):
                        return _response(ApiFailureV1(failure="deadline_exceeded"))
            except Exception:
                if type(receipt) in (CommandRunReceiptV1, BatchRunReceiptV1):
                    return _response(ApiFailureV1(failure="runtime_error"))
            return _response(receipt, status)
        try:
            if execution.remaining_seconds(clock) <= 0:
                return respond(ApiFailureV1(failure="deadline_exceeded"))
            headers = request.headers.getlist("x-proofkey-proof")
            if len(headers) != 1 or not headers[0] or len(headers[0].encode("utf-8")) > 256:
                raise ValueError
            proof = transport_proof_resolver(headers[0])
            if type(proof) is not TransportProofHandle:
                raise ValueError
            auth_resolver.resolve(proof, InspectProfileCommandV1(release_id=release_id))
        except Exception:
            return respond(ApiFailureV1(failure="scope_denied"), 401)
        try:
            if inspection:
                body = InspectProfileCommandV1(release_id=release_id).model_dump_json().encode()
            else:
                body = await _read(request, interface_limits.max_input_bytes if batch else min(
                    interface_limits.max_input_bytes, host_limits.max_command_bytes), execution, clock)
                if type(body) is not bytes:
                    return respond(body)
            value = _document(body, interface_limits)
            if batch:
                if type(value) is not list or len(value) > interface_limits.max_positions:
                    raise ValueError
            else:
                command = parse_command(body, max_bytes=min(interface_limits.max_input_bytes, host_limits.max_command_bytes))
                if command.release_id != release_id:
                    return respond(ApiFailureV1(failure="scope_denied"))
            if execution.remaining_seconds(clock) <= 0:
                return respond(ApiFailureV1(failure="deadline_exceeded"))
        except Exception:
            return respond(ApiFailureV1(failure="invalid_input"))
        job = None
        try:
            job = lifecycle.admit(body, batch, proof, execution, deadline)
            if type(job) is not _Job:
                return respond(job)
            now, mono = _sample(clock)
            remaining = max(0.0, min((deadline - now).total_seconds(), execution.monotonic_deadline + reserve - mono))
            receipt = await _await_job(request, lifecycle, job, remaining)
            return respond(receipt)
        except asyncio.CancelledError:
            if type(job) is _Job:
                lifecycle.cancel(job)
            raise
        except Exception:
            return respond(lifecycle.cancel(job) if type(job) is _Job else ApiFailureV1(failure="runtime_error"))

    @app.post("/v1/commands")
    async def commands(request: Request):
        return await route(request)

    @app.post("/v1/batch")
    async def batch_route(request: Request):
        return await route(request, batch=True)

    @app.get("/v1/profile")
    async def profile(request: Request):
        return await route(request, inspection=True)

    return app


def serve_loopback(app, *, host="127.0.0.1", port=8000):
    try:
        if type(host) is not str or not ipaddress.ip_address(host).is_loopback:
            raise ValueError
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError("Literal loopback host and valid port required") from None
    import uvicorn
    return uvicorn.run(app, host=host, port=port)
