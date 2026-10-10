"""Independent synthetic J06 cases; no product fingerprint builder."""
from datetime import timedelta
from hashlib import sha256
import json

from proofkey.contracts import CanonicalRequest
from proofkey.execution import ExecutionContext


def cj(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def context(clock, seconds=5):
    return ExecutionContext.capture(clock.now() + timedelta(seconds=seconds), clock)


def case_data(kind="reschedule_window"):
    window = kind == "reschedule_window"
    suffix = "WINDOW" if window else "GOODS"
    ids = dict(case_id="J06-CASE-" + suffix, object_id="J06-ORDER-" + suffix,
               principal_id="J06-USER-" + suffix, request_id="J06-REQ-" + suffix)
    inventory = {"j06-widget": 2, "j06-cable": 1}
    arguments = {"inventory": inventory}
    if window:
        arguments.update(window_start="2026-10-08T13:00:00+00:00",
                         window_end="2026-10-08T15:00:00+00:00")
    body = dict(**ids, request_revision="v1", consent_revision="v1", kind=kind,
                consent_mode="window" if window else "unknown",
                arguments=arguments, evidence_ids=[], narrative=None)
    business = sha256(cj({key: body[key] for key in
                        ("kind", "consent_mode", "arguments")})).hexdigest()
    values = {
        "case.binding": ids, "case.request_revision": "v1",
        "case.authorization": "verified", "case.generation": "G1",
        "case.question_revision": "v1", "case.result_revision": "v1",
        "case.completeness": "complete", "customer.consent": "granted",
        "customer.consent_revision": "v1", "customer.consent_mode": body["consent_mode"],
        "customer.request_fingerprint": business,
        "delivery.status": "scheduled" if window else "delivered",
        "delivery.risk": "safe", "delivery.stage": "eligible",
        "scheduling.capacity": ["J06-S3", "J06-S4"], "scheduling.slot": "J06-S0",
        "scheduling.slot_details": {
            "J06-S3": {"start": "2026-10-08T13:00:00+00:00", "end": "2026-10-08T14:00:00+00:00"},
            "J06-S4": {"start": "2026-10-08T14:00:00+00:00", "end": "2026-10-08T15:00:00+00:00"}},
        "policy.version": "v1", "ownership.state_revision": "v1",
        "ownership.state": "accepted", "ownership.epoch": 0,
        "ownership.owner": ids["principal_id"], "goods.inventory": inventory,
        "goods.quantity": 3, "goods.refusal": "none", "service.refusal": "none",
        "returns.destination": "J06-DEPOT-B", "returns.status": "none",
        "messaging.permission": "granted", "messaging.recipient": ids["principal_id"],
        "operator.packet_hash": "b" * 64, "operator.packet_revision": "v1",
        "operator.recipient": "J06-OPERATOR"}
    facts = {key: dict(value=value, revision="v1", case_id=ids["case_id"],
                      object_id=ids["object_id"], evidence_ref="synthetic-j06:" + key)
             for key, value in values.items()}
    fixture = dict(version="synthetic-provider-v1", as_of="2026-10-08T10:00:00+00:00",
                   scopes=[dict(case_id=ids["case_id"], object_id=ids["object_id"],
                                principal_id=ids["principal_id"],
                                readers={ids["principal_id"]: "j06-synthetic-proof"})], facts=facts)
    return CanonicalRequest.model_validate(body), fixture
