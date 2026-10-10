"""Durable conservative reservations, with an exclusive process-level ledger lock.

Reservations are never refunded: unsuccessful requests and unknown usage may be
billed. This is a local admission policy under configured prices, not a provider
billing cap. The application does not perform retries.
"""
from decimal import Decimal, InvalidOperation
import fcntl
import json
import os
from pathlib import Path


FRAMING_ALLOWANCE_TOKENS = 512


def sync_directory(path):
    """Persist directory entries as well as file bytes before admitting spend."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def positive_decimal(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError("invalid_" + label)
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("invalid_" + label) from None
    if not result.is_finite() or result <= 0:
        raise ValueError("invalid_" + label)
    return result


class BudgetLedger:
    def __init__(self, path, cap_usd):
        self.path = Path(path)
        self.cap = positive_decimal(cap_usd, "budget")
        if self.cap > 25:
            raise ValueError("budget_above_25_usd")
        self.stream = None
        self.reservations = {}
        self.spent = {}

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.path, flags, 0o600)
        self.stream = os.fdopen(descriptor, "r+", encoding="utf-8")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            self.stream = None
            raise ValueError("budget_locked") from None
        try:
            for line in self.stream:
                row = json.loads(line)
                if row.get("event") == "created" and Decimal(row["cap_usd"]) != self.cap:
                    raise ValueError("budget_cap_changed")
                if row.get("event") == "reserve":
                    key = (row["provider"], row["model"])
                    self.spent[key] = self.spent.get(key, Decimal(0)) + Decimal(row["amount_usd"])
                    self.reservations[row["request_key"]] = row
            if self.path.stat().st_size == 0:
                self._append({"event": "created", "cap_usd": str(self.cap),
                              "policy": "full_reservation_retained_no_refunds",
                              "framing_allowance_tokens": FRAMING_ALLOWANCE_TOKENS})
            sync_directory(self.path.parent)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *args):
        if self.stream is not None:
            self.stream.close()
            self.stream = None

    def _append(self, row):
        if self.stream is None:
            raise ValueError("budget_not_locked")
        self.stream.seek(0, os.SEEK_END)
        self.stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def reserve(self, config, system, prompt, max_output_tokens, request_key):
        if request_key in self.reservations:
            raise ValueError("duplicate_request")
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("invalid_max_output_tokens")
        input_rate = positive_decimal(config["input_usd_per_million"], "input_price")
        output_rate = positive_decimal(config["output_usd_per_million"], "output_price")
        input_bound = len(system.encode("utf-8")) + len(prompt.encode("utf-8")) + FRAMING_ALLOWANCE_TOKENS
        amount = (input_bound * input_rate + max_output_tokens * output_rate) / Decimal(1_000_000)
        key = (config["provider"], config["model"])
        if self.spent.get(key, Decimal(0)) + amount > self.cap:
            raise ValueError("budget_exhausted")
        row = {"event": "reserve", "request_key": request_key, "provider": key[0], "model": key[1],
               "estimated_input_token_upper_bound": input_bound, "max_output_tokens": max_output_tokens,
               "amount_usd": str(amount), "reserved_usd": float(amount)}
        self._append(row)  # durable before admission is returned to the caller
        self.reservations[request_key] = row
        self.spent[key] = self.spent.get(key, Decimal(0)) + amount
        return row

    def record_outcome(self, request_key, status, input_tokens=None, output_tokens=None):
        if request_key not in self.reservations:
            raise ValueError("unreserved_request")
        self._append({"event": "outcome", "request_key": request_key, "status": status,
                      "input_tokens": input_tokens, "output_tokens": output_tokens,
                      "reservation_retained": True})

    def summary(self):
        return {"cap_per_provider_model_usd": float(self.cap),
                "reserved_usd": float(sum(self.spent.values(), Decimal(0))),
                "reservation_count": len(self.reservations),
                "models": [{"provider": provider, "model": model, "reserved_usd": float(amount)}
                           for (provider, model), amount in sorted(self.spent.items())],
                "policy": "conservative_local_admission_not_provider_billing_cap_no_refunds"}
