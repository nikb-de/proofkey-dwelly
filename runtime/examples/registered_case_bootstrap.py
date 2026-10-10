"""External trusted Python example. Explicit synthetic authority is not human approval."""
from contextlib import redirect_stdout
from datetime import timedelta
import io
import json
from proofkey.batch import run_command
from proofkey.bootstrap import CliReceiptV1
from proofkey.cli import main as cli_main
from proofkey.contracts import AuthContext, CanonicalRequest
from proofkey.execution import ExecutionContext
from proofkey.host import AuthResolver, HostDispatcher
from proofkey.host_admission import ProvisionedReviewResolverV1, SyntheticReviewGrantV1
from proofkey.host_contracts import HostLimitsV1, InterfaceLimitsV1
from proofkey.synthetic_provisioning import (
    SyntheticCaseReleaseSpecV1, prepare_synthetic_release, configure_registered_cli)


def context(clock, seconds=5):
    return ExecutionContext.capture(clock.now() + timedelta(seconds=seconds), clock)


def prepare_case(request_path, fixture_path, parent, clock):
    """Read the independent files once; preparation does not grant authority."""
    request = CanonicalRequest.model_validate_json(request_path.read_bytes())
    fixture = fixture_path.read_bytes()
    spec = SyntheticCaseReleaseSpecV1("J06-H", "J06-L", "J06-R", request, fixture)
    return prepare_synthetic_release(spec, parent=parent, clock=clock,
                                     execution=context(clock)), request


def execute_case(prepared, request, request_path, clock, surface, *, negative=None):
    """Explicit demo authorization, then ordinary installed library/CLI APIs.

    The optional negative selects finite acceptance denials only. Returned
    Python objects are private; only the public receipt is safe to serialize.
    """
    allowed = {None, "wrong-proof", "wrong-release", "omitted-release",
               "expired-review", "mismatched-review", "drifted-fixture"}
    if negative not in allowed or surface not in ("library", "cli"):
        raise ValueError("Unsupported example position")
    now = clock.now()
    issued = now - timedelta(seconds=2) if negative == "expired-review" else now
    expiry = now - timedelta(seconds=1) if negative == "expired-review" else now + timedelta(minutes=20)
    grant = SyntheticReviewGrantV1("j06-review",
        "0" * 64 if negative == "mismatched-review" else prepared.binding.artifact_hash,
        "j06-reviewer", "admit_fixed_local_replay", "synthetic_rehearsal", issued, expiry)
    resolver = AuthResolver({"j06-user": AuthContext(caller_id=request.principal_id,
        proof_reference="wrong-proof" if negative == "wrong-proof" else "j06-synthetic-proof")})
    configuration = configure_registered_cli(prepared,
        approvals=ProvisionedReviewResolverV1((grant,)), review_id="j06-review",
        auth_resolver=resolver, clock=clock, execution=context(clock),
        host_limits=HostLimitsV1(), interface_limits=InterfaceLimitsV1(),
        total_seconds=120.0, publication_reserve_seconds=10.0, shutdown_seconds=2.0)
    if surface == "cli":
        argv = ["run", "--input", str(request_path), "--credential-ref", "j06-user"]
        if negative != "omitted-release":
            argv += ["--release", "unknown-release" if negative == "wrong-release" else "J06-H"]
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli_main(argv, configuration=configuration)
        raw = output.getvalue()
        receipt = CliReceiptV1.model_validate_json(raw)
        for private in ("j06-synthetic-proof", "j06-reviewer", "j06-review",
                        "route-source-declaration-v1", str(prepared.root)):
            assert private not in raw, "public receipt disclosed private preparation"
        return {"code": code, "run": receipt.run, "shutdown": receipt.shutdown,
                "public": json.loads(raw)}
    execution = context(clock, 110)
    dispatcher = HostDispatcher(configuration.factory, resolver,
        configuration.profile_registry, clock, prepared.inventory_parent / "HOST-library",
        configuration.host_limits, release_id="J06-H",
        admission_composition=configuration.admission_composition)
    command_error = None
    try:
        run = run_command({"tag": "run", "release_id": "J06-H",
            "request": request.model_dump(mode="json")}, dispatcher, resolver.handle("j06-user"),
            execution, publication_deadline=execution.deadline + timedelta(seconds=10),
            publication_reserve_seconds=10.0, output_root=prepared.output_parent / "run",
            limits=configuration.interface_limits, clock=clock)
    except BaseException as error:
        command_error = error
        raise
    finally:
        try:
            shutdown = dispatcher.close(clock.now() + timedelta(seconds=2))
        except BaseException as close_error:
            if command_error is None:
                raise
            command_error._j06_shutdown = None
            command_error._j06_shutdown_error = close_error
        else:
            if command_error is not None:
                # Private application evidence; preserve the original exception
                # identity and traceback rather than replacing it with close state.
                command_error._j06_shutdown = shutdown
                command_error._j06_shutdown_error = None
    receipt = CliReceiptV1(run=run, shutdown=shutdown)
    return {"code": 0 if run.command.result is not None and
            run.command.result.status == "authorized" and shutdown.owner_closed else 2,
            "run": run, "shutdown": shutdown, "public": receipt.model_dump(mode="json")}
