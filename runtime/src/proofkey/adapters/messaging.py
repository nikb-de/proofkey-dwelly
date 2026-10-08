"""Scoped messaging port for the independent simulated provider."""
from datetime import datetime

from ..contracts import AuthorityReadback, DispatchResult, EffectIntent, ReadRequest


class MessagingAdapter:
    def __init__(self, world):
        self._world = world

    def read_message(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_message", request)

    def send_clarification(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        return self._world._dispatch("send_clarification", intent, deadline=deadline)

    def send_status(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        return self._world._dispatch("send_status", intent, deadline=deadline)
