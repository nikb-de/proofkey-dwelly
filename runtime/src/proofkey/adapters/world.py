"""Independent SQLite provider, demonstrating synthetic guarantees only.

The journal cannot join this database's transactions. Driver controls are
deliberately absent from the six public ports and their wire responses.
"""
import json
import math
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from ..contracts import (AuthContext, AuthorityObservation, AuthorityReadback, DispatchResult,
                         EffectIntent, EnvironmentProfile, NonexecutionProof,
                         ReadRequest, RevisionVector)
from ..identity import fingerprint
from ..ports import AdapterBundle
from ..process import material_fields
from ..profiles import load_profile, requires_completed_service, validate_profile
from ..ownership_contracts import (ownership_enabled, OWNERSHIP_FIELDS_V1,
    OriginalTransferIdentityV1, TransferRejectedV1)
from .ownership import SyntheticOwnershipSource, strict_fixture_pairs
from ..packet_contracts import (PACKET_FIELDS, PacketContentReceiptV1, packet_enabled,
                                packet_postcondition, validate_packet_arguments, validate_packet_policy, validate_packet_scope)

_EFFECTS = frozenset({"reschedule", "register_goods_refusal", "register_service_refusal", "create_return",
                      "send_clarification", "send_status", "enqueue_handoff", "transfer_owner"})
_BUSINESS_EFFECTS = frozenset({"reschedule", "register_goods_refusal", "register_service_refusal", "create_return"})
_SCOPE_MATERIAL = frozenset({"customer.request_fingerprint", "customer.consent_mode"})
_NEW_FACTS = frozenset({"customer.request_fingerprint", "scheduling.slot_details"})
_FACT_SCOPES = {
    "read_case": {"case": {"binding", "request_revision", "authorization", "generation", "question_revision",
                            "result_revision", "completeness"}, "policy": {"version"}},
    "read_principal": {"customer": {"consent", "consent_revision", "consent_mode", "request_fingerprint"}},
    "read_delivery": {"delivery": {"status", "risk", "stage"}, "goods": {"inventory", "quantity"}},
    "read_refusal": {"goods": {"refusal", "inventory", "quantity"}, "service": {"refusal"}},
    "list_permitted_slots": {"scheduling": {"capacity", "slot", "slot_details"}},
    "read_schedule": {"scheduling": {"capacity", "slot", "slot_details"}},
    "read_return_policy": {"returns": {"destination"}, "policy": {"version"}},
    "read_return": {"returns": {"status", "destination"}},
    "read_message": {"messaging": {"permission", "recipient"}},
    "read_receipt": {"operator": {"packet_hash", "packet_revision", "recipient"}},
    "read_resume": {"operator": {"packet_hash", "packet_revision", "recipient"}},
    "read_owner": {"ownership": {"state", "state_revision", "epoch", "owner"}},
}
_ORIGINAL_SCOPES = {"read_refusal": {"register_goods_refusal", "register_service_refusal"},
                    "read_schedule": {"reschedule"}, "read_return": {"create_return"},
                    "read_message": {"send_clarification", "send_status"},
                    "read_receipt": {"enqueue_handoff"}, "read_resume": {"enqueue_handoff", "transfer_owner"},
                    "read_owner": {"transfer_owner"}}
_FAULTS = frozenset({"none", "business_rejection", "timeout_before", "timeout_after", "wrong_object", "429",
                    "delivered", "owner_accepted", "return_received", "terminal_not_executed", "final_rejection_unknown"})
_FAULT_ALIASES = {"timeout_before_execute": "timeout_before", "timeout_after_execute": "timeout_after"}


@dataclass(frozen=True)
class _Call:
    operation: str
    purpose: str


class _FixtureClock:
    def __init__(self, start):
        self._start = start

    def now(self):
        return self._start


def _scope_contract(profile):
    # Only frozen legacy v1 retains its original scope semantics. A new version
    # or an explicitly designated commitment cannot silently drop protection.
    return profile.version != "v1" or "customer.request_fingerprint" in profile.authorities


def required_material_keys(connection, profile, operation, stage):
    """Trusted manifest plus minimum provider coverage; never caller keys."""
    capability = profile.capabilities.get(operation)
    minimum = material_fields(operation)
    if operation == "enqueue_handoff" and packet_enabled(profile):
        minimum |= PACKET_FIELDS
    if operation == "transfer_owner" and ownership_enabled(profile):
        minimum |= OWNERSHIP_FIELDS_V1
    if _scope_contract(profile) and operation in _BUSINESS_EFFECTS:
        minimum |= _SCOPE_MATERIAL
        if operation == "reschedule":
            minimum |= {"scheduling.slot_details"}
    if operation == "register_service_refusal" and requires_completed_service(profile):
        minimum |= {"delivery.status"}
    if operation not in _EFFECTS or capability is None or not stage:
        return None
    contracts = (capability.permission_basis, capability.acknowledgement, capability.readback,
                 capability.idempotency_scope, capability.conditional_coverage)
    if any(contract.status != "supported" for contract in contracts):
        return None
    covered = set(capability.conditional_coverage.covered_fields)
    if not minimum <= covered:
        return None
    if any(profile.authorities.get(key) != key.partition(".")[0] for key in covered):
        return None
    return covered


def read_material_revisions(connection, required, case_id, object_id):
    rows = connection.execute("SELECT identity,revision FROM facts WHERE case_id=? AND object_id=?",
                              (case_id, object_id))
    return {row[0]: row[1] for row in rows if row[0] in required}


class SimulatedWorld:
    def __init__(self, path: str | Path, fixture: str | Path, *, profile: EnvironmentProfile | None = None,
                 clock=None, fixture_bytes: bytes | None = None):
        if fixture_bytes is not None and (type(fixture_bytes) is not bytes or not 0 < len(fixture_bytes) <= 1048576):
            raise ValueError("Trusted fixture requires bounded nonempty immutable bytes")
        self._path = Path(path)
        self._profile = EnvironmentProfile.model_validate((profile or load_profile("flat-v1")).model_dump())
        if self._profile.version == "v1.4":
            self._profile = validate_profile(self._profile)
        fixture_text = (Path(fixture).read_text(encoding="utf-8") if fixture_bytes is None
                        else fixture_bytes.decode("utf-8"))
        raw = json.loads(fixture_text,
                         object_pairs_hook=strict_fixture_pairs if self._profile.version == "v1.4" else None)
        start = datetime.fromisoformat(raw["as_of"])
        if start.utcoffset() is None or raw.get("version") != "synthetic-provider-v1":
            raise ValueError("Trusted synthetic fixture requires a version and aware time")
        self._clock = clock or _FixtureClock(start)
        self._now()
        self._ownership = (SyntheticOwnershipSource(self, raw.get("ownership_authority"))
                           if ownership_enabled(self._profile) else None)
        self._faults, self._calls = {}, []
        self._driver_lock = threading.Lock()
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS scopes(case_id TEXT,object_id TEXT,principal_id TEXT,readers TEXT,
                    PRIMARY KEY(case_id,object_id));
                CREATE TABLE IF NOT EXISTS facts(case_id TEXT,object_id TEXT,identity TEXT,value TEXT,revision TEXT,
                    evidence_ref TEXT,PRIMARY KEY(case_id,object_id,identity));
                CREATE TABLE IF NOT EXISTS effects(account_id TEXT,provider_key TEXT,case_id TEXT,object_id TEXT,
                    operation TEXT,generation TEXT,action_id TEXT,fingerprint TEXT,identity_hash TEXT,
                    request_id TEXT,stage TEXT,observations TEXT,created_at TEXT,question_id TEXT,
                    transfer_id TEXT,packet_id TEXT,packet_revision TEXT,PRIMARY KEY(account_id,provider_key));
                CREATE TABLE IF NOT EXISTS pressure(account_id TEXT PRIMARY KEY,used INTEGER,active INTEGER,
                    ticks TEXT,blocked_until REAL);
                CREATE TABLE IF NOT EXISTS reservations(token TEXT PRIMARY KEY,account_id TEXT,expires_at REAL);
                CREATE TABLE IF NOT EXISTS final_rejections(account_id TEXT,provider_key TEXT,case_id TEXT,object_id TEXT,
                    operation TEXT,generation TEXT,action_id TEXT,fingerprint TEXT,identity_hash TEXT,
                    request_id TEXT,created_at TEXT,PRIMARY KEY(account_id,provider_key));
            """)
            marker = connection.execute("SELECT value FROM metadata WHERE key='fixture'").fetchone()
            if self._ownership is None and connection.execute("SELECT 1 FROM metadata WHERE key='ownership_fixture'").fetchone():
                raise ValueError("Registered ownership provider cannot reopen under legacy semantics")
            fixture_hash = fingerprint(raw)
            if marker and marker[0] != fixture_hash:
                raise ValueError("Existing provider database belongs to a different fixture")
            if not marker:
                connection.execute("INSERT INTO metadata VALUES('fixture',?)", (fixture_hash,))
                for scope in raw["scopes"]:
                    connection.execute("INSERT INTO scopes VALUES(?,?,?,?)", (scope["case_id"], scope["object_id"],
                                       scope["principal_id"], json.dumps(scope["readers"])))
                for key, fact in raw["facts"].items():
                    authority, separator, field = key.partition(".")
                    if not separator or not authority or not field:
                        raise ValueError("Fixture facts need qualified authority identities")
                    connection.execute("INSERT INTO facts VALUES(?,?,?,?,?,?)", (fact["case_id"], fact["object_id"],
                                       key, json.dumps(fact["value"]), fact["revision"], fact["evidence_ref"]))
            if self._ownership:
                self._ownership.seed(connection)
            for case_id, object_id in connection.execute("SELECT case_id,object_id FROM scopes"):
                required = set().union(*(material_fields(operation) for operation in _EFFECTS))
                if not required <= read_material_revisions(connection, required, case_id, object_id).keys():
                    raise ValueError("Fixture omits provider material facts")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self._path, timeout=0.1)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _now(self):
        now = self._clock.now()
        if not isinstance(now, datetime) or now.utcoffset() is None or not math.isfinite(now.timestamp()):
            raise ValueError("Provider clock requires finite aware timestamps")
        return now.astimezone(timezone.utc)

    def bundle(self) -> AdapterBundle:
        from .case import CaseAdapter
        from .delivery import DeliveryAdapter
        from .scheduling import SchedulingAdapter
        from .returns import ReturnsAdapter
        from .messaging import MessagingAdapter
        from .operator import OperatorAdapter
        return AdapterBundle(CaseAdapter(self), DeliveryAdapter(self), SchedulingAdapter(self), ReturnsAdapter(self),
                             MessagingAdapter(self), OperatorAdapter(self))

    @property
    def calls(self):
        """Test-driver snapshot, never an adapter response."""
        with self._driver_lock:
            return tuple(self._calls)

    def set_fault(self, operation, behavior):
        behavior = _FAULT_ALIASES.get(behavior, behavior)
        if operation not in _EFFECTS | _FACT_SCOPES.keys() or behavior not in _FAULTS:
            raise ValueError("Unknown driver scenario")
        with self._driver_lock:
            self._faults[operation] = behavior

    def mutate(self, fact, value):
        """Test-driver mutation; ambiguous/unqualified keys are rejected."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute("SELECT * FROM facts WHERE identity=?", (fact,)).fetchall()
            if len(rows) != 1:
                raise ValueError("Driver fact must identify one existing qualified fixture fact")
            self._update(connection, rows[0]["case_id"], rows[0]["object_id"], fact, value)

    def material_revisions(self) -> RevisionVector:
        with self._connect() as connection:
            scopes = connection.execute("SELECT case_id,object_id FROM scopes").fetchall()
            if len(scopes) != 1:
                raise ValueError("Driver revision snapshot requires one fixture scope")
            required = set().union(*(material_fields(operation) for operation in _EFFECTS))
            required.update(key for operation in _EFFECTS if operation in self._profile.capabilities
                            for key in self._profile.capabilities[operation].conditional_coverage.covered_fields)
            return RevisionVector(revisions=read_material_revisions(connection, required, *scopes[0]))

    def effect_count(self, operation) -> int:
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM effects WHERE operation=?", (operation,)).fetchone()[0]

    def deliver_target_acceptance(self, instruction) -> bool:
        """Trusted synthetic TEST DRIVER only, absent from every runtime port."""
        if self._ownership is None:
            return False
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return self._ownership.deliver(connection, instruction)

    def _call(self, operation, purpose):
        with self._driver_lock:
            self._calls.append(_Call(operation, purpose))
            return self._faults.get(operation, "none")

    def _limits(self, operation):
        capability = self._profile.capabilities.get(operation)
        if not capability or not capability.shared_limits.account_id:
            return None
        account = capability.shared_limits.account_id
        limits = [cap.shared_limits for cap in self._profile.capabilities.values() if cap.shared_limits.account_id == account]
        # One account cannot acquire looser constraints through another port.
        values = [min((getattr(limit, name) for limit in limits if getattr(limit, name) is not None), default=None)
                  for name in ("quota", "concurrency", "rate_per_second")]
        return (account, *values)

    def _reserve(self, operation, deadline, behavior):
        limits = self._limits(operation)
        now = self._now().timestamp()
        if self._now() >= deadline or limits is None:
            return None
        account, quota, concurrency, rate = limits
        if None in (quota, concurrency, rate) or min(quota, concurrency, rate) <= 0:
            return None
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                now = self._now().timestamp()
                if now >= deadline.timestamp():
                    return None
                connection.execute("INSERT OR IGNORE INTO pressure VALUES(?,0,0,'[]',0)", (account,))
                connection.execute("DELETE FROM reservations WHERE account_id=? AND expires_at<=?", (account, now))
                active = connection.execute("SELECT COUNT(*) FROM reservations WHERE account_id=?", (account,)).fetchone()[0]
                connection.execute("UPDATE pressure SET active=? WHERE account_id=?", (active, account))
                row = connection.execute("SELECT * FROM pressure WHERE account_id=?", (account,)).fetchone()
                ticks = [tick for tick in json.loads(row["ticks"]) if tick > now - 1]
                if behavior == "429":
                    connection.execute("UPDATE pressure SET blocked_until=? WHERE account_id=?", (now + 1, account))
                    return None
                if row["blocked_until"] > now or row["used"] >= quota or row["active"] >= concurrency or len(ticks) >= rate:
                    return None
                ticks.append(now)
                token = str(uuid4())
                connection.execute("INSERT INTO reservations VALUES(?,?,?)", (token, account, deadline.timestamp()))
                connection.execute("UPDATE pressure SET used=used+1,active=active+1,ticks=? WHERE account_id=?",
                                   (json.dumps(ticks), account))
                if self._now() >= deadline:
                    connection.rollback()
                    return None
                return account, token
        except sqlite3.OperationalError:
            return None

    def _release(self, account, token):
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("DELETE FROM reservations WHERE account_id=? AND token=?", (account, token))
                active = connection.execute("SELECT COUNT(*) FROM reservations WHERE account_id=?", (account,)).fetchone()[0]
                connection.execute("UPDATE pressure SET active=? WHERE account_id=?", (active, account))
        except sqlite3.OperationalError:
            # A busy provider may defer cleanup until the bounded lease expires.
            pass

    @staticmethod
    def _facts(connection, case_id, object_id):
        return {row["identity"]: row for row in connection.execute("SELECT * FROM facts WHERE case_id=? AND object_id=?",
                (case_id, object_id))}

    @staticmethod
    def _update(connection, case_id, object_id, identity, value):
        row = connection.execute("SELECT revision FROM facts WHERE case_id=? AND object_id=? AND identity=?",
                                 (case_id, object_id, identity)).fetchone()
        if row is None:
            raise ValueError("Provider effect cannot invent a material fact")
        revision = "v" + str(int(row[0][1:]) + 1) if row[0].startswith("v") and row[0][1:].isdigit() else fingerprint({"revision": row[0], "value": value})
        connection.execute("UPDATE facts SET value=?,revision=? WHERE case_id=? AND object_id=? AND identity=?",
                           (json.dumps(value), revision, case_id, object_id, identity))
        return revision

    def _write_identity_allowed(self, connection, intent):
        binding = intent.binding
        scope = connection.execute("SELECT principal_id FROM scopes WHERE case_id=? AND object_id=?",
                                    (binding.case_id, binding.object_id)).fetchone()
        if not scope or scope[0] != binding.principal_id:
            return False
        facts = self._facts(connection, binding.case_id, binding.object_id)
        values = {key: json.loads(row["value"]) for key, row in facts.items()}
        original = values.get("case.binding")
        identity_matches = (isinstance(original, dict) and all(original.get(field) == getattr(binding, field)
                for field in ("case_id", "object_id", "principal_id", "request_id"))
                and values.get("case.request_revision") == binding.request_revision
                and values.get("customer.consent_revision") == binding.consent_revision
                and values.get("case.generation") == binding.generation
                and values.get("case.authorization") == "verified")
        if _scope_contract(self._profile) and intent.operation in _BUSINESS_EFFECTS:
            commitment = values.get("customer.request_fingerprint")
            return (identity_matches and isinstance(commitment, str) and len(commitment) == 64
                    and all(char in "0123456789abcdef" for char in commitment)
                    and commitment == binding.fingerprint)
        return identity_matches

    def _dispatch(self, operation, intent: EffectIntent, *, deadline: datetime | None = None,
                  auth: AuthContext | None = None) -> DispatchResult:
        """Apply a trusted transport scope without changing saved provider identity."""
        intent = EffectIntent.model_validate(intent.model_dump())
        behavior = self._call(operation, "dispatch")
        reject = lambda reason: DispatchResult(status="rejected", reason=reason, evidence_refs=["synthetic-provider:dispatch"])
        if deadline is not None:
            try:
                if not isinstance(deadline, datetime) or deadline.utcoffset() is None or not math.isfinite(deadline.timestamp()):
                    return reject("invalid_deadline")
                deadline = deadline.astimezone(timezone.utc)
            except (ValueError, TypeError, OverflowError):
                return reject("invalid_deadline")
        if operation != intent.operation or operation not in _EFFECTS:
            return reject("unsupported_operation")
        capability = self._profile.capabilities.get(operation)
        if capability is None or capability.timeout_seconds is None:
            return reject("unsupported_guarantee")
        tool_deadline = min(intent.deadline, self._now() + timedelta(seconds=min(10, capability.timeout_seconds)))
        if deadline is not None:
            tool_deadline = min(tool_deadline, deadline)
        if self._now() >= tool_deadline:
            return reject("deadline_expired")
        reservation = self._reserve(operation, tool_deadline, behavior)
        if reservation is None:
            return reject("provider_unavailable")
        account, token = reservation
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                if self._now() >= tool_deadline:
                    return reject("deadline_expired")
                if not self._write_identity_allowed(connection, intent):
                    return reject("identity_scope_rejected")
                registered_transfer = operation == "transfer_owner" and self._ownership is not None
                if registered_transfer:
                    if not self._ownership.authenticated(connection, auth, intent.binding):
                        return reject("actor_scope_rejected")
                    try:
                        self._ownership.parse(intent)
                    except (ValueError, TypeError, KeyError):
                        return reject("ownership_contract_rejected")
                if self._now() >= tool_deadline:
                    return reject("deadline_expired")
                required = required_material_keys(connection, self._profile, operation, intent.stage)
                if required is None:
                    return reject("unsupported_guarantee")
                identity_hash = fingerprint(intent.model_dump(mode="json"))
                existing = connection.execute("SELECT identity_hash,request_id FROM effects WHERE account_id=? AND provider_key=?",
                                              (account, intent.provider_key)).fetchone()
                if existing:
                    if self._now() >= tool_deadline:
                        return reject("deadline_expired")
                    if existing["identity_hash"] != identity_hash:
                        return reject("idempotency_conflict")
                    return DispatchResult(status="acknowledged", provider_request_id=existing["request_id"],
                                          evidence_refs=["synthetic-provider:acknowledgement"])
                fenced = connection.execute("SELECT identity_hash FROM final_rejections WHERE account_id=? AND provider_key=?",
                                            (account, intent.provider_key)).fetchone()
                if fenced:
                    if self._now() >= tool_deadline:
                        return reject("deadline_expired")
                    return reject("terminally_rejected" if fenced[0] == identity_hash else "idempotency_conflict")
                expected = intent.expected_revisions.revisions
                if not required <= expected.keys():
                    return reject("missing_material_revision")
                current = read_material_revisions(connection, required, intent.binding.case_id, intent.binding.object_id)
                if current != {key: expected[key] for key in required}:
                    return reject("stale_material_revision")
                if registered_transfer and not self._ownership.current_allowed(connection, intent):
                    return reject("ownership_scope_rejected")
                if self._now() >= tool_deadline:
                    return reject("deadline_expired")
                if behavior in {"business_rejection", "final_rejection_unknown"}:
                    request_id = "provider:" + fingerprint({"account": account, "provider_key": intent.provider_key})[:24]
                    connection.execute("INSERT INTO final_rejections VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (account, intent.provider_key, intent.binding.case_id, intent.binding.object_id, operation,
                         intent.binding.generation, intent.action_id, intent.argument_fingerprint, identity_hash,
                         request_id, self._now().isoformat()))
                    if registered_transfer:
                        self._ownership.reject(connection, intent, request_id)
                    if self._now() >= tool_deadline:
                        connection.rollback()
                        return reject("deadline_expired")
                    if behavior == "final_rejection_unknown":
                        return DispatchResult(status="outcome_unknown", evidence_refs=["synthetic-provider:transport"])
                    return reject("business_rejected")
                if behavior == "timeout_before":
                    return DispatchResult(status="outcome_unknown", evidence_refs=["synthetic-provider:transport"])
                result = self._apply_declared_operation(connection, intent, behavior)
                if result is None:
                    return reject("provider_precondition_rejected")
                stage, values = result
                if self._now() >= tool_deadline:
                    connection.rollback()
                    return reject("deadline_expired")
                observations = self._effect_observations(connection, intent, values)
                request_id = "provider:" + fingerprint({"account": account, "provider_key": intent.provider_key})[:24]
                connection.execute("INSERT INTO effects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (account, intent.provider_key, intent.binding.case_id, intent.binding.object_id, operation,
                     intent.binding.generation, intent.action_id, intent.argument_fingerprint, identity_hash,
                     request_id, stage, json.dumps([o.model_dump(mode="json") for o in observations]),
                     self._now().isoformat(), intent.arguments.get("question_id"),
                     intent.arguments["intent"]["transfer_id"] if registered_transfer else intent.arguments.get("transfer_id"),
                     intent.arguments.get("packet_id"), intent.arguments.get("packet_revision")))
                if self._now() >= tool_deadline:
                    connection.rollback()
                    return reject("deadline_expired")
            return DispatchResult(status="outcome_unknown" if behavior == "timeout_after" else "acknowledged",
                                  provider_request_id=None if behavior == "timeout_after" else request_id,
                                  evidence_refs=["synthetic-provider:transport" if behavior == "timeout_after" else "synthetic-provider:acknowledgement"])
        except sqlite3.OperationalError:
            return DispatchResult(status="outcome_unknown", evidence_refs=["synthetic-provider:transport"])
        finally:
            self._release(account, token)

    def _apply_declared_operation(self, connection, intent, behavior):
        """One declared physical operation; no adapter calls or compensation."""
        case, obj = intent.binding.case_id, intent.binding.object_id
        facts = self._facts(connection, case, obj)
        values = {key: json.loads(row["value"]) for key, row in facts.items()}
        args, operation = intent.arguments, intent.operation
        if operation == "transfer_owner" and self._ownership is not None:
            return self._ownership.apply(connection, intent)
        requires_business_consent = not _scope_contract(self._profile) or operation in _BUSINESS_EFFECTS
        if ((requires_business_consent and values["customer.consent"] != "granted") or values["delivery.risk"] != "safe"
                or values["delivery.stage"] != "eligible" or values["policy.version"] != intent.policy_version
                or intent.profile_version != self._profile.version or intent.process_version != "v1"):
            return None
        if values["ownership.state"] != "accepted":
            return None
        if intent.ownership_state_revision is not None and intent.ownership_state_revision != values["ownership.state_revision"]:
            return None
        if intent.ownership_epoch is not None and intent.ownership_epoch != values["ownership.epoch"]:
            return None
        stage = "committed"
        if operation == "reschedule":
            slot = args.get("slot")
            if not isinstance(values["scheduling.capacity"], list) or slot not in values["scheduling.capacity"] or values["delivery.status"] != "scheduled":
                return None
            self._update(connection, case, obj, "scheduling.slot", slot)
            outcome = {"scheduling.slot": slot}
        elif operation in {"register_goods_refusal", "create_return"}:
            inventory = args.get("inventory")
            if (not isinstance(inventory, dict) or inventory != values["goods.inventory"] or not inventory
                    or any(type(quantity) is not int or quantity <= 0 for quantity in inventory.values())
                    or sum(inventory.values()) != values["goods.quantity"]):
                return None
            if operation == "register_goods_refusal":
                self._update(connection, case, obj, "goods.refusal", "verified")
                outcome = {"goods.refusal": "verified", "goods.inventory": inventory, "goods.quantity": values["goods.quantity"]}
            else:
                if values["goods.refusal"] != "verified" or args.get("destination") != values["returns.destination"]:
                    return None
                stage = "received" if behavior == "return_received" else "initiated"
                self._update(connection, case, obj, "returns.status", stage)
                outcome = {"returns.status": stage, "goods.inventory": inventory, "goods.quantity": values["goods.quantity"],
                           "returns.destination": values["returns.destination"]}
        elif operation == "register_service_refusal":
            if (args.get("scope") != "service" or
                    requires_completed_service(self._profile) and values.get("delivery.status") != "completed"):
                return None
            self._update(connection, case, obj, "service.refusal", "verified")
            outcome = {"service.refusal": "verified"}
        elif operation in {"send_clarification", "send_status"}:
            if values["messaging.permission"] != "granted" or args.get("recipient") != values["messaging.recipient"]:
                return None
            if not isinstance(args.get("text"), str) or not args["text"]:
                return None
            if operation == "send_clarification" and not isinstance(args.get("question_id"), str):
                return None
            stage = "delivered" if behavior == "delivered" else "sent"
            outcome = {"messaging.status": stage, "messaging.recipient": args["recipient"]}
            if operation == "send_clarification":
                outcome["messaging.question_id"] = args["question_id"]
        else:
            if args.get("packet_revision") != values["operator.packet_revision"] or args.get("packet_hash") != values["operator.packet_hash"] or not isinstance(args.get("packet_id"), str):
                return None
            if operation == "enqueue_handoff":
                if args.get("recipient") != values["operator.recipient"]:
                    return None
                if packet_enabled(self._profile):
                    try:
                        content = validate_packet_arguments(args, binding=intent.binding)
                        if intent.stage != "enqueue" or intent.postcondition != packet_postcondition(args):
                            return None
                        validate_packet_policy(content, self._profile, process_version=intent.process_version,
                                               policy_version=intent.policy_version)
                        catalog, access = validate_packet_scope(values.get("operator.packet_catalog"), values.get("operator.packet_access"),
                            case_id=case, object_id=obj, sender=intent.binding.principal_id,
                            recipient=values["operator.recipient"], now=self._now())
                        source = content.source
                        refs = {ref.identity: ref for ref in source.observations}
                        needed = PACKET_FIELDS | {"operator.packet_hash", "operator.packet_revision", "operator.recipient"}
                        if (content.catalog != catalog or content.access != access or content.as_of > self._now()
                                or self._now() >= content.expires_at or source.owner != values["ownership.owner"]
                                or source.owner_state != values["ownership.state"]
                                or source.state_revision != values["ownership.state_revision"] or source.epoch != values["ownership.epoch"]
                                or not needed <= refs.keys()
                                or any(key not in facts or ref.revision != facts[key]["revision"]
                                       or ref.evidence_ref != facts[key]["evidence_ref"] for key, ref in refs.items())):
                            return None
                    except (ValueError, TypeError, KeyError):
                        return None
                    receipt = PacketContentReceiptV1(packet_id=source.packet_id, packet_hash=source.packet_hash,
                        packet_revision=source.packet_revision, content_hash=args["content_hash"],
                        catalog_revision=catalog.revision, access_revision=access.revision, recipient=source.recipient,
                        generation=intent.binding.generation, action_id=intent.action_id, provider_key=intent.provider_key,
                        argument_fingerprint=intent.argument_fingerprint, owner=source.owner, state_revision=source.state_revision,
                        epoch=source.epoch, stored_at=self._now(), evidence_ref="synthetic-provider:effect:" + intent.action_id,
                        content_status="stored", owner_status="pending")
                    return "queued", {"operator.handoff_disposition": "pending", "operator.packet_id": source.packet_id,
                        "operator.packet_revision": source.packet_revision, "operator.packet_hash": source.packet_hash,
                        "operator.packet_content": content.model_dump(mode="json"),
                        "operator.packet_content_receipt": receipt.model_dump(mode="json")}
                stage = "queued"
                outcome = {"operator.handoff_disposition": "pending", "operator.packet_id": args["packet_id"],
                           "operator.packet_revision": args["packet_revision"], "operator.packet_hash": args["packet_hash"]}
            else:
                if not isinstance(args.get("transfer_id"), str) or not isinstance(args.get("target_owner"), str):
                    return None
                scope = connection.execute("SELECT readers FROM scopes WHERE case_id=? AND object_id=?", (case, obj)).fetchone()
                if args["target_owner"] not in json.loads(scope[0]) or args["target_owner"] == values["ownership.owner"]:
                    return None
                stage = "accepted" if behavior == "owner_accepted" else "pending"
                self._update(connection, case, obj, "ownership.state", stage)
                state_revision = self._update(connection, case, obj, "ownership.state_revision", "pending")
                connection.execute("UPDATE facts SET value=? WHERE case_id=? AND object_id=? AND identity='ownership.state_revision'",
                                   (json.dumps(state_revision), case, obj))
                if stage == "accepted":
                    self._update(connection, case, obj, "ownership.owner", args["target_owner"])
                    self._update(connection, case, obj, "ownership.epoch", values["ownership.epoch"] + 1)
                outcome = {"ownership.state": stage, "ownership.state_revision": state_revision,
                           "ownership.owner": args["target_owner"] if stage == "accepted" else values["ownership.owner"],
                           "ownership.epoch": values["ownership.epoch"] + (stage == "accepted"),
                           "operator.transfer_id": args["transfer_id"], "operator.packet_id": args["packet_id"],
                           "operator.packet_revision": args["packet_revision"]}
        return stage, outcome

    def _effect_observations(self, connection, intent, values):
        facts = self._facts(connection, intent.binding.case_id, intent.binding.object_id)
        receipt = values.get("operator.packet_content_receipt")
        # The original receipt and its evidence describe one provider event.
        # This receipt was generated above by the provider, never supplied in
        # caller arguments; sampling again would create a distinct event time.
        transfer = values.get("operator.transfer_receipt")
        now = (PacketContentReceiptV1.model_validate(receipt).stored_at if receipt is not None else
               datetime.fromisoformat(transfer.get("accepted_at") or transfer.get("pending_at") or transfer["rejected_at"])
               if transfer is not None else self._now())
        return [AuthorityObservation(authority=key.partition(".")[0], fact=key.partition(".")[2],
                object_id=intent.binding.object_id, value=value, revision=facts[key]["revision"] if key in facts else "v1",
                provider_at=now, observed_at=now, evidence_ref="synthetic-provider:effect:" + intent.action_id)
                for key, value in values.items()]

    def _read(self, operation, request: ReadRequest) -> AuthorityReadback:
        request = ReadRequest.model_validate(request.model_dump())
        behavior = self._call(operation, request.purpose)
        empty = lambda stage="unavailable": AuthorityReadback(operation=operation, object_id=request.object_id,
                         observations=[], stage=stage, as_of=self._now(), evidence_refs=[])
        target = request.target
        capability_name = target.operation if target.kind == "original_effect" else "read_authority"
        capability = self._profile.capabilities.get(capability_name)
        if (capability is None or capability.readback.status != "supported" or capability.permission_basis.status != "supported"
                or capability.timeout_seconds is None):
            return empty()
        tool_deadline = min(request.deadline, self._now() + timedelta(seconds=min(10, capability.timeout_seconds)))
        reservation = self._reserve(capability_name, tool_deadline, behavior)
        if reservation is None:
            return empty()
        account, token = reservation
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                if self._now() >= tool_deadline:
                    return empty()
                scope = connection.execute("SELECT readers FROM scopes WHERE case_id=? AND object_id=?", (request.case_id, request.object_id)).fetchone()
                if not scope or json.loads(scope[0]).get(request.caller_id) != request.proof_reference:
                    return empty("scope_rejected")
                if behavior in {"timeout_before", "timeout_after", "business_rejection"}:
                    return empty()
                observations, record = [], None
                if target.kind == "authority_facts":
                    allowed = _FACT_SCOPES.get(operation, {}).get(target.authority, set())
                    if packet_enabled(self._profile) and operation == "read_receipt" and target.authority == "operator":
                        allowed = allowed | {"packet_catalog", "packet_access"}
                    if self._ownership and operation == "read_owner" and target.authority == "operator":
                        allowed = allowed | {"ownership_grant", "ownership_packet", "packet_hash", "packet_revision"}
                    if not set(target.facts) <= allowed:
                        return empty("scope_rejected")
                    if any(target.authority + "." + fact in _NEW_FACTS
                           and self._profile.authorities.get(target.authority + "." + fact) != target.authority
                           for fact in target.facts):
                        return empty("scope_rejected")
                    facts = self._facts(connection, request.case_id, request.object_id)
                    if (target.authority == "operator" and "ownership_grant" in target.facts
                            and not self._ownership.disclosure_allowed(facts, request)):
                        return empty("scope_rejected")
                    if (target.authority == "operator" and {"packet_catalog", "packet_access"} & set(target.facts)
                            and not self._packet_disclosure_allowed(facts, request)):
                        return empty("scope_rejected")
                    for fact in target.facts:
                        row = facts.get(target.authority + "." + fact)
                        if row is None:
                            return empty("unknown")
                        observations.append(AuthorityObservation(authority=target.authority, fact=fact, object_id=request.object_id,
                            value=json.loads(row["value"]), revision=row["revision"], provider_at=self._now(), observed_at=self._now(), evidence_ref=row["evidence_ref"]))
                else:
                    where, params = "account_id=? AND case_id=? AND object_id=?", [account, request.case_id, request.object_id]
                    if target.kind == "original_effect":
                        if target.operation not in _ORIGINAL_SCOPES.get(operation, set()):
                            return empty("scope_rejected")
                        where += " AND operation=? AND generation=? AND action_id=? AND provider_key=? AND fingerprint=?"
                        params += [target.operation, target.generation, target.action_id, target.provider_key, target.fingerprint]
                    elif target.kind == "question" and operation == "read_message":
                        where += " AND operation='send_clarification' AND question_id=?"
                        params += [target.question_id]
                    elif ((target.kind == "operator_packet" and operation in {"read_receipt", "read_resume"})
                          or (target.kind == "transfer" and operation in {"read_resume", "read_owner"})):
                        if target.kind == "transfer" and self._ownership is not None:
                            return empty("scope_rejected")
                        where += " AND packet_id=? AND packet_revision=?"
                        params += [target.packet_id, target.packet_revision]
                        if target.kind == "transfer":
                            where += " AND operation='transfer_owner' AND transfer_id=?"
                            params += [target.transfer_id]
                        else:
                            where += " AND operation='enqueue_handoff'"
                    else:
                        return empty("scope_rejected")
                    records = connection.execute("SELECT * FROM effects WHERE " + where, params).fetchall()
                    if target.kind == "original_effect" and not records and behavior == "terminal_not_executed":
                        rejections = connection.execute("SELECT * FROM final_rejections WHERE " + where, params).fetchall()
                        terminal = self._profile.capabilities[target.operation].terminal_nonexecution_basis
                        if len(rejections) == 1 and terminal.status == "supported":
                            as_of = self._now()
                            if as_of >= tool_deadline:
                                return empty()
                            record = rejections[0]
                            evidence = "synthetic-provider:terminal-rejection:" + record["request_id"]
                            terminal_observations = []
                            if self._ownership and target.operation == "transfer_owner" and operation == "read_owner":
                                try:
                                    original = OriginalTransferIdentityV1(binding=self._ownership.fixture.packet.binding,
                                        transfer_id=target.action_id, action_id=target.action_id, provider_key=target.provider_key,
                                        argument_fingerprint=target.fingerprint)
                                    saved = self._ownership.load(connection, original)
                                except (ValueError, KeyError, TypeError):
                                    return empty("unknown")
                                if not saved or not isinstance(saved.receipt, TransferRejectedV1):
                                    return empty("unknown")
                                terminal_observations = self._effect_observations(connection, saved.effect,
                                    self._ownership.outcome(saved.receipt))
                                terminal_observations = [AuthorityObservation.model_validate({**obs.model_dump(), "observed_at": as_of})
                                                         for obs in terminal_observations]
                            return AuthorityReadback(operation=record["operation"], object_id=request.object_id, observations=terminal_observations,
                                provider_request_id=record["request_id"], action_id=record["action_id"], fingerprint=record["fingerprint"],
                                stage="terminally_rejected", nonexecution=NonexecutionProof(status="proven", basis=terminal.basis,
                                                                                          evidence_ref=evidence),
                                as_of=as_of, evidence_refs=[evidence])
                    # A reusable business ID is ambiguous, never resolved by latest.
                    if len(records) != 1:
                        return empty("unknown")
                    record = records[0]
                    if self._ownership and record["operation"] == "transfer_owner":
                        try:
                            original = OriginalTransferIdentityV1(binding=self._ownership.fixture.packet.binding,
                                transfer_id=record["action_id"], action_id=record["action_id"],
                                provider_key=record["provider_key"], argument_fingerprint=record["fingerprint"])
                            if self._ownership.load(connection, original) is None:
                                return empty("unknown")
                        except (ValueError, KeyError, TypeError):
                            return empty("unknown")
                    capability = self._profile.capabilities.get(record["operation"])
                    if not capability or capability.readback.status != "supported":
                        return empty("unavailable")
                    observations = [AuthorityObservation.model_validate({**item, "observed_at": self._now()})
                                    for item in json.loads(record["observations"])]
                    if any(obs.authority == "operator" and obs.fact == "transfer_receipt" for obs in observations):
                        if (self._ownership is None or operation != "read_owner" or target.kind != "original_effect"
                                or target.operation != "transfer_owner"):
                            return empty("scope_rejected")
                    content_bearing = any(obs.authority == "operator" and obs.fact in
                                          {"packet_content", "packet_content_receipt"} for obs in observations)
                    # Disclosure follows the stored provider-owned outcome,
                    # not a later profile selection when reopening this DB.
                    # Genuine legacy metadata-only rows retain their semantics.
                    if record["operation"] == "enqueue_handoff" and content_bearing:
                        facts = self._facts(connection, request.case_id, request.object_id)
                        if not self._packet_disclosure_allowed(facts, request, original=True):
                            return empty("scope_rejected")
                        # Full private contents remain in the immutable outcome. Public
                        # original verification initially exposes digest/receipt only.
                        observations = [obs for obs in observations if obs.fact != "packet_content"]
                object_id = "provider-other-object" if behavior == "wrong_object" else request.object_id
                if behavior == "wrong_object":
                    observations = [AuthorityObservation.model_validate({**obs.model_dump(), "object_id": object_id}) for obs in observations]
                if self._now() >= tool_deadline:
                    return empty()
                return AuthorityReadback(operation=record["operation"] if record else operation, object_id=object_id,
                    observations=observations, provider_request_id=record["request_id"] if record else None,
                    action_id=record["action_id"] if record else None, fingerprint=record["fingerprint"] if record else None,
                    stage=record["stage"] if record else "observed", nonexecution=NonexecutionProof(),
                    as_of=self._now(), evidence_refs=["synthetic-provider:readback"])
        except sqlite3.OperationalError:
            return empty()
        finally:
            self._release(account, token)

    def _packet_disclosure_allowed(self, facts, request, *, original=False):
        try:
            if not original and request.purpose != "operator_packet":
                return False
            values = {key: json.loads(row["value"]) for key, row in facts.items()}
            validate_packet_scope(values.get("operator.packet_catalog"), values.get("operator.packet_access"),
                case_id=request.case_id, object_id=request.object_id, sender=request.caller_id,
                recipient=values.get("operator.recipient"), now=self._now())
            # Decision/catalog revisions identify their typed source snapshots;
            # observation revisions fence current facts and need not be equal.
            return True
        except (ValueError, TypeError, KeyError):
            return False
