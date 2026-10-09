"""Offline executable consuming the common public command library."""
import argparse
from datetime import timedelta
import json
import math
from pathlib import Path
import sys
from uuid import uuid4

from .batch import run_batch, run_command
from .bootstrap import CliConfiguration, CliReceiptV1, _PathPins, _default_configuration
from .clock import SyntheticReplayClock
from .contracts import CanonicalRequest, ScopedReply
from .execution import ExecutionContext
from .host import HostDispatcher
from .host_contracts import (BatchRunReceiptV1, InspectProfileCommandV1, RecoverCommandV1,
                             ReplyCommandV1, RunCommandV1, StopCommandV1, UnavailableCommandV1)


class _Usage(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _Usage("invalid_usage")

    def exit(self, status=0, message=None):
        raise _Usage("invalid_usage")


def _arguments(argv):
    parser = _Parser(add_help=False, allow_abbrev=False)
    parser.add_argument("--release", default="host-window-replay-v1")
    parser.add_argument("--credential-ref", default="synthetic-user")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    for name in ("run", "recover", "reply", "stop", "batch", "inspect-profile", "transfer"):
        child = commands.add_parser(name, add_help=False, allow_abbrev=False)
        child.add_argument("--release", default=argparse.SUPPRESS)
        child.add_argument("--credential-ref", default=argparse.SUPPRESS)
        if name in ("run", "reply", "batch"):
            child.add_argument("--input", required=True)
        if name in ("recover", "stop"):
            child.add_argument("--case-id", required=True)
        if name == "stop":
            child.add_argument("--generation", required=True)
    return parser.parse_args(argv)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_input")
        result[key] = value
    return result


def _input(args, configuration):
    name = args.command
    if name in ("run", "reply", "batch"):
        limit = configuration.interface_limits.max_input_bytes
        if name != "batch":
            limit = min(limit, configuration.host_limits.max_command_bytes)
        if args.input == "-":
            data = sys.stdin.buffer.read(limit + 1)
        else:
            with Path(args.input).open("rb") as stream:
                data = stream.read(limit + 1)
        if type(data) is not bytes or len(data) > limit:
            raise ValueError("invalid_input")
        if name == "batch":
            return data
        # Parse duplicate/nonfinite syntax before strict model validation; validate
        # JSON again to preserve schema-declared timestamps without Python coercion.
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid_input")))
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        model = CanonicalRequest if name == "run" else ScopedReply
        body = model.model_validate_json(encoded)
        return (RunCommandV1(release_id=args.release, request=body) if name == "run"
                else ReplyCommandV1(release_id=args.release, reply=body))
    model = {"recover": RecoverCommandV1, "stop": StopCommandV1,
             "inspect-profile": InspectProfileCommandV1, "transfer": UnavailableCommandV1}[name]
    fields = {"release_id": args.release}
    if name in ("recover", "stop"):
        fields["case_id"] = args.case_id
    if name == "stop":
        fields["generation"] = args.generation
    if name == "transfer":
        fields["tag"] = "transfer"
    return model(**fields)


def _command_exit(command):
    if command is None:
        return 3
    if command.inventory_status in ("partial", "unavailable"):
        return 4
    if command.outcome in ("infrastructure_error", "queue_full"):
        return 4
    if command.outcome in ("expired", "started_pending"):
        return 3
    if command.outcome in ("denied", "unavailable", "cancelled_before_start"):
        return 2
    if command.outcome == "inspection":
        return 0
    if command.result is not None:
        return {"authorized": 0, "denied": 2, "error": 4}[command.result.status]
    return 4


def _run_exit(run):
    if run.input_outcome in ("invalid_command", "invalid_document"):
        return 2
    if run.publication_status != "committed" or run.pending_command_ids:
        return 4 if run.publication_status != "committed" else 3
    if type(run) is BatchRunReceiptV1:
        codes = [0]
        if run.unresolved_admission_ordinals or run.outcome in ("runtime_error", "publication_failed"):
            codes.append(4)
        if run.outcome in ("deadline_exceeded", "abandoned_pending"):
            codes.append(3)
        for position in run.positions:
            if position.export_outcome == "failed" or position.execution_outcome == "runtime_error":
                codes.append(4)
            elif position.execution_outcome == "deadline_exceeded":
                codes.append(3)
            elif position.execution_outcome in ("invalid_request", "denied", "not_started"):
                codes.append(2)
            else:
                codes.append(_command_exit(position.command))
        return max(codes)
    if run.unresolved_admission or run.export_outcome == "failed":
        return 4
    return _command_exit(run.command)


def _emit(receipt, code):
    print(receipt.model_dump_json())
    return code


def main(argv=None, *, configuration=None):
    try:
        args = _arguments(argv)
    except (ValueError, TypeError):
        return _emit(CliReceiptV1(failure="invalid_usage"), 64)
    if configuration is not None and type(configuration) is not CliConfiguration:
        return _emit(CliReceiptV1(failure="invalid_configuration"), 4)
    holds, dispatcher, run, shutdown, failure, code = [], None, None, None, None, 4
    try:
        clock = configuration.clock if configuration is not None else SyntheticReplayClock()
        total = configuration.total_seconds if configuration is not None else 120.0
        reserve = configuration.publication_reserve_seconds if configuration is not None else 10.0
        execution = ExecutionContext.capture(clock.now() + timedelta(seconds=total - reserve), clock)
        publication_deadline = execution.deadline + timedelta(seconds=reserve)
        monotonic_deadline = execution.monotonic_deadline + reserve
        def boundary():
            now, observed = clock.now(), clock.monotonic()
            if (type(observed) not in (float, int) or not math.isfinite(observed)
                    or observed < execution.captured_monotonic or now < execution.captured_at
                    or now >= publication_deadline or observed >= monotonic_deadline):
                raise ValueError("bootstrap_unavailable")
        boundary()
        if configuration is None:
            configuration, holds = _default_configuration(clock, boundary=boundary)
        for index, parent in enumerate((configuration.output_parent, configuration.inventory_parent)):
            pins = _PathPins(parent)
            holds.append(pins)
            if tuple(item[3] for item in pins.entries) != configuration._parent_identities[index]:
                raise ValueError("bootstrap_unavailable")
        try:
            configuration.profile_registry.resolve(args.release)
            proof = configuration.auth_resolver.handle(args.credential_ref)
            boundary()
            command = _input(args, configuration)
        except Exception:
            boundary()
            failure, code = "invalid_input", 2
        if failure is None:
            boundary()
            for held in holds:
                held.check()
            inventory_root = configuration.inventory_parent / uuid4().hex
            output_root = configuration.output_parent / uuid4().hex
            dispatcher = HostDispatcher(configuration.factory, configuration.auth_resolver,
                configuration.profile_registry, clock, inventory_root, configuration.host_limits, release_id=args.release)
            parameters = dict(publication_deadline=publication_deadline, publication_reserve_seconds=reserve,
                output_root=output_root, limits=configuration.interface_limits, clock=clock)
            operation = run_batch if args.command == "batch" else run_command
            run = operation(command, dispatcher, proof, execution, **parameters)
            code = _run_exit(run)
    except Exception:
        failure, code = "bootstrap_unavailable", 4
    finally:
        if dispatcher is not None:
            try:
                shutdown = dispatcher.close(clock.now() + timedelta(seconds=configuration.shutdown_seconds))
                if not shutdown.owner_closed or shutdown.pending_command_ids:
                    failure, code = "owner_pending", 4
                elif shutdown.inventory_failure:
                    failure, code = "bootstrap_unavailable", 4
            except Exception:
                failure, code = "owner_pending", 4
        for held in reversed(holds):
            held.close()
    return _emit(CliReceiptV1(run=run, shutdown=shutdown, failure=failure), code)


if __name__ == "__main__":
    sys.exit(main())
