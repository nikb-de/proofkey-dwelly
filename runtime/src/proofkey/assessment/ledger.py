"""Bounded ordinal inventory, including malformed and duplicate supplied rows."""
from dataclasses import dataclass, replace
from proofkey.contracts import AuditFinding, LedgerAudit, FrozenDict
from proofkey.identity import fingerprint
from proofkey.profiles import load_profile
from .contracts import CaseRow, MAX_POSITIONS, canonical_bytes, digest_bytes, strict_loads


@dataclass(frozen=True)
class LedgerPosition:
    ordinal: int
    raw_bytes: bytes | None
    raw_hash: str | None
    row: CaseRow | None
    status: str
    effective_split: str | None


@dataclass(frozen=True)
class LedgerInspection:
    audit: LedgerAudit
    positions: tuple[LedgerPosition, ...]
    control_counts: FrozenDict
    independent_groups: tuple[str, ...]


def inspect_case_ledger(rows):
    iterator = iter(rows)
    supplied = []
    for item in iterator:
        supplied.append(item)
        if len(supplied) > MAX_POSITIONS:
            raise ValueError("Assessment ledger exceeds bounded positions")
    positions, findings, seen, group_splits, feedback_groups = [], [], {}, {}, set()
    def finding(ordinal, reason, severity="error"):
        findings.append(AuditFinding(requirement_id="case_ledger", severity=severity,
                        reason=reason, evidence_refs=[f"ordinal-{ordinal}"]))
    for ordinal, supplied_row in enumerate(supplied):
        raw, row, status = None, None, "invalid"
        try:
            raw = supplied_row if type(supplied_row) is bytes else supplied_row.encode("utf-8") if type(supplied_row) is str else canonical_bytes(supplied_row)
            data = strict_loads(raw)
            row = CaseRow.model_validate(data)
            profile = load_profile(row.profile_name)
            if row.profile_hash != profile.release_hash or row.input.kind not in profile.processes:
                raise ValueError("Invalid profile join")
            mode = {"reschedule_window": "window", "reschedule_exact": "exact_slot"}.get(row.input.kind)
            if mode and row.input.consent_mode not in {mode, "unknown"}:
                raise ValueError("Invalid consent join")
            status = "valid"
            if row.case_id in seen:
                status = "duplicate"
                finding(ordinal, "duplicate_case_id")
                if seen[row.case_id] != canonical_bytes(row.model_dump(mode="json")):
                    finding(ordinal, "conflicting_duplicate_metadata")
            else:
                seen[row.case_id] = canonical_bytes(row.model_dump(mode="json"))
            group_splits.setdefault(row.independence_group, set()).add((row.split, row.split_seed))
            if row.feedback:
                feedback_groups.add(row.independence_group)
        except (TypeError, ValueError, UnicodeError, RecursionError):
            row = None
            finding(ordinal, "invalid_case_row")
        raw_hash = digest_bytes(raw) if raw is not None and len(raw) <= 1_048_576 else None
        positions.append(LedgerPosition(ordinal, raw, raw_hash, row, status, None if row is None else row.split))
    for p in positions:
        if p.row is not None and len(group_splits[p.row.independence_group]) > 1:
            finding(p.ordinal, "cross_split_group")
    positions = tuple(replace(p, effective_split="validation") if p.row is not None and p.row.independence_group in feedback_groups else p for p in positions)
    valid = [p.row for p in positions if p.row is not None]
    counts = {}
    for row in valid:
        family = row.source.get("family")
        if not isinstance(family, str) or not family:
            finding(0, "missing_source_family")
            continue
        counts.setdefault(family, {"positive": 0, "unsafe": 0, "insufficient": 0})[row.control] += 1
    for family, controls in counts.items():
        if any(value == 0 for value in controls.values()):
            findings.append(AuditFinding(requirement_id="case_balance", severity="warning",
                reason="control_family_incomplete", evidence_refs=["family-counts"]))
    ambiguous = sum(bool(row.reference.ambiguity) for row in valid)
    excluded = sum(row.reference.exclusion is not None for row in valid)
    sources = {}
    for name in ("source_hash", "reference_hash", "label_hash", "rubric_hash", "lineage_hash"):
        sources[name] = fingerprint({"domain": "ledger-" + name, "positions": [
            {"ordinal": p.ordinal, "raw_hash": p.raw_hash, "identity": None if p.row is None else getattr(p.row.reference, name)} for p in positions]})
    audit = LedgerAudit(**sources, total_cases=len(positions), included_cases=len(positions) - excluded,
                        ambiguous_cases=ambiguous, excluded_cases=excluded, findings=findings)
    return LedgerInspection(audit, positions, FrozenDict({k: FrozenDict(v) for k, v in counts.items()}),
                            tuple(sorted(group_splits)))


def validate_case_ledger(rows):
    return inspect_case_ledger(rows).audit
