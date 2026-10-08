"""Scoped returns port for the independent simulated provider."""
from datetime import datetime

from ..contracts import AuthorityReadback, DispatchResult, EffectIntent, ReadRequest


class ReturnsAdapter:
    def __init__(self, world):
        self._world = world

    def read_return_policy(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_return_policy", request)

    def read_return(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_return", request)

    def create_return(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        return self._world._dispatch("create_return", intent, deadline=deadline)
