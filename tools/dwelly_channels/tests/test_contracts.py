"""Offline normalization contracts; source claims never become routing authority."""
import base64
from copy import deepcopy
import importlib
import io
import json
from pathlib import Path
import shutil
import wave

import pytest


@pytest.fixture
def contracts():
    return importlib.import_module("tools.dwelly_channels.contracts")


def config():
    return {"schema_version": "proofkey-channel-config-v1", "connectors": [{
        "id": "mailbox", "channel": "email", "secret_env": "MAIL_HMAC_SECRET",
        "routes": {"thread@example.test": "case-1"}, "contacts": {"sender@example.test": "customer"}}]}


def envelope(fmt="message", payload=None):
    return {"schema_version": "proofkey-inbound-v1", "delivery_id": "external-1", "conversation_id": "thread@example.test",
            "format": fmt, "payload": payload if payload is not None else {
                "sender": "sender@example.test", "recipients": ["operator@example.test"],
                "occurred_at": "2026-10-10T11:00:00+02:00", "text": "Original text — unchanged."}}


def email_envelope(raw):
    return envelope("email", {"raw_base64": base64.b64encode(raw).decode("ascii")})


def mail(body=b"Plain source text.\r\n", extra=b"", content_type=b"text/plain; charset=utf-8"):
    return (b"From: Sender <sender@example.test>\r\nTo: Operator <operator@example.test>\r\n"
            b"Date: Sat, 10 Oct 2026 09:00:00 +0000\r\nMessage-ID: <source-1@example.test>\r\n"
            b"Subject: Original subject\r\nMIME-Version: 1.0\r\nContent-Type: " + content_type + b"\r\n" + extra + b"\r\n" + body)


def multipart(parts, subtype="mixed"):
    body = b"".join(b"--boundary\r\n" + part + b"\r\n" for part in parts) + b"--boundary--\r\n"
    return mail(body, content_type=f'multipart/{subtype}; boundary="boundary"'.encode())


def png():
    from PIL import Image
    data = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(data, format="PNG")
    return data.getvalue()


def audio():
    data = io.BytesIO()
    with wave.open(data, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 800)
    return data.getvalue()


def media(kind="photo", mime="image/png", data=None):
    return envelope("media", {"sender": "sender@example.test", "recipients": ["operator@example.test"],
        "occurred_at": "2026-10-10T09:00:00Z", "kind": kind, "filename": "../../unsafe.png", "mime_type": mime,
        "data_base64": base64.b64encode(png() if data is None else data).decode()})


def test_config_accepts_only_operator_mapping_and_returns_detached_copy(contracts):
    supplied = config()
    validated = contracts.load_config(supplied)
    assert validated == supplied
    supplied["connectors"][0]["routes"].clear()
    assert validated["connectors"][0]["routes"] == {"thread@example.test": "case-1"}


def test_config_reads_strict_json_path(contracts, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config()))
    assert contracts.load_config(path) == config()
    path.write_text('{"schema_version":"proofkey-channel-config-v1","connectors":[],"connectors":[]}')
    with pytest.raises(ValueError, match="^invalid_channel_config$"):
        contracts.load_config(str(path))


@pytest.mark.parametrize("change", [
    lambda c: c.update(secret="must-not-accept"),
    lambda c: c["connectors"][0].update(secret="must-not-accept"),
    lambda c: c["connectors"].append(deepcopy(c["connectors"][0])),
    lambda c: c["connectors"][0].update(channel="sms"),
    lambda c: c["connectors"][0].update(secret_env="bad\nname"),
    lambda c: c["connectors"][0].update(routes={"thread": "../case"}),
    lambda c: c["connectors"][0].update(contacts={"sender": "unknown actor"}),
    lambda c: c["connectors"][0].update(routes=[]),
])
def test_config_rejects_unsafe_or_unknown_fields(contracts, change):
    supplied = config()
    change(supplied)
    with pytest.raises(ValueError, match="^invalid_channel_config$"):
        contracts.load_config(supplied)


def test_envelope_identity_is_validated_without_accepting_payload_claims(contracts):
    supplied = envelope(payload={"case_id": "forged", "anything": True})
    assert contracts.validate_envelope_identity(supplied) == {
        "delivery_id": "external-1", "conversation_id": "thread@example.test"}
    with pytest.raises(ValueError, match="^invalid_message$"):
        contracts.normalize(supplied, "chat")


def test_message_preserves_text_and_claimed_contacts_but_not_authority(contracts):
    supplied = envelope()
    result = contracts.normalize(supplied, "chat")
    assert result["events"] == [{"sender": "sender@example.test", "recipients": ["operator@example.test"],
        "occurred_at": "2026-10-10T09:00:00+00:00", "kind": "message", "text": "Original text — unchanged.", "asset": None}]
    assert result["provenance"]["identity_verification"] == "not_verified"
    assert result["provenance"]["normalizer_version"] == contracts.NORMALIZER_VERSION
    assert "case_id" not in result


def test_supplied_transcript_is_explicitly_unverified(contracts):
    result = contracts.normalize(envelope("transcript"), "phone")
    assert result["events"][0]["kind"] == "message"
    assert result["provenance"]["transcript_verification"] == "supplied_transcript_unverified"
    with pytest.raises(ValueError, match="^channel_format_mismatch$"):
        contracts.normalize(envelope("transcript"), "chat")


@pytest.mark.parametrize("changed,code", [
    ({"schema_version": "wrong"}, "invalid_envelope"),
    ({"case_id": "forged"}, "invalid_envelope"),
    ({"format": "url"}, "unsupported_format"),
    ({"delivery_id": ""}, "invalid_identity"),
    ({"conversation_id": "a\nforged"}, "invalid_identity"),
    ({"delivery_id": "a" * 257}, "invalid_identity"),
])
def test_top_level_validation_is_bounded(contracts, changed, code):
    supplied = envelope()
    supplied.update(changed)
    with pytest.raises(ValueError, match=f"^{code}$"):
        contracts.normalize(supplied, "chat")


@pytest.mark.parametrize("changed,code", [
    ({"sender": ""}, "invalid_identity"), ({"recipients": []}, "invalid_message"),
    ({"recipients": ["same", "same"]}, "invalid_message"),
    ({"occurred_at": "2026-10-10T09:00:00"}, "invalid_timestamp"),
    ({"occurred_at": "not-a-date"}, "invalid_timestamp"),
    ({"text": "x" * 4097}, "invalid_message"), ({"text": " \n"}, "invalid_message"),
    ({"text": "embedded\x00null"}, "invalid_message"),
    ({"sender_id": "forged"}, "invalid_message"),
])
def test_message_invalid_fields_are_never_truncated_or_trusted(contracts, changed, code):
    supplied = envelope()
    supplied["payload"].update(changed)
    with pytest.raises(ValueError, match=f"^{code}$"):
        contracts.normalize(supplied, "chat")


def test_oversized_envelope_is_rejected_before_normalization(contracts):
    supplied = envelope(payload={"text": "x" * (contracts.MAX_ENVELOPE_BYTES + 1)})
    with pytest.raises(ValueError, match="^envelope_too_large$"):
        contracts.normalize(supplied, "chat")


def test_email_claims_and_plain_text_are_preserved(contracts):
    raw = mail()
    result = contracts.normalize(email_envelope(raw), "email")
    assert result["events"] == [{"sender": "sender@example.test", "recipients": ["operator@example.test"],
        "occurred_at": "2026-10-10T09:00:00+00:00", "kind": "message", "text": "Plain source text.\r\n", "asset": None}]
    assert result["provenance"]["claimed_headers"]["message-id"] == "<source-1@example.test>"
    assert result["provenance"]["identity_verification"] == "not_verified"


def test_email_alternative_prefers_plain_without_fetching_html_urls(contracts, monkeypatch):
    import socket
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("network use forbidden"))
    raw = multipart([b"Content-Type: text/plain; charset=utf-8\r\n\r\nOriginal plain.",
                     b"Content-Type: text/html\r\n\r\n<img src='https://example.test/private'>"], "alternative")
    result = contracts.normalize(email_envelope(raw), "email")
    assert [event["text"] for event in result["events"]] == ["Original plain."]
    assert result["provenance"]["ignored_html_alternatives"] == 1


def test_ignored_html_alternative_must_still_have_valid_encoding(contracts):
    raw = multipart([b"Content-Type: text/plain; charset=utf-8\r\n\r\nOriginal plain.",
        b"Content-Type: text/html\r\nContent-Transfer-Encoding: base64\r\n\r\nnot@@base64"], "alternative")
    with pytest.raises(ValueError, match="^invalid_email$"):
        contracts.normalize(email_envelope(raw), "email")


@pytest.mark.parametrize("change", [lambda value: value.update(channel=[]),
    lambda value: value.update(routes={"x": []}), lambda value: value.update(contacts={"x": True})])
def test_nested_malformed_config_returns_plain_bounded_error(contracts, change):
    value = config()
    change(value["connectors"][0])
    with pytest.raises(ValueError, match="^invalid_channel_config$") as caught:
        contracts.load_config(value)
    assert type(caught.value) is ValueError


def test_identity_rejects_nonjson_payload_before_storage(contracts):
    value = envelope(payload={"bad": float("nan")})
    with pytest.raises(ValueError, match="^invalid_envelope$"):
        contracts.validate_envelope_identity(value)


def test_email_raw_size_limit_is_separate_from_envelope_limit(contracts):
    raw = b"x" * (26 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="^email_too_large$"):
        contracts.normalize(email_envelope(raw), "email")


@pytest.mark.parametrize("raw,code", [
    (mail(content_type=b"text/html"), "unsupported_email_part"),
    (mail(body=mail(), content_type=b"message/rfc822"), "unsupported_email_part"),
    (mail(content_type=b"application/zip"), "unsupported_email_part"),
    (mail(extra=b"From: other@example.test\r\n"), "invalid_email"),
    (mail().replace(b"Date: Sat, 10 Oct 2026 09:00:00 +0000\r\n", b""), "invalid_email"),
    (mail().replace(b"To: Operator <operator@example.test>\r\n", b""), "invalid_email"),
    (mail(body=b"SGVsbG8@@", extra=b"Content-Transfer-Encoding: base64\r\n"), "invalid_email"),
    (mail(body=b"invalid=QX", extra=b"Content-Transfer-Encoding: quoted-printable\r\n"), "invalid_email"),
    (mail(content_type=b"text/plain; charset=does-not-exist"), "invalid_email"),
    (mail(body=b"x" * 4097), "invalid_message"),
])
def test_email_unsafe_or_ambiguous_content_is_rejected(contracts, raw, code):
    with pytest.raises(ValueError, match=f"^{code}$"):
        contracts.normalize(email_envelope(raw), "email")


def test_email_ambiguous_multiple_plain_bodies_are_rejected(contracts):
    raw = multipart([b"Content-Type: text/plain\r\n\r\none", b"Content-Type: text/plain\r\n\r\ntwo"])
    with pytest.raises(ValueError, match="^invalid_email$"):
        contracts.normalize(email_envelope(raw), "email")


def test_email_part_and_depth_limits_fail_closed(contracts):
    raw = multipart([b"Content-Type: text/plain\r\n\r\npart"] * 33)
    with pytest.raises(ValueError, match="^email_limits_exceeded$"):
        contracts.normalize(email_envelope(raw), "email")
    part = b"Content-Type: text/plain\r\n\r\nleaf"
    for depth in range(9):
        boundary = f"b{depth}".encode()
        part = (b"Content-Type: multipart/mixed; boundary=" + boundary + b"\r\n\r\n--" + boundary + b"\r\n" +
                part + b"\r\n--" + boundary + b"--\r\n")
    with pytest.raises(ValueError, match="^email_limits_exceeded$"):
        contracts.normalize(email_envelope(mail(part.split(b"\r\n\r\n", 1)[1], content_type=b"multipart/mixed; boundary=b8")), "email")


def test_media_requires_real_decode_and_sanitizes_filename(contracts):
    result = contracts.normalize(media(), "chat")
    event = result["events"][0]
    assert event["kind"] == "photo" and event["text"] is None
    assert event["asset"] == {"filename": "unsafe.png", "mime_type": "image/png", "data": png()}
    with pytest.raises(ValueError, match="^invalid_media$"):
        contracts.normalize(media(data=b"\x89PNG\r\n\x1a\nnot-a-real-image"), "chat")


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="offline ffprobe required")
def test_call_recording_is_validated_offline_without_asr(contracts, monkeypatch):
    from tools.dwelly_platform.media import OpenAIMediaProvider
    monkeypatch.setattr(OpenAIMediaProvider, "process", lambda *a, **k: pytest.fail("provider forbidden"))
    result = contracts.normalize(media("call_recording", "audio/wav", audio()), "phone")
    assert result["events"][0]["kind"] == "call_recording"
    assert result["events"][0]["asset"]["data"] == audio()
    assert result["provenance"]["transcript_verification"] == "not_transcribed"


@pytest.mark.parametrize("channel,value", [
    ("phone", media()), ("email", media("voice_message", "audio/wav", audio())),
    ("chat", media("photo", "audio/wav", audio())),
])
def test_media_channel_and_kind_mismatches_rejected(contracts, channel, value):
    with pytest.raises(ValueError, match="^channel_format_mismatch$"):
        contracts.normalize(value, channel)


def test_invalid_base64_and_unknown_media_fields_rejected(contracts):
    supplied = media()
    supplied["payload"]["data_base64"] = "not!base64"
    with pytest.raises(ValueError, match="^invalid_base64$"):
        contracts.normalize(supplied, "chat")
    supplied = media()
    supplied["payload"]["url"] = "https://example.test/track"
    with pytest.raises(ValueError, match="^invalid_media$"):
        contracts.normalize(supplied, "chat")


def test_email_attachment_is_same_case_draft_not_an_external_url(contracts):
    part = (b'Content-Type: image/png\r\nContent-Disposition: attachment; filename="../../image.png"\r\n'
            b"Content-Transfer-Encoding: base64\r\n\r\n" + base64.b64encode(png()))
    raw = multipart([b"Content-Type: text/plain\r\n\r\nAttached source image.", part])
    result = contracts.normalize(email_envelope(raw), "email")
    assert len(result["events"]) == 2
    assert result["events"][1]["asset"] == {"filename": "image.png", "mime_type": "image/png", "data": png()}


def test_email_attachment_limit_rejects_the_whole_message(contracts):
    part = (b'Content-Type: image/png\r\nContent-Disposition: attachment; filename="image.png"\r\n'
            b"Content-Transfer-Encoding: base64\r\n\r\n" + base64.b64encode(png()))
    raw = multipart([b"Content-Type: text/plain\r\n\r\nsource", *([part] * 17)])
    with pytest.raises(ValueError, match="^email_limits_exceeded$"):
        contracts.normalize(email_envelope(raw), "email")


def test_error_codes_are_finite_and_plain_value_errors(contracts):
    with pytest.raises(ValueError) as caught:
        contracts.normalize(envelope(), "unknown")
    assert type(caught.value) is ValueError
    assert caught.value.args[0] in contracts.ERROR_CODES
