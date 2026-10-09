"""Position-preserving pilot coverage and observed offline grader variability.

Captured callbacks establish local runner behavior only. Provisional references
and absent independent human custody keep every result unqualified.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import random
from proofkey.contracts import FrozenDict, QualificationReceipt
from proofkey.identity import fingerprint
from .contracts import (AssessmentPosition, CaseRow, ExecutionPosition, GraderDescriptor, MAX_POSITIONS, Observation,
                        Reference, canonical_bytes, digest_bytes, require_hash, strict_loads)
from .labels import score_case
from .ledger import LedgerInspection


@dataclass(frozen=True)
class CoverageReport:
    total_positions: int
    included_positions: int
    ambiguous_positions: int
    excluded_positions: int
    errors: int
    missing_outputs: int
    independent_groups: int
    positive_families: FrozenDict
    positions: tuple[AssessmentPosition, ...]


def summarize_coverage(ledger, positions):
    if not isinstance(ledger, LedgerInspection):
        raise TypeError("Typed ledger inspection required")
    supplied = tuple(positions)
    if len(supplied) > MAX_POSITIONS:
        raise ValueError("Assessment positions exceed bound")
    by_ordinal = {}
    for position in supplied:
        if not isinstance(position, AssessmentPosition):
            raise TypeError("Typed ordinal assessment required")
        if position.ordinal in by_ordinal or position.ordinal >= len(ledger.positions):
            raise ValueError("Assessment position join mismatch")
        row = ledger.positions[position.ordinal].row
        if position.assessment is not None:
            if row is None or position.assessment.case_id != row.case_id:
                raise ValueError("Assessment case join mismatch")
            for name, value in row.reference.sources().items():
                if getattr(position.assessment, name) != value:
                    raise ValueError("Assessment reference join mismatch")
        by_ordinal[position.ordinal] = position
    joined = tuple(by_ordinal.get(p.ordinal, AssessmentPosition(p.ordinal)) for p in ledger.positions)
    families = {"rescheduling": False, "whole_order_return": False}
    for family in families:
        positives = [(p, joined[p.ordinal]) for p in ledger.positions if p.row is not None
                     and p.row.source.get("family") == family and p.row.control == "positive"
                     and p.row.reference.exclusion is None]
        families[family] = bool(positives) and all(
            position.status == "valid" and assessment.error is None and assessment.assessment is not None
            and all(v.verdict == "correct" for v in assessment.assessment.effect_verdicts.values())
            and set(position.row.reference.required_behavior) <= set(assessment.assessment.effect_verdicts)
            for position, assessment in positives)
    return CoverageReport(ledger.audit.total_cases, ledger.audit.included_cases,
        ledger.audit.ambiguous_cases, ledger.audit.excluded_cases, sum(p.error is not None for p in joined),
        sum(p.assessment is None for p in joined), len(ledger.independent_groups), FrozenDict(families), joined)


@dataclass(frozen=True)
class Judgment:
    observation: Observation
    output_hash: str
    order: tuple[str, ...]
    repetition: int
    verdict: str
    score: float | None
    response_bytes: bytes | None
    error: bytes | None

    def __post_init__(self):
        if not isinstance(self.observation, Observation) or self.output_hash != self.observation.output_hash:
            raise ValueError("Exact captured judgment output required")
        if type(self.order) is not tuple or any(type(item) is not str for item in self.order):
            raise ValueError("Immutable presentation order required")
        if type(self.repetition) is not int or not 0 <= self.repetition < 16 or self.verdict not in {"correct", "incorrect", "abstain", "error"}:
            raise ValueError("Bounded observed grader verdict required")
        if self.score is not None and (type(self.score) is not float or not math.isfinite(self.score) or not 0 <= self.score <= 1):
            raise ValueError("Finite observed grader score required")
        for raw in (self.response_bytes, self.error):
            if raw is not None:
                digest_bytes(raw)


@dataclass(frozen=True)
class JudgmentBatch:
    grader_bytes: bytes
    judgments: tuple[Judgment, ...]
    seed: int
    captured_at: datetime
    case_ids: tuple[str, ...] = ()
    repetitions: int | None = None

    def __post_init__(self):
        GraderDescriptor.model_validate(strict_loads(self.grader_bytes))
        if type(self.judgments) is not tuple or not self.judgments or len(self.judgments) > MAX_POSITIONS or any(not isinstance(j, Judgment) for j in self.judgments):
            raise ValueError("Immutable bounded captured judgments required")
        if type(self.seed) is not int or not isinstance(self.captured_at, datetime) or self.captured_at.utcoffset() is None:
            raise ValueError("Presentation seed and aware capture time required")
        if (type(self.case_ids) is not tuple or len(self.case_ids) > MAX_POSITIONS
                or any(type(case) is not str or not case for case in self.case_ids)
                or len(set(self.case_ids)) != len(self.case_ids)
                or self.repetitions is not None and (type(self.repetitions) is not int
                    or not 2 <= self.repetitions <= 16 or len(self.case_ids) * self.repetitions > MAX_POSITIONS)):
            raise ValueError("Bounded declared grading inventory required")

    @property
    def grader_hash(self):
        return digest_bytes(self.grader_bytes)


@dataclass(frozen=True)
class ExecutionBatch:
    candidate_hash: str
    executions: tuple[Observation, ...]
    captured_at: datetime
    positions: tuple[ExecutionPosition, ...] = ()

    def __post_init__(self):
        require_hash(self.candidate_hash)
        if (type(self.executions) is not tuple or not self.executions or len(self.executions) > MAX_POSITIONS
                or any(not isinstance(o, Observation) or o.candidate_hash != self.candidate_hash for o in self.executions)):
            raise ValueError("Bounded captured unchanged executions required")
        if (type(self.positions) is not tuple or self.positions and
                (len(self.positions) != len(self.executions) or any(not isinstance(p, ExecutionPosition)
                    or p.ordinal != i or p.observation != self.executions[i] for i, p in enumerate(self.positions)))):
            raise ValueError("Execution position inventory mismatch")


@dataclass(frozen=True)
class ControlEvidence:
    """A captured runner batch for a declared control, never an approval flag."""
    kind: str
    batch: JudgmentBatch | ExecutionBatch | None
    references: tuple[bytes, ...] = ()
    execution_batch: ExecutionBatch | None = None
    grading_repetitions: int | None = None

    def __post_init__(self):
        if self.kind not in {"known_good", "known_bad", "disabled", "improved", "independent_execution"} or self.batch is not None and not isinstance(self.batch, (JudgmentBatch, ExecutionBatch)):
            raise ValueError("Captured declared control required")
        if self.kind != "independent_execution" and self.batch is not None and not isinstance(self.batch, JudgmentBatch):
            raise ValueError("Sensitivity control requires grader observations")
        if self.batch is None and self.execution_batch is None:
            raise ValueError("Control must retain captured execution evidence")
        if type(self.references) is not tuple:
            raise ValueError("Immutable reference identities required")
        for raw in self.references:
            Reference.model_validate(strict_loads(raw))
        if self.execution_batch is not None and not isinstance(self.execution_batch, ExecutionBatch):
            raise TypeError("Captured control execution batch required")
        if self.grading_repetitions is not None and (type(self.grading_repetitions) is not int or not 2 <= self.grading_repetitions <= 16):
            raise ValueError("Bounded declared control repetitions required")


@dataclass(frozen=True)
class JudgmentEvidence:
    """Every captured batch, with missing positions kept explicit, not averaged away."""
    kind: str
    batch: JudgmentBatch | None
    expected_cases: tuple[str, ...]
    expected_repetitions: int | None
    limits: tuple[str, ...]

    def __post_init__(self):
        if (self.kind not in {"primary", "known_good", "known_bad", "disabled", "improved", "independent_execution"}
                or self.batch is not None and not isinstance(self.batch, JudgmentBatch)
                or type(self.expected_cases) is not tuple or not self.expected_cases
                or len(self.expected_cases) > MAX_POSITIONS or len(set(self.expected_cases)) != len(self.expected_cases)
                or any(type(case) is not str or not case for case in self.expected_cases)
                or type(self.limits) is not tuple or any(type(limit) is not str for limit in self.limits)
                or self.expected_repetitions is not None and (type(self.expected_repetitions) is not int
                    or not 2 <= self.expected_repetitions <= 16
                    or len(self.expected_cases) * self.expected_repetitions > MAX_POSITIONS)):
            raise ValueError("Closed bounded judgment evidence required")

    @property
    def denominator(self):
        return 0 if self.batch is None else len(self.batch.judgments)

    @property
    def expected_positions(self):
        return None if self.expected_repetitions is None else len(self.expected_cases) * self.expected_repetitions

    @property
    def missing_scores(self):
        return 0 if self.batch is None else sum(j.score is None for j in self.batch.judgments)

    @property
    def errors(self):
        return 0 if self.batch is None else sum(j.verdict == "error" or j.error is not None for j in self.batch.judgments)

    @property
    def abstentions(self):
        return 0 if self.batch is None else sum(j.verdict == "abstain" for j in self.batch.judgments)


def _judgment_evidence(kind, batch, expected_cases, declared_repetitions=None):
    limits = []
    if batch is None:
        return JudgmentEvidence(kind, None, expected_cases, declared_repetitions, ("grading_batch_missing",))
    repetitions = batch.repetitions
    if not batch.case_ids or repetitions is None:
        limits.append("declared_grading_inventory_missing")
    if declared_repetitions is not None and repetitions != declared_repetitions:
        limits.append("declared_grading_repetition_mismatch")
    if batch.case_ids and set(batch.case_ids) != set(expected_cases):
        limits.append("grading_case_inventory_mismatch")
    by_case = {}
    for j in batch.judgments:
        if j.output_hash != digest_bytes(j.observation.output_bytes):
            raise ValueError("Judgment exact output join mismatch")
        by_case.setdefault(j.observation.case_id, []).append(j)
    if set(by_case) != set(expected_cases):
        limits.append("grading_case_inventory_mismatch")
    for case in expected_cases:
        items = by_case.get(case, [])
        if (repetitions is None or len(items) != repetitions
                or {j.repetition for j in items} != set(range(repetitions))):
            limits.append("grading_repetition_inventory_incomplete")
        if len({j.order for j in items}) < 2:
            limits.append("grading_presentation_order_incomplete")
        if len({j.output_hash for j in items}) != 1:
            limits.append("grading_output_changed")
    if any(j.verdict in {"error", "abstain"} or j.error is not None or j.score is None for j in batch.judgments):
        limits.append("grading_error_abstention_or_missing_score")
    return JudgmentEvidence(kind, batch, expected_cases, repetitions, tuple(dict.fromkeys(limits)))


@dataclass(frozen=True)
class QualificationSummary:
    receipt: QualificationReceipt
    judgments: tuple[Judgment, ...]
    independent_groups: int
    verdict_flips: int
    score_spread: float | None
    abstentions: int
    errors: int
    execution_disagreements: int | None
    paired_group_effects: tuple[tuple[str, float], ...]
    uncertainty: str
    judgment_evidence: tuple[JudgmentEvidence, ...]


def capture_judgments(observations, *, grader_descriptor, runner, repeats, seed):
    observations = tuple(observations)
    if (not observations or len(observations) > MAX_POSITIONS or type(repeats) is not int
            or not 2 <= repeats <= 16 or len(observations) * repeats > MAX_POSITIONS or type(seed) is not int):
        raise ValueError("Bounded repeated independent observations required")
    if not callable(runner) or any(not isinstance(o, Observation) or o.output_bytes is None for o in observations):
        raise TypeError("Observed exact outputs and host runner required")
    if len({o.case_id for o in observations}) != len(observations):
        raise ValueError("Distinct judgment case identities required")
    try:
        descriptor = GraderDescriptor.model_validate(grader_descriptor)
    except (TypeError, ValueError):
        raise ValueError("Invalid closed grader descriptor") from None
    grader_bytes = canonical_bytes(descriptor.model_dump(mode="json"))
    order = [o.case_id for o in observations]
    random.Random(seed).shuffle(order)
    # With one case, the two presentation sides still swap explicitly.
    presentations = (tuple(order + ["reference", "observed"]), tuple(reversed(order + ["reference", "observed"])))
    judgments = []
    for repetition in range(repeats):
        presentation = presentations[repetition % 2]
        for observation in observations:
            verdict, score, response, error = "error", None, None, None
            try:
                response = canonical_bytes(runner(observation.output_bytes, presentation))
                data = strict_loads(response)
                if not isinstance(data, dict) or set(data) != {"verdict", "score"} or data["verdict"] not in {"correct", "incorrect", "abstain"}:
                    raise ValueError("Invalid grader response")
                score = data["score"]
                if score is not None and (type(score) not in {int, float} or not math.isfinite(score) or not 0 <= score <= 1):
                    raise ValueError("Invalid grader score")
                if data["verdict"] == "abstain" and score is not None:
                    raise ValueError("Abstention score unavailable")
                verdict = data["verdict"]
            except Exception as exc:
                error = (type(exc).__name__ + ":" + str(exc)).encode("utf-8")[:1_048_576]
                verdict, score = "error", None
            judgments.append(Judgment(observation, observation.output_hash, presentation, repetition, verdict,
                                      None if score is None else float(score), response, error))
    return JudgmentBatch(grader_bytes, tuple(judgments), seed, datetime.now(timezone.utc),
                         tuple(o.case_id for o in observations), repeats)


def capture_executions(rows, *, candidate_hash, execute, repeats):
    rows = tuple(rows)
    require_hash(candidate_hash)
    if (not rows or any(not isinstance(row, CaseRow) for row in rows) or type(repeats) is not int
            or not 2 <= repeats <= 16 or len(rows) * repeats > MAX_POSITIONS):
        raise ValueError("Bounded independent execution rows required")
    if not callable(execute) or len({r.case_id for r in rows}) != len(rows):
        raise ValueError("Declared host execution and unique cases required")
    observations, positions = [], []
    for row in rows:
        for repetition in range(repeats):
            try:
                returned = execute(row)
            except Exception as exc:
                error = (type(exc).__name__ + ":" + str(exc)).encode("utf-8")[:1_048_576]
                position = ExecutionPosition(len(positions), repetition,
                    Observation.capture(row, candidate_hash, output=None, error=error), "callback_error", None, None)
            else:
                position = ExecutionPosition.capture_returned(row, candidate_hash, output=returned,
                    ordinal=len(positions), repetition=repetition)
            positions.append(position)
            observations.append(position.observation)
    return ExecutionBatch(candidate_hash, tuple(observations), datetime.now(timezone.utc), tuple(positions))


def capture_control(kind, rows, *, candidate_hash, execute, grader_descriptor, runner, repeats, seed):
    rows = tuple(rows)
    if kind not in {"known_good", "known_bad", "disabled", "improved"}:
        raise ValueError("Declared sensitivity control required")
    executed = capture_executions(rows, candidate_hash=candidate_hash, execute=execute, repeats=2)
    # The sensitivity batch judges one captured output per case; execution
    # variability is retained in a separate ExecutionBatch when requested.
    observations = tuple(executed.executions[2 * i] for i in range(len(rows)))
    references = tuple(canonical_bytes(row.reference.model_dump(mode="json")) for row in rows)
    if any(o.output_bytes is None or o.error is not None for o in observations):
        return ControlEvidence(kind, None, references, executed, repeats)
    return ControlEvidence(kind, capture_judgments(observations, grader_descriptor=grader_descriptor,
        runner=runner, repeats=repeats, seed=seed), references, executed, repeats)


def qualify_grader_details(repeated_judgments, controls):
    if not isinstance(repeated_judgments, JudgmentBatch):
        raise TypeError("Captured host judgment batch required")
    controls = tuple(controls)
    if len(controls) > 16 or any(not isinstance(c, ControlEvidence) for c in controls):
        raise TypeError("Captured bounded control evidence required")
    batch = repeated_judgments
    judgments = batch.judgments
    if not judgments or len(judgments) > MAX_POSITIONS:
        raise ValueError("Captured judgment inventory required")
    observations, per_output = {}, {}
    for judgment in judgments:
        if judgment.output_hash != digest_bytes(judgment.observation.output_bytes):
            raise ValueError("Judgment exact output join mismatch")
        observations[judgment.observation.case_id] = judgment.observation
        per_output.setdefault((judgment.observation.case_id, judgment.output_hash), []).append(judgment)
    candidates = {o.candidate_hash for o in observations.values()}
    if len(candidates) != 1:
        raise ValueError("Repeatability requires unchanged candidate")
    groups = {o.independence_group for o in observations.values()}
    flips = sum(sum(a.verdict != b.verdict for a, b in zip(items, items[1:])) for items in per_output.values())
    spreads = [max(values) - min(values) for items in per_output.values()
               if (values := [j.score for j in items if j.score is not None])]
    spread = None if not spreads else max(spreads)
    limits = ["provisional_reference", "actual_grader_origin_unattested", "protected_custody_missing", "statistical_power_unestablished"]
    expected_cases = batch.case_ids or tuple(observations)
    evidence = [_judgment_evidence("primary", batch, expected_cases)]
    for control in controls:
        if isinstance(control.batch, JudgmentBatch) or control.kind != "independent_execution":
            control_batch = control.batch if isinstance(control.batch, JudgmentBatch) else None
            if control_batch is not None and control_batch.grader_hash != batch.grader_hash:
                raise ValueError("Control grader identity mismatch")
            evidence.append(_judgment_evidence(control.kind, control_batch, expected_cases, control.grading_repetitions))
    if evidence[0].limits:
        limits.append("primary_grading_incomplete")
    if any(e.limits for e in evidence[1:]):
        limits.append("control_grading_incomplete")
    if len(groups) < 2:
        limits.append("independent_groups_inadequate")
    if any(len(items) < 2 or len({j.order for j in items}) < 2 for items in per_output.values()):
        limits.append("presentation_repeatability_incomplete")
    if any(j.verdict in {"error", "abstain"} for j in judgments):
        limits.append("grader_errors_or_abstentions")
    kinds = {c.kind: c.batch for c in controls if c.batch is not None}
    references = {c.kind: c.references for c in controls}
    if any(c.execution_batch is not None and any(o.error is not None or o.output_bytes is None for o in c.execution_batch.executions) for c in controls):
        limits.append("control_execution_incomplete")
    if len({c.kind for c in controls}) != len(controls):
        raise ValueError("Control identity duplicated")
    if not {"known_good", "known_bad", "disabled", "improved"} <= kinds.keys():
        limits.append("sensitivity_controls_missing")
    paired = []
    if {"known_good", "known_bad", "disabled", "improved"} <= kinds.keys():
        for control in controls:
            if not isinstance(control.batch, JudgmentBatch):
                continue
            if control.batch.grader_hash != batch.grader_hash:
                raise ValueError("Control grader identity mismatch")
        anchored = True
        for kind in ("known_good", "known_bad", "disabled", "improved"):
            if not references[kind]:
                anchored = False
                continue
            reference_by_case = {ref.case_id: ref for ref in (Reference.model_validate(strict_loads(raw)) for raw in references[kind])}
            if len(reference_by_case) != len(references[kind]):
                raise ValueError("Control reference duplicated")
            for judgment in kinds[kind].judgments:
                if judgment.observation.case_id not in reference_by_case:
                    raise ValueError("Control reference missing")
                assessment = score_case(judgment.observation, reference_by_case[judgment.observation.case_id])
                deterministic = [v.verdict for v in assessment.effect_verdicts.values()]
                if any(v in {"unassessed", "ambiguous"} for v in deterministic):
                    anchored = False
                if (kind in {"known_good", "improved"} and any(v != "correct" for v in deterministic)
                        or kind in {"known_bad", "disabled"} and "incorrect" not in deterministic):
                    anchored = False
        if not anchored:
            limits.append("control_reference_evidence_missing")
        def group_scores(control):
            by_group = {}
            for j in control.judgments:
                if j.score is not None:
                    by_group.setdefault(j.observation.independence_group, []).append(j.score)
            return {g: sum(values) / len(values) for g, values in by_group.items()}
        good, bad = group_scores(kinds["known_good"]), group_scores(kinds["known_bad"])
        disabled, improved = group_scores(kinds["disabled"]), group_scores(kinds["improved"])
        matched = groups & good.keys() & bad.keys() & disabled.keys() & improved.keys()
        if matched != groups or any(good[g] <= bad[g] or improved[g] <= disabled[g] for g in matched):
            limits.append("sensitivity_unestablished")
        paired = [(group, improved[group] - disabled[group]) for group in sorted(matched)]
        for first, second in (("known_good", "known_bad"), ("disabled", "improved")):
            left = {j.observation.case_id: j.observation for j in kinds[first].judgments}
            right = {j.observation.case_id: j.observation for j in kinds[second].judgments}
            if set(left) != set(observations) or set(right) != set(observations):
                limits.append("control_case_inventory_mismatch")
            for case in set(left) & set(right) & set(observations):
                for name in ("input_hash", "source_hash", "reference_hash", "label_hash", "rubric_hash", "lineage_hash", "independence_group"):
                    if getattr(left[case], name) != getattr(observations[case], name) or getattr(right[case], name) != getattr(observations[case], name):
                        raise ValueError("Control source identity mismatch")
                if left[case].output_hash == right[case].output_hash or left[case].candidate_hash == right[case].candidate_hash:
                    limits.append("control_change_unestablished")
    execution_disagreements = None
    if "independent_execution" not in kinds:
        limits.append("independent_execution_missing")
    else:
        executions = kinds["independent_execution"]
        if not isinstance(executions, ExecutionBatch):
            limits.append("independent_execution_origin_unattested")
        else:
            per_case, counts = {}, {}
            for observation in executions.executions:
                if observation.case_id not in observations or observation.candidate_hash != next(iter(candidates)):
                    raise ValueError("Independent execution candidate/case mismatch")
                for name in ("input_hash", "source_hash", "reference_hash", "label_hash", "rubric_hash", "lineage_hash", "independence_group"):
                    if getattr(observation, name) != getattr(observations[observation.case_id], name):
                        raise ValueError("Independent execution source mismatch")
                per_case.setdefault(observation.case_id, set()).add(observation.output_hash)
                counts[observation.case_id] = counts.get(observation.case_id, 0) + 1
                if observation.error is not None or observation.output_hash is None:
                    limits.append("independent_execution_incomplete")
            if set(counts) != set(observations) or any(n < 2 for n in counts.values()):
                limits.append("independent_execution_incomplete")
            execution_disagreements = sum(len(hashes) - 1 for hashes in per_case.values())
    missing = any(x in limits for x in ("primary_grading_incomplete", "control_grading_incomplete", "independent_groups_inadequate", "presentation_repeatability_incomplete", "sensitivity_controls_missing", "sensitivity_unestablished", "independent_execution_missing", "grader_errors_or_abstentions", "control_reference_evidence_missing", "control_case_inventory_mismatch", "control_change_unestablished", "independent_execution_origin_unattested", "independent_execution_incomplete", "control_execution_incomplete"))
    limits = list(dict.fromkeys(limits))
    sources = {name: fingerprint({"domain": "qualification-" + name,
        "identities": [getattr(o, name) for o in observations.values()]})
        for name in ("source_hash", "reference_hash", "label_hash", "rubric_hash", "lineage_hash")}
    receipt = QualificationReceipt(**sources, total_cases=len(observations), included_cases=len(observations),
        ambiguous_cases=sum(any(j.verdict == "abstain" for j in judgments if j.observation.case_id == case) for case in observations),
        excluded_cases=0, candidate_hash=next(iter(candidates)), assessment_hashes=[digest_bytes(canonical_bytes({
            "kind": e.kind, "ordinal": ordinal, "case": j.observation.case_id, "output_hash": j.output_hash, "grader_hash": e.batch.grader_hash,
            "order": list(j.order), "repetition": j.repetition, "response": None if j.response_bytes is None else digest_bytes(j.response_bytes),
            "error": None if j.error is None else digest_bytes(j.error)})) for e in evidence if e.batch is not None for ordinal, j in enumerate(e.batch.judgments)],
        status="incomplete" if missing else "rehearsal", qualification_limits=limits, as_of=batch.captured_at)
    return QualificationSummary(receipt, judgments, len(groups), flips, spread,
        sum(e.abstentions for e in evidence), sum(e.errors for e in evidence),
        execution_disagreements, tuple(paired), "Independent-group descriptive differences only; available scores exclude missing/error/abstaining positions retained in judgment_evidence; no calibrated confidence or power claim",
        tuple(evidence))


def qualify_grader(repeated_judgments, controls):
    return qualify_grader_details(repeated_judgments, controls).receipt
