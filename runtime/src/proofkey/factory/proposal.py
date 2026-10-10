"""Host-only adaptation evidence interfaces; no runtime registration API."""
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
import re

from ..contracts import (AdaptationProposal, EnvironmentProfile, AdaptationDiff,
                         MigrationPlan, ReviewPacket, HumanReviewApproval)
from ..identity import fingerprint, validate_json
from ..profiles import (validate_profile, load_profile, is_window_readiness_profile,
                        _window_readiness_profile_data, WINDOW_READINESS_FACTORY_KEY,
                        WINDOW_READINESS_IMPLEMENTATION_PATHS)

MAX_BYTES = 2 * 1024 * 1024
# Exact canonical reviewed flat-v1.3 supplement; hashes bind bytes, not origin.
REGISTERED_SUPPLEMENT_HASH = "5bb712b13efaace655ee7180f3d913d93cbd637e3d1685331c6a1eecbade7bf4"
REGISTERED_IMPLEMENTATIONS = (
    ("adapters/operator.py", "429ca2c36af43a80d0d9daac8c1ee0606cefaa02113d3e47b2b74fa71a46fe42"),
    ("adapters/world.py", "b790a73e81f59bc56ac7a422ea4ea9223ad572f23092fd6627a5466de74d8815"),
    ("verifier.py", "86e6e1c445d9a971ea8cb181558c0e677e286c89c1916966e0e6f72bd0e89a37"),
    ("packet_contracts.py", "16a3546c3405402a444f3532f4a2964a49e37e307871274f23684cb7e5a26e91"),
    ("process.py", "9aab2b58826fe6d23e4f54f4e3a39a67a46767f0e5f61321dd91555cf90b8d09"),
    ("profiles.py", "d65b6a383eb273c616429c2869fdea4309ae67103337a468943fc5a496645991"),
)


def canonical(value):
    validate_json(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise FactoryDenied("material_limit_exceeded")
    return encoded


def decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise FactoryDenied("invalid_material")
            value[key] = item
        return value
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise FactoryDenied("invalid_material")
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        canonical(value)
        return value
    except (ValueError, TypeError, UnicodeError):
        raise FactoryDenied("invalid_material") from None


def wire(model):
    return canonical(model.model_dump(mode="json"))


def _contract_inventory(profile):
    return tuple(sorted(
        [("capability:" + name + ":" + cap.version, wire(cap)) for name, cap in profile.capabilities.items()]
        + [("process:" + kind + ":" + spec.version, wire(spec)) for kind, spec in profile.processes.items()]))


def _affected(baseline, candidate):
    return sorted(["capability:" + name + ":" + cap.version for name, cap in baseline.capabilities.items()
                   if wire(cap) != wire(candidate.capabilities[name])]
                  + ["process:" + name + ":" + spec.version for name, spec in baseline.processes.items()
                     if wire(spec) != wire(candidate.processes[name])])


def _validate_candidate(baseline, candidate, supplement):
    # The only supplemental grant is the exact already reviewed v1.3 family.
    if candidate.policy_hash != baseline.policy_hash:
        raise FactoryDenied("changed_policy")
    if set(candidate.capabilities) != set(baseline.capabilities) or set(candidate.processes) != set(baseline.processes):
        raise FactoryDenied("permission_expansion")
    if set(supplement.capabilities) != set(baseline.capabilities):
        raise FactoryDenied("untrusted_supplement")
    expected_authorities = dict(baseline.authorities)
    expected_authorities.update({key: value for key, value in supplement.authorities.items()
                                 if key not in baseline.authorities})
    if candidate.authorities != expected_authorities or any(supplement.authorities.get(k) != v for k, v in baseline.authorities.items()):
        raise FactoryDenied("changed_authority")
    for name, old in baseline.capabilities.items():
        permitted = supplement.capabilities[name] if name == "enqueue_handoff" else old
        if wire(candidate.capabilities[name]) != wire(permitted):
            raise FactoryDenied("permission_expansion")
    for kind, old in baseline.processes.items():
        new = candidate.processes[kind]
        a, b = old.model_dump(mode="json"), new.model_dump(mode="json")
        for field in ("phases", "edges", "operations", "waits", "approvals", "acknowledgements", "readbacks", "completion"):
            if a[field] != b[field]:
                raise FactoryDenied("unsupported_process_change")
        if any(r not in new.prerequisites for r in old.prerequisites):
            raise FactoryDenied("weakened_readiness")
        for requirement in new.prerequisites:
            if requirement in old.prerequisites:
                continue
            key = requirement.authority + "." + requirement.fact
            operations = [edge.operation for edge in new.edges if edge.origin == requirement.phase]
            if (candidate.authorities.get(key) != requirement.authority or not any(
                    key in candidate.capabilities[op].conditional_coverage.covered_fields
                    for op in operations if op in candidate.capabilities)):
                raise FactoryDenied("unsupported_readiness")
        if a != b and (new.version == old.version or new.process_id == old.process_id):
            raise FactoryDenied("reused_process_identity")
    if candidate.release_hash != baseline.release_hash and candidate.profile_id == baseline.profile_id:
        raise FactoryDenied("reused_profile_identity")


def _material_proposal(material, implementation_registration=None, process_delta_registration=None):
    try:
        if implementation_registration is not None and process_delta_registration is not None:
            raise FactoryDenied("conflicting_implementation_registrations")
        if type(material) is not ProposalMaterial or type(material.adapter_sources) is not tuple:
            raise FactoryDenied("invalid_material")
        if process_delta_registration is not None:
            process_delta_registration = _normalize_window_registration(process_delta_registration)
            _window_sources(material.adapter_sources)
        baseline = validate_profile(EnvironmentProfile.model_validate(decode(material.baseline)))
        candidate = validate_profile(EnvironmentProfile.model_validate(decode(material.candidate)))
        supplement = validate_profile(EnvironmentProfile.model_validate(decode(material.reviewed_supplement)))
        if supplement.version != "v1.3" or supplement.release_hash != REGISTERED_SUPPLEMENT_HASH:
            raise FactoryDenied("untrusted_supplement")
        if process_delta_registration is None:
            _validate_candidate(baseline, candidate, supplement)
        elif (baseline.release_hash != process_delta_registration.baseline_hash or
                not is_window_readiness_profile(candidate) or
                candidate.release_hash != process_delta_registration.candidate_hash or
                candidate.process_hash != process_delta_registration.process_hash or
                candidate.policy_hash != process_delta_registration.policy_hash):
            raise FactoryDenied("unsupported_candidate")
        source, tests, agent = decode(material.source), decode(material.tests), decode(material.agent)
        if not all(type(item) is dict for item in (source, tests, agent)):
            raise FactoryDenied("invalid_material")
        if agent.get("mode") != "synthetic":
            raise FactoryDenied("agent_execution_unestablished")
        diffs = sorted([AdaptationDiff.model_validate(item) for item in decode(material.diff)], key=lambda item: item.path)
        if len(diffs) > 64 or len({diff.path for diff in diffs}) != len(diffs):
            raise FactoryDenied("invalid_diff")
        before, after = baseline.model_dump(mode="json"), candidate.model_dump(mode="json")
        # Complete top-level changes are review material. A truthful leaf cannot
        # stand in for omitted changed siblings under the same semantic field.
        # Only profile release identity and derived hash metadata are excluded;
        # process identities/versions and all their semantics remain in processes.
        semantic_changes = {key for key in before if key not in {"profile_id", "version", "release_hash", "process_hash"}
                            and canonical(before[key]) != canonical(after[key])}
        if {diff.path for diff in diffs} != semantic_changes:
            raise FactoryDenied("incomplete_diff")
        for diff in diffs:
            if (canonical(diff.before) != canonical(before[diff.path]) or
                    canonical(diff.after) != canonical(after[diff.path])):
                raise FactoryDenied("diff_mismatch")
        migration = MigrationPlan.model_validate(decode(material.migration))
        affected = _affected(baseline, candidate)
        if sorted(migration.affected_contracts) != affected or len(set(migration.affected_contracts)) != len(affected):
            raise FactoryDenied("affected_contract_inventory_mismatch")
        migration = MigrationPlan(strategy=migration.strategy, affected_contracts=affected)
        adapters = []
        source_bytes = 0
        for pair in material.adapter_sources:
            if type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str or type(pair[1]) is not bytes:
                raise FactoryDenied("invalid_adapter_sources")
            if implementation_registration is not None:
                source_bytes += len(pair[1])
                if len(pair[1]) > MAX_BYTES or source_bytes > 6 * MAX_BYTES:
                    raise FactoryDenied("material_limit_exceeded")
            adapters.append({"path": pair[0], "sha256": sha256(pair[1]).hexdigest()})
        if not adapters or len({entry["path"] for entry in adapters}) != len(adapters):
            raise FactoryDenied("invalid_adapter_sources" if implementation_registration is None
                                else "unsupported_adapter_implementation")
        pins = (process_delta_registration.implementations if process_delta_registration is not None
                else REGISTERED_IMPLEMENTATIONS if implementation_registration is None
                else implementation_registration.implementations)
        if {entry["path"]: entry["sha256"] for entry in adapters} != dict(pins):
            raise FactoryDenied("unsupported_adapter_implementation")
        required = tests.get("required_cases")
        if (type(required) is not list or not required or len(required) > 128 or
                any(type(case) is not str or not case for case in required) or len(required) != len(set(required))):
            raise FactoryDenied("invalid_test_suite")
        body = dict(domain="proofkey-adaptation-proposal-v1", proposal_id=material.proposal_id,
            source_hash=fingerprint(source), baseline_hash=baseline.release_hash, candidate_hash=candidate.release_hash,
            diff=[item.model_dump(mode="json") for item in diffs], test_hash=fingerprint(tests),
            migration=migration.model_dump(mode="json"), agent_hash=fingerprint(agent),
            adapter_sources=sorted(adapters, key=lambda item: item["path"]),
            policy_hash=candidate.policy_hash, process_hash=candidate.process_hash,
            original_contracts=[{"id": name, "sha256": sha256(raw).hexdigest()} for name, raw in _contract_inventory(baseline)],
            supplement_hash=supplement.release_hash)
        if implementation_registration is not None:
            registered_pins = [{"path": path, "sha256": digest} for path, digest in
                               sorted(implementation_registration.implementations)]
            body["implementation_registration"] = {
                "registration_id": implementation_registration.registration_id,
                "provenance": implementation_registration.provenance,
                "inventory_sha256": sha256(canonical(registered_pins)).hexdigest(),
            }
        if process_delta_registration is not None:
            body["process_delta_registration"] = _window_registration_commitment(process_delta_registration)
        proposal = AdaptationProposal(**{key: body[key] for key in (
            "proposal_id", "source_hash", "baseline_hash", "diff", "test_hash", "migration", "agent_hash")},
            proposal_hash=fingerprint(body))
        return proposal, candidate, baseline, body
    except FactoryDenied:
        raise
    except (ValueError, TypeError, KeyError, AttributeError):
        raise FactoryDenied("unsupported_candidate") from None


class FactoryDenied(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class ProposalMaterial:
    proposal_id: str
    source: bytes
    baseline: bytes
    candidate: bytes
    tests: bytes
    agent: bytes
    diff: bytes
    migration: bytes
    adapter_sources: tuple[tuple[str, bytes], ...]
    reviewed_supplement: bytes


@dataclass(frozen=True)
class RegressionEvidence:
    receipt: bytes


@dataclass(frozen=True)
class RunnerIdentity:
    runner_id: str
    provenance: str
    suite_hash: str


@dataclass(frozen=True)
class HumanReviewEvent:
    proof_reference: str
    approval: bytes
    actor_type: str
    provenance: str


@dataclass(frozen=True)
class OriginalInventory:
    inventory_id: str
    scope: str
    baseline_hash: str
    pending: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class SyntheticImplementationRegistration:
    registration_id: str
    provenance: str
    implementations: tuple[tuple[str, str], ...]


def _normalize_registration(registration):
    if registration is None:
        return None
    if (type(registration) is not SyntheticImplementationRegistration or
            type(registration.registration_id) is not str or
            re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", registration.registration_id) is None or
            type(registration.provenance) is not str or
            registration.provenance != "local_controlled_synthetic" or
            type(registration.implementations) is not tuple or len(registration.implementations) != 6):
        raise FactoryDenied("invalid_implementation_registration")
    pins = []
    for pair in registration.implementations:
        if (type(pair) is not tuple or len(pair) != 2 or
                type(pair[0]) is not str or type(pair[1]) is not str or
                re.fullmatch(r"[0-9a-f]{64}", pair[1]) is None):
            raise FactoryDenied("invalid_implementation_registration")
        pins.append((pair[0], pair[1]))
    if {path for path, _ in pins} != {path for path, _ in REGISTERED_IMPLEMENTATIONS}:
        raise FactoryDenied("invalid_implementation_registration")
    return SyntheticImplementationRegistration(registration.registration_id, registration.provenance,
                                               tuple(sorted(pins)))


@dataclass(frozen=True, slots=True)
class WindowReadinessRegistrationV1:
    registration_id: str
    provenance: str
    host_factory_key: str
    baseline_hash: str
    candidate_hash: str
    process_hash: str
    policy_hash: str
    implementations: tuple[tuple[str, str], ...]


def _normalize_window_registration(registration):
    if registration is None:
        return None
    if type(registration) is not WindowReadinessRegistrationV1:
        raise FactoryDenied("invalid_process_delta_registration")
    expected = _window_readiness_profile_data(load_profile("flat-v1.3"))
    fields = dict(
        registration_id="synthetic-window-readiness-delta-v1",
        provenance="local_controlled_synthetic",
        host_factory_key=WINDOW_READINESS_FACTORY_KEY,
        baseline_hash=REGISTERED_SUPPLEMENT_HASH, candidate_hash=expected["release_hash"],
        process_hash=expected["process_hash"], policy_hash=expected["policy_hash"])
    if any(type(getattr(registration, key, None)) is not str or getattr(registration, key) != value
           for key, value in fields.items()):
        raise FactoryDenied("invalid_process_delta_registration")
    pins = getattr(registration, "implementations", None)
    if type(pins) is not tuple or len(pins) != len(WINDOW_READINESS_IMPLEMENTATION_PATHS):
        raise FactoryDenied("invalid_process_delta_registration")
    detached = []
    for pair, path in zip(pins, WINDOW_READINESS_IMPLEMENTATION_PATHS):
        if (type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str or
                pair[0] != path or type(pair[1]) is not str or
                re.fullmatch("[0-9a-f]{64}", pair[1]) is None):
            raise FactoryDenied("invalid_process_delta_registration")
        detached.append((pair[0], pair[1]))
    return WindowReadinessRegistrationV1(**fields, implementations=tuple(detached))


def _window_sources(sources):
    """Bound and detach source bytes before interpreting any JSON material."""
    if type(sources) is not tuple:
        raise FactoryDenied("invalid_adapter_sources")
    detached, total = [], 0
    for pair in sources:
        if (type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str or
                type(pair[1]) is not bytes or not pair[1]):
            raise FactoryDenied("invalid_adapter_sources")
        total += len(pair[1])
        if len(pair[1]) > 1048576 or total > 8388608:
            raise FactoryDenied("material_limit_exceeded")
        detached.append((pair[0], pair[1]))
    if tuple(path for path, _ in detached) != WINDOW_READINESS_IMPLEMENTATION_PATHS:
        raise FactoryDenied("unsupported_adapter_implementation")
    return tuple(detached)


def _window_registration_commitment(registration):
    inventory = [{"path": path, "sha256": digest} for path, digest in registration.implementations]
    body = {name: getattr(registration, name) for name in (
        "registration_id", "provenance", "host_factory_key", "baseline_hash",
        "candidate_hash", "process_hash", "policy_hash")}
    body["inventory_sha256"] = sha256(canonical(inventory)).hexdigest()
    body["registration_sha256"] = sha256(canonical(body)).hexdigest()
    return body


@dataclass(frozen=True)
class FactoryContext:
    materials: tuple[ProposalMaterial, ...]
    regressions: tuple[RegressionEvidence, ...]
    runners: tuple[RunnerIdentity, ...]
    reviews: tuple[HumanReviewEvent, ...]
    inventory: OriginalInventory | None
    now: datetime
    implementation_registration: SyntheticImplementationRegistration | None = None
    process_delta_registration: WindowReadinessRegistrationV1 | None = None


class AdaptationFactory:
    __slots__ = ("_context",)

    def __init__(self, context):
        if type(context) is not FactoryContext or any(type(getattr(context, field)) is not tuple for field in
                ("materials", "regressions", "runners", "reviews")):
            raise FactoryDenied("trusted_context_unavailable")
        if context.implementation_registration is not None and context.process_delta_registration is not None:
            raise FactoryDenied("conflicting_implementation_registrations")
        if (type(context.now) is not datetime or context.now.tzinfo is None or len(context.materials) > 32 or
                len(context.regressions) > 128 or len(context.reviews) > 128 or len(context.runners) > 128):
            raise FactoryDenied("invalid_context")
        registration = _normalize_registration(context.implementation_registration)
        window_registration = _normalize_window_registration(context.process_delta_registration)
        if any(type(runner) is not RunnerIdentity or any(type(getattr(runner, name)) is not str for name in
               ("runner_id", "provenance", "suite_hash")) for runner in context.runners):
            raise FactoryDenied("runner_untrusted")
        inventory = context.inventory
        if inventory is not None:
            if (type(inventory) is not OriginalInventory or type(inventory.pending) is not tuple or
                    any(type(raw) is not bytes for raw in inventory.pending) or len(inventory.pending) > 128 or
                    any(type(getattr(inventory, name)) is not str for name in ("inventory_id", "scope", "baseline_hash"))):
                raise FactoryDenied("pending_inventory_unavailable")
            inventory = replace(inventory, pending=tuple(canonical(decode(raw)) for raw in inventory.pending))
        materials = []
        for material in context.materials:
            if type(material) is not ProposalMaterial:
                raise FactoryDenied("invalid_material")
            if window_registration is not None:
                material = replace(material, adapter_sources=_window_sources(material.adapter_sources))
            normalized = replace(material, **{field: canonical(decode(getattr(material, field))) for field in
                ("source", "baseline", "candidate", "tests", "agent", "diff", "migration", "reviewed_supplement")})
            _material_proposal(normalized, registration, window_registration)
            materials.append(normalized)
        if len({material.proposal_id for material in materials}) != len(materials):
            raise FactoryDenied("duplicate_registration")
        regressions = tuple(RegressionEvidence(canonical(decode(item.receipt))) for item in context.regressions
                            if type(item) is RegressionEvidence)
        if len(regressions) != len(context.regressions) or any(type(decode(item.receipt)) is not dict for item in regressions):
            raise FactoryDenied("invalid_regression")
        reviews = tuple(replace(event, approval=canonical(decode(event.approval))) for event in context.reviews
                        if type(event) is HumanReviewEvent)
        if len(reviews) != len(context.reviews):
            raise FactoryDenied("approval_untrusted")
        self._context = replace(context, materials=tuple(materials), regressions=regressions, reviews=reviews,
                                inventory=inventory, implementation_registration=registration,
                                process_delta_registration=window_registration)

    @property
    def context(self):
        return self._context

    def _resolve(self, proposal):
        if type(proposal) is not AdaptationProposal:
            raise FactoryDenied("proposal_mismatch")
        for material in self.context.materials:
            expected, candidate, baseline, body = _material_proposal(
                material, self.context.implementation_registration, self.context.process_delta_registration)
            if expected.proposal_hash == proposal.proposal_hash:
                if wire(expected) != wire(proposal):
                    raise FactoryDenied("proposal_mismatch")
                return material, expected, candidate, baseline, body
        raise FactoryDenied("proposal_unregistered")

    def _proposal_hash(self, proposal_hash):
        for material in self.context.materials:
            proposal, _, _, _ = _material_proposal(
                material, self.context.implementation_registration, self.context.process_delta_registration)
            if proposal.proposal_hash == proposal_hash:
                return proposal
        raise FactoryDenied("proposal_unregistered")

    def prepare_proposal(self, packet, baseline, agent_receipt):
        try:
            source, agent = canonical(decode(packet)), canonical(decode(agent_receipt))
            baseline_bytes = wire(validate_profile(baseline))
            matches = [material for material in self.context.materials
                if canonical(decode(material.source)) == source and canonical(decode(material.agent)) == agent
                and canonical(decode(material.baseline)) == baseline_bytes]
            if len(matches) != 1:
                raise FactoryDenied("proposal_material_unregistered")
            return _material_proposal(matches[0], self.context.implementation_registration,
                                      self.context.process_delta_registration)[0]
        except FactoryDenied:
            raise
        except (ValueError, TypeError, AttributeError):
            raise FactoryDenied("invalid_material") from None

    def check_proposal(self, proposal, regression_receipt):
        material, exact, candidate, baseline, _ = self._resolve(proposal)
        matching = [decode(item.receipt) for item in self.context.regressions
                    if type(item) is RegressionEvidence and fingerprint(decode(item.receipt)) == regression_receipt]
        if len(matching) != 1:
            raise FactoryDenied("regression_unregistered")
        evidence = matching[0]
        required_fields = {"proposal_hash", "candidate_hash", "baseline_hash", "test_hash", "runner_id",
                           "provenance", "execution_id", "executed_at", "result", "cases"}
        if set(evidence) != required_fields:
            raise FactoryDenied("invalid_regression")
        bindings = dict(proposal_hash=exact.proposal_hash, candidate_hash=candidate.release_hash,
                        baseline_hash=baseline.release_hash, test_hash=exact.test_hash)
        if any(evidence[key] != expected for key, expected in bindings.items()):
            raise FactoryDenied("regression_binding_mismatch")
        runners = [runner for runner in self.context.runners if type(runner) is RunnerIdentity and
                   runner.runner_id == evidence["runner_id"] and runner.suite_hash == exact.test_hash
                   and runner.provenance == evidence["provenance"] == "local_controlled_synthetic"]
        if len(runners) != 1:
            raise FactoryDenied("runner_untrusted")
        if evidence["result"] == "failed":
            raise FactoryDenied("failed_regression")
        if evidence["result"] != "passed":
            raise FactoryDenied("regression_unavailable")
        # Preserve the legacy denial order; only the registered delta continues.
        if self.context.process_delta_registration is None and any(
                spec.version != "v1" for spec in candidate.processes.values()):
            raise FactoryDenied("regression_unavailable")
        try:
            time = datetime.fromisoformat(evidence["executed_at"])
            if not evidence["execution_id"] or time.tzinfo is None or time > self.context.now:
                raise FactoryDenied("regression_provenance_mismatch")
            required = set(decode(material.tests)["required_cases"])
            cases = evidence["cases"]
            if (type(cases) is not list or len(cases) != len(required) or
                    {case["case_id"] for case in cases} != required or any(
                    set(case) != {"case_id", "result", "output_hash"} or case["result"] != "passed" or
                    type(case["output_hash"]) is not str or len(case["output_hash"]) != 64 or
                    any(ch not in "0123456789abcdef" for ch in case["output_hash"]) for case in cases)):
                raise FactoryDenied("regression_coverage_incomplete")
        except (ValueError, TypeError, KeyError):
            raise FactoryDenied("invalid_regression") from None
        # Only the exact retained J05 semantic registration admits its sole v2 process.
        if any(spec.version != "v1" for spec in candidate.processes.values()):
            if self.context.process_delta_registration is None or not is_window_readiness_profile(candidate):
                raise FactoryDenied("regression_unavailable")
        return ReviewPacket(proposal_hash=exact.proposal_hash, regression_hash=regression_receipt,
            affected_pending_contracts=exact.migration.affected_contracts, proposed_profile=candidate,
            proposed_processes=candidate.processes, compatibility=exact.migration)

    def release_profile(self, review_packet, human_approval, pending_intents):
        from .release import stage_release
        return stage_release(self, review_packet, human_approval, pending_intents)


def prepare_proposal(packet, baseline, agent_receipt):
    raise FactoryDenied("trusted_context_unavailable")


def check_proposal(proposal, regression_receipt):
    raise FactoryDenied("trusted_context_unavailable")
