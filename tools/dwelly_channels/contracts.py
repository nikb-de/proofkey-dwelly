"""Strict, offline normalization contracts for untrusted communication content."""
import base64
import binascii
from copy import deepcopy
from datetime import datetime, timezone
from email import errors, policy
from email.message import EmailMessage
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import quopri
import re

from tools.dwelly_platform.media import _validated_asset
from tools.dwelly_platform.store import PlatformStore

MAX_ENVELOPE_BYTES = 40 * 1024 * 1024
NORMALIZER_VERSION = "proofkey-channel-normalizer-v1"
MAX_EMAIL_BYTES = 26 * 1024 * 1024
ERROR_CODES = frozenset({"invalid_channel_config", "invalid_envelope", "invalid_identity", "invalid_channel",
    "unsupported_format", "channel_format_mismatch", "invalid_message", "invalid_timestamp", "invalid_base64",
    "envelope_too_large", "email_too_large", "invalid_email", "unsupported_email_part", "email_limits_exceeded",
    "invalid_media", "media_validator_unavailable"})
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_CHANNELS = {"email", "chat", "phone"}
_ENVELOPE_FIELDS = {"schema_version", "delivery_id", "conversation_id", "format", "payload"}
_MESSAGE_FIELDS = {"sender", "recipients", "occurred_at", "text"}
_MEDIA_FIELDS = {"sender", "recipients", "occurred_at", "kind", "filename", "mime_type", "data_base64"}
_IMAGE = {"image/png", "image/jpeg"}
_AUDIO = {"audio/mpeg", "audio/wav", "audio/mp4", "audio/webm"}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _identity(value):
    _require(type(value) is str and 1 <= len(value) <= 256 and bool(value.strip())
             and all(ord(char) >= 32 and ord(char) != 127 for char in value), "invalid_identity")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError("invalid_identity") from None
    return value


def _exact(value, keys, code):
    _require(type(value) is dict and set(value) == keys, code)


def _json_bytes(value, code):
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError(code) from None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_channel_config")
        result[key] = value
    return result


def load_config(value):
    """Validate mappings only; never read the named secret environment variables."""
    try:
        if isinstance(value, (str, Path)):
            with Path(value).open("rb") as handle:
                raw = handle.read(512 * 1024 + 1)
            _require(len(raw) <= 512 * 1024, "invalid_channel_config")
            value = json.loads(raw, object_pairs_hook=_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid_channel_config")))
        _exact(value, {"schema_version", "connectors"}, "invalid_channel_config")
        _require(value["schema_version"] == "proofkey-channel-config-v1", "invalid_channel_config")
        connectors = value["connectors"]
        _require(type(connectors) is list and len(connectors) <= 32, "invalid_channel_config")
        seen = set()
        for connector in connectors:
            _exact(connector, {"id", "channel", "secret_env", "routes", "contacts"}, "invalid_channel_config")
            _require(type(connector["id"]) is str and _IDENTIFIER.fullmatch(connector["id"])
                     and connector["id"] not in seen, "invalid_channel_config")
            seen.add(connector["id"])
            _require(connector["channel"] in _CHANNELS, "invalid_channel_config")
            _require(type(connector["secret_env"]) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", connector["secret_env"]),
                     "invalid_channel_config")
            for field in ("routes", "contacts"):
                mapping = connector[field]
                _require(type(mapping) is dict and len(mapping) <= 256, "invalid_channel_config")
                for source, target in mapping.items():
                    _identity(source)
                    _require(type(target) is str and _IDENTIFIER.fullmatch(target), "invalid_channel_config")
        _require(len(_json_bytes(value, "invalid_channel_config")) <= 512 * 1024, "invalid_channel_config")
        return deepcopy(value)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise ValueError("invalid_channel_config") from None


def validate_envelope_identity(envelope):
    """Bound raw retention before trusting IDs; leave payload rejection to normalize."""
    _exact(envelope, _ENVELOPE_FIELDS, "invalid_envelope")
    _require(envelope["schema_version"] == "proofkey-inbound-v1", "invalid_envelope")
    _require(len(_json_bytes(envelope, "invalid_envelope")) <= MAX_ENVELOPE_BYTES, "envelope_too_large")
    return {key: _identity(envelope[key]) for key in ("delivery_id", "conversation_id")}


def _timestamp(value):
    _require(type(value) is str and 1 <= len(value) <= 64, "invalid_timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(stamp.tzinfo is not None and stamp.utcoffset() is not None, "invalid_timestamp")
        return stamp.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        raise ValueError("invalid_timestamp") from None


def _text(value):
    _require(type(value) is str and bool(value.strip()) and len(value) <= 4096
             and not any(ord(char) < 32 and char not in "\r\n\t" for char in value) and "\x7f" not in value,
             "invalid_message")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError("invalid_message") from None
    return value


def _participants(payload):
    sender = _identity(payload["sender"])
    recipients = payload["recipients"]
    _require(type(recipients) is list and 1 <= len(recipients) <= 16, "invalid_message")
    recipients = [_identity(item) for item in recipients]
    _require(len(set(recipients)) == len(recipients), "invalid_message")
    return {"sender": sender, "recipients": recipients, "occurred_at": _timestamp(payload["occurred_at"])}


def _decode64(value):
    _require(type(value) is str and bool(value), "invalid_base64")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error, UnicodeError):
        raise ValueError("invalid_base64") from None


def _asset(kind, filename, mime, data, channel):
    _require(type(kind) is str and type(mime) is str, "invalid_media")
    _require((kind == "photo" and mime in _IMAGE and channel in {"chat", "email"})
             or (kind in {"voice_message", "call_recording"} and mime in _AUDIO and channel in {"phone", "chat"}),
             "channel_format_mismatch")
    _require(type(filename) is str and 1 <= len(filename) <= 256 and not any(ord(c) < 32 for c in filename), "invalid_media")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename.replace("\\", "/").split("/")[-1])[:128].strip(".") or "attachment"
    try:
        PlatformStore._validate_asset(mime, safe, data)
        _validated_asset(data, mime, "image_analysis" if kind == "photo" else "asr")
    except ValueError as error:
        if error.args and error.args[0] == "media_validator_unavailable":
            raise ValueError("media_validator_unavailable") from None
        raise ValueError("invalid_media") from None
    return {"filename": safe, "mime_type": mime, "data": data}


def _decoded_part(part):
    """Decode transfer encodings strictly; email's permissive recovery is not admission."""
    payload = part.get_payload()
    _require(type(payload) is str, "invalid_email")
    try:
        raw = payload.encode("ascii", "surrogateescape")
    except UnicodeError:
        raise ValueError("invalid_email") from None
    encoding = str(part.get("Content-Transfer-Encoding", "7bit")).strip().lower()
    try:
        if encoding == "base64":
            data = base64.b64decode(re.sub(rb"[\r\n\t ]", b"", raw), validate=True)
        elif encoding == "quoted-printable":
            _require(re.search(rb"=(?![0-9A-Fa-f]{2}|\r?\n)", raw) is None, "invalid_email")
            data = quopri.decodestring(raw)
        elif encoding in {"7bit", "8bit", "binary"}:
            _require(encoding != "7bit" or all(char < 128 for char in raw), "invalid_email")
            data = raw
        else:
            raise ValueError("invalid_email")
    except (binascii.Error, UnicodeError):
        raise ValueError("invalid_email") from None
    _require(len(data) <= MAX_EMAIL_BYTES, "email_too_large")
    return data


def _email(raw, channel):
    _require(len(raw) <= MAX_EMAIL_BYTES, "email_too_large")
    _require(bool(raw) and b"\x00" not in raw, "invalid_email")
    count = 0
    def factory(policy=None):
        nonlocal count
        count += 1
        _require(count <= 32, "email_limits_exceeded")
        return EmailMessage(policy=policy)
    try:
        message = BytesParser(_class=factory, policy=policy.default.clone(raise_on_defect=True)).parsebytes(raw)
    except ValueError as error:
        if error.args and error.args[0] in ERROR_CODES:
            raise
        raise ValueError("invalid_email") from None
    except (errors.MessageError, errors.MessageDefect, RecursionError, UnicodeError, TypeError):
        raise ValueError("invalid_email") from None
    for key in ("From", "To", "Cc", "Bcc", "Date", "Message-ID", "Subject"):
        _require(len(message.get_all(key, [])) <= 1, "invalid_email")
    try:
        senders = message["From"].addresses
        recipients = [address for key in ("To", "Cc", "Bcc") for header in message.get_all(key, []) for address in header.addresses]
        _require(len(senders) == 1 and 1 <= len(recipients) <= 16, "invalid_email")
        _require(all(address.username and address.domain for address in [*senders, *recipients]), "invalid_email")
        when = message["Date"].datetime
        _require(when is not None and when.tzinfo is not None, "invalid_email")
        participants = _participants({"sender": senders[0].addr_spec,
            "recipients": [address.addr_spec for address in recipients], "occurred_at": when.isoformat()})
    except (AttributeError, KeyError, TypeError, ValueError, IndexError, OverflowError):
        raise ValueError("invalid_email") from None
    bodies, assets, ignored_html = [], [], 0
    stack = [(message, 1, False)]
    while stack:
        part, depth, alternative = stack.pop()
        _require(depth <= 8, "email_limits_exceeded")
        _require(not part.defects, "invalid_email")
        for key, header in part.items():
            _require(not getattr(header, "defects", ()), "invalid_email")
        for key in ("Content-Type", "Content-Transfer-Encoding", "Content-Disposition"):
            _require(len(part.get_all(key, [])) <= 1, "invalid_email")
        mime = part.get_content_type()
        _require(mime != "message/rfc822", "unsupported_email_part")
        if part.is_multipart():
            _require(mime in {"multipart/mixed", "multipart/alternative", "multipart/related"}, "unsupported_email_part")
            children = part.get_payload()
            _require(type(children) is list and bool(children), "invalid_email")
            stack.extend((child, depth + 1, alternative or mime == "multipart/alternative") for child in reversed(children))
            continue
        filename = part.get_filename()
        attachment = part.get_content_disposition() == "attachment" or filename is not None
        if mime == "text/html" and alternative and not attachment:
            # Ignored representations still must be well-formed; they are
            # decoded only for validation, never rendered or fetched.
            try:
                _decoded_part(part).decode(part.get_content_charset() or "ascii", errors="strict")
            except (LookupError, UnicodeError):
                raise ValueError("invalid_email") from None
            ignored_html += 1
            continue
        data = _decoded_part(part)
        if mime == "text/plain" and not attachment:
            try:
                bodies.append(_text(data.decode(part.get_content_charset() or "ascii", errors="strict")))
            except (LookupError, UnicodeError):
                raise ValueError("invalid_email") from None
        else:
            _require(mime in _IMAGE | _AUDIO, "unsupported_email_part")
            _require(len(assets) < 16, "email_limits_exceeded")
            kind = "photo" if mime in _IMAGE else "voice_message"
            asset = _asset(kind, filename or "attachment", mime, data, channel)
            assets.append({**participants, "kind": kind, "text": None, "asset": asset})
    _require(len(bodies) <= 1 and bool(bodies or assets), "invalid_email")
    _require(not ignored_html or bool(bodies), "unsupported_email_part")
    events = ([{**participants, "kind": "message", "text": bodies[0], "asset": None}] if bodies else []) + assets
    provenance = {"raw_sha256": hashlib.sha256(raw).hexdigest(), "ignored_html_alternatives": ignored_html,
                  "claimed_headers": {key.lower(): str(message[key]) for key in ("From", "To", "Cc", "Date", "Subject", "Message-ID") if key in message}}
    return events, provenance


def normalize(envelope, channel):
    """Produce untrusted drafts only: no case lookup, DB write, fetch, ASR or model call."""
    validate_envelope_identity(envelope)
    _require(type(channel) is str and channel in _CHANNELS, "invalid_channel")
    fmt, payload = envelope["format"], envelope["payload"]
    _require(type(fmt) is str and fmt in {"message", "transcript", "media", "email"}, "unsupported_format")
    provenance = {"normalizer_version": NORMALIZER_VERSION, "format": fmt,
                  "identity_verification": "not_verified", "qualification": "untrusted_source_claims"}
    if fmt == "email":
        _require(channel == "email", "channel_format_mismatch")
        _exact(payload, {"raw_base64"}, "invalid_email")
        events, email_provenance = _email(_decode64(payload["raw_base64"]), channel)
        provenance.update(email_provenance)
    elif fmt in {"message", "transcript"}:
        _require(fmt != "transcript" or channel == "phone", "channel_format_mismatch")
        _exact(payload, _MESSAGE_FIELDS, "invalid_message")
        events = [{**_participants(payload), "kind": "message", "text": _text(payload["text"]), "asset": None}]
        if fmt == "transcript":
            provenance["transcript_verification"] = "supplied_transcript_unverified"
    else:
        _exact(payload, _MEDIA_FIELDS, "invalid_media")
        participants = _participants(payload)
        asset = _asset(payload["kind"], payload["filename"], payload["mime_type"], _decode64(payload["data_base64"]), channel)
        events = [{**participants, "kind": payload["kind"], "text": None, "asset": asset}]
        if payload["mime_type"] in _AUDIO:
            provenance["transcript_verification"] = "not_transcribed"
    provenance.update(event_count=len(events), attachment_count=sum(event["asset"] is not None for event in events))
    return {"events": events, "provenance": provenance}
