"""Scoped case port for the independent simulated provider."""
from ..contracts import AuthorityReadback, DispatchResult, EffectIntent, ReadRequest


class CaseAdapter:
    def __init__(self, world):
        self._world = world

    def read_case(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_case", request)

    def read_principal(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_principal", request)
