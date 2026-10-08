"""Scoped scheduling port for the independent simulated provider."""
from datetime import datetime

from ..contracts import AuthorityReadback, DispatchResult, EffectIntent, ReadRequest


class SchedulingAdapter:
    def __init__(self, world):
        self._world = world

    def list_permitted_slots(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("list_permitted_slots", request)

    def read_schedule(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_schedule", request)

    def reschedule(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        return self._world._dispatch("reschedule", intent, deadline=deadline)
