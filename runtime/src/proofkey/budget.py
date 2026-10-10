"""Finite, cumulative case accounting. Caller records active elapsed time explicitly."""
from datetime import datetime
import math

from .contracts import BudgetLedger


class BudgetExceeded(RuntimeError):
    """No remaining allowance; never permission to enter a transport."""


def check_time(ledger: BudgetLedger, now: datetime):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("Accounting requires an aware time")
    if now >= ledger.deadline or ledger.active_seconds >= ledger.max_active_seconds:
        raise BudgetExceeded("Case execution budget exhausted")


def tool_timeout(ledger: BudgetLedger, now: datetime) -> float:
    check_time(ledger, now)
    return min(ledger.max_tool_seconds, ledger.max_active_seconds - ledger.active_seconds,
               (ledger.deadline - now).total_seconds())


def debit(ledger: BudgetLedger, kind: str, amount, now: datetime, *, handoff=False) -> BudgetLedger:
    check_time(ledger, now)
    if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
        raise ValueError("Debit must be positive and finite")
    if kind != "active_seconds" and type(amount) is not int:
        raise ValueError("Discrete debit requires an integer")
    data = ledger.model_dump()
    caps = {"active_seconds": "max_active_seconds", "tool_calls": "max_tool_calls",
            "planner_calls": "max_planner_calls", "clarifications": "max_clarifications", "effects": "max_effects"}
    if kind in caps:
        cap = data[caps[kind]]
        if kind == "effects" and not handoff:
            cap -= data["reserved_handoff_effects"]
        if data[kind] + amount > cap:
            raise BudgetExceeded("Case allowance exhausted: " + kind)
        data[kind] += amount
    elif kind.startswith(("reconciliation_reads:", "retries:")):
        field, action_id = kind.split(":", 1)
        if not action_id:
            raise ValueError("Per-intent allowance requires an action ID")
        consumed = data[field].get(action_id, 0)
        if consumed + amount > data["max_" + field]:
            raise BudgetExceeded("Per-intent allowance exhausted")
        data[field][action_id] = consumed + amount
        if field == "reconciliation_reads":
            if data["tool_calls"] + amount > data["max_tool_calls"]:
                raise BudgetExceeded("Tool allowance exhausted")
            data["tool_calls"] += amount
    else:
        raise ValueError("Unknown accounting kind")
    return BudgetLedger.model_validate(data)


def validate_budget(ledger: BudgetLedger):
    """Reject incompatible global ceilings and overdrawn persisted ledgers."""
    ceilings = {"max_active_seconds": 120.0, "max_planner_calls": 4, "max_tool_calls": 24,
                "max_effects": 6, "max_reconciliation_reads": 3, "max_retries": 1,
                "max_clarifications": 2, "max_tool_seconds": 10.0}
    if any(getattr(ledger, field) > limit for field, limit in ceilings.items()):
        raise ValueError("Admission exceeds global finite ceilings")
    if ledger.reserved_handoff_effects < 1 or ledger.reserved_handoff_effects > ledger.max_effects:
        raise ValueError("Admission must reserve a handoff effect")
    for field in ("active_seconds", "planner_calls", "tool_calls", "effects", "clarifications"):
        if getattr(ledger, field) > getattr(ledger, "max_" + field):
            raise ValueError("Stored case accounting exceeds ceiling")
    for field in ("reconciliation_reads", "retries"):
        if any(count > getattr(ledger, "max_" + field) for count in getattr(ledger, field).values()):
            raise ValueError("Stored per-intent accounting exceeds ceiling")
    for role in ledger.role_allowances.values():
        if (role.invocations > role.max_invocations or role.cost > role.max_cost
                or any(key not in role.usage_allowances or amount > role.usage_allowances[key] for key, amount in role.usage.items())):
            raise ValueError("Stored role accounting exceeds ceiling")


def initial_budget(ledger: BudgetLedger):
    """Trusted admission can tighten defaults, but cannot raise global ceilings."""
    validate_budget(ledger)
    counts = (ledger.active_seconds, ledger.tool_calls, ledger.planner_calls, ledger.effects, ledger.clarifications)
    if any(counts) or ledger.reconciliation_reads or ledger.retries:
        raise ValueError("Initial accounting must start unconsumed")
    if any(role.invocations or role.cost or role.usage for role in ledger.role_allowances.values()):
        raise ValueError("Initial role accounting must start unconsumed")


def preserve_budget(incoming: BudgetLedger, current: BudgetLedger) -> BudgetLedger:
    """Checkpoint writes move control state; only accounting transactions debit."""
    scalar_caps = ("max_active_seconds", "max_planner_calls", "max_tool_calls", "max_effects",
                   "reserved_handoff_effects", "max_reconciliation_reads", "max_retries",
                   "max_clarifications", "max_tool_seconds")
    if incoming.deadline > current.deadline or any(getattr(incoming, key) != getattr(current, key) for key in scalar_caps):
        raise ValueError("Checkpoint cannot relax/change frozen allowances")
    if set(incoming.role_allowances) != set(current.role_allowances):
        raise ValueError("Checkpoint cannot change enabled role allowances")
    for name, role in current.role_allowances.items():
        other = incoming.role_allowances[name]
        if (other.max_invocations, other.max_cost, other.usage_allowances) != (role.max_invocations, role.max_cost, role.usage_allowances):
            raise ValueError("Checkpoint cannot change role ceilings")
    data = current.model_dump()
    data["deadline"] = incoming.deadline
    return BudgetLedger.model_validate(data)
