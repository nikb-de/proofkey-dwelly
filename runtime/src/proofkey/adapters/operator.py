"""Scoped operator port for the independent simulated provider."""
from datetime import datetime

from ..contracts import AuthContext, AuthorityReadback, DispatchResult, EffectIntent, ReadRequest


class OperatorAdapter:
    def __init__(self, world):
        self._world = world

    def read_receipt(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_receipt", request)

    def read_resume(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_resume", request)

    def read_owner(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_owner", request)

    def enqueue_handoff(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        return self._world._dispatch("enqueue_handoff", intent, deadline=deadline)

    def transfer_owner(self, intent: EffectIntent, *, deadline: datetime | None = None,
                       auth: AuthContext | None = None) -> DispatchResult:
        return self._world._dispatch("transfer_owner", intent, deadline=deadline, auth=auth)
