"""Scoped delivery port for the independent simulated provider."""
from datetime import datetime

from ..contracts import AuthorityReadback, DispatchResult, EffectIntent, ReadRequest


class DeliveryAdapter:
    def __init__(self, world):
        self._world = world

    def read_delivery(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_delivery", request)

    def read_refusal(self, request: ReadRequest) -> AuthorityReadback:
        return self._world._read("read_refusal", request)

    def register_goods_refusal(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        return self._world._dispatch("register_goods_refusal", intent, deadline=deadline)

    def register_service_refusal(self, intent: EffectIntent, *, deadline: datetime | None = None) -> DispatchResult:
        return self._world._dispatch("register_service_refusal", intent, deadline=deadline)
