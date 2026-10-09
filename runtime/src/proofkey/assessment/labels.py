"""Frozen provisional effects and append-only unsent review history."""
from dataclasses import dataclass
from proofkey.contracts import CaseAssessment, EffectVerdict, RepeatabilityResult, SensitivityResult, NoiseResult
from proofkey.identity import fingerprint
from .contracts import Observation, ObservedOutput, Reference, canonical_bytes, digest_bytes, strict_loads


def score_case(observed, reference):
    if not isinstance(observed, Observation) or not isinstance(reference, Reference):
        raise TypeError("Typed frozen observation and reference required")
    for name in ("case_id", "input_hash", "source_hash", "reference_hash", "label_hash", "rubric_hash", "lineage_hash"):
        if getattr(observed, name) != getattr(reference, name):
            raise ValueError("Assessment evidence join mismatch")
    output = None if observed.output_bytes is None else ObservedOutput.model_validate(strict_loads(observed.output_bytes))
    verdicts = {}
    for effect, expected in reference.required_behavior.items():
        actual = None if output is None else output.effects.get(effect)
        if observed.error is not None or output is None:
            verdict, reason = "unassessed", "output_unavailable"
        elif reference.ambiguity or reference.exclusion is not None:
            verdict, reason = "ambiguous", "reference_ambiguous_or_excluded"
        elif expected.status == "absent":
            verdict, reason = ("correct", None) if actual is None else ("incorrect", "unexpected_effect")
        elif (actual is not None and actual.status == expected.status and actual.postcondition == expected.postcondition
              and (not expected.requires_evidence or actual.evidence_refs)):
            verdict, reason = "correct", None
        else:
            verdict, reason = "incorrect", "effect_reference_mismatch"
        verdicts[effect] = EffectVerdict(verdict=verdict, evidence_refs=[] if actual is None else actual.evidence_refs, reason=reason)
    forbidden = [] if output is None else list(output.forbidden_effects)
    if output is not None:
        forbidden_names = {"physical_receipt", "refund", "payment", "internal_case_creation"}
        forbidden.extend(effect for effect in output.effects if effect in forbidden_names)
        def claims(value):
            if isinstance(value, dict):
                return any((key in forbidden_names and item not in (None, False, 0, "not_executed", "unavailable"))
                           or claims(item) for key, item in value.items())
            return isinstance(value, list) and any(claims(item) for item in value)
        if any(claims(effect.postcondition) for effect in output.effects.values()):
            forbidden.append("unsupported_completion_claim")
        for name, effect in output.effects.items():
            if name not in reference.required_behavior:
                verdicts[name] = EffectVerdict(verdict="incorrect", evidence_refs=effect.evidence_refs,
                    reason="undeclared_effect")
    verdicts["forbidden_effects"] = EffectVerdict(verdict="unassessed" if output is None or observed.error is not None else "incorrect" if forbidden else "correct",
        evidence_refs=[], reason="forbidden_effect_observed" if forbidden else None)
    return CaseAssessment(**reference.sources(), case_id=reference.case_id, effect_verdicts=verdicts,
        repeatability=RepeatabilityResult(runs=0, agreements=0), sensitivity=SensitivityResult(trials=0, detected=0),
        noise=NoiseResult(trials=0, disagreements=0), qualification_limits=["provisional_reference", "evidence_origin_unattested", "grader_unqualified"])


@dataclass(frozen=True)
class LabelHistory:
    reference_bytes: bytes
    entries: tuple[bytes, ...]

    def __post_init__(self):
        Reference.model_validate(strict_loads(self.reference_bytes))
        if type(self.entries) is not tuple or not self.entries or len(self.entries) > 256:
            raise ValueError("Bounded immutable label history required")
        for entry in self.entries:
            strict_loads(entry)

    @classmethod
    def propose(cls, reference, *, requested_model, observed_model, prompt, evidence_refs, disagreements=()):
        if not isinstance(reference, Reference):
            raise TypeError("Typed reference required")
        if type(requested_model) is not str or not requested_model.strip() or observed_model is not None and (type(observed_model) is not str or not observed_model.strip()):
            raise ValueError("Declared and observed model identity required")
        entry = {"kind": "proposal", "status": "provisional_llm", "mode": "replay" if observed_model else "unknown",
            "requested_model": requested_model, "observed_model": observed_model, "prompt": prompt,
            "prompt_hash": fingerprint(prompt), "evidence_refs": list(evidence_refs), "disagreements": list(disagreements),
            "reference_hash": reference.reference_hash}
        return cls(canonical_bytes(reference.model_dump(mode="json")), (canonical_bytes(entry),))

    def review(self, *, reviewer, disposition, evidence_refs, replacement=None):
        if type(reviewer) is not str or not reviewer.strip() or disposition not in {"accept", "change", "ambiguous"}:
            raise ValueError("Review identity and disposition required")
        if not evidence_refs or disposition == "change" and replacement is None or disposition != "change" and replacement is not None:
            raise ValueError("Review evidence and explicit replacement required")
        entry = {"kind": "review", "reviewer": reviewer, "disposition": disposition,
                 "evidence_refs": list(evidence_refs), "replacement": replacement,
                 "prior_history_hash": self.label_set_hash, "custody": "unattested"}
        return LabelHistory(self.reference_bytes, self.entries + (canonical_bytes(entry),))

    @property
    def label_set_hash(self):
        return digest_bytes(canonical_bytes({"reference": digest_bytes(self.reference_bytes), "history": [digest_bytes(entry) for entry in self.entries]}))

    @property
    def unsent_packet(self):
        return canonical_bytes({"delivery": "unsent", "reference": strict_loads(self.reference_bytes),
                                "history": [strict_loads(entry) for entry in self.entries], "label_set_hash": self.label_set_hash})
