from pathlib import Path


def make_source(root: Path, number="001"):
    case = root / "Delivery & Logistics" / number
    (case / "attachments").mkdir(parents=True)
    (case / "index.md").write_text("# Future title\n\nSECRET_FUTURE_OUTCOME\n", encoding="utf-8")
    (case / "attachments" / "visible.txt").write_bytes(b"visible source\n")
    (case / "attachments" / "future.txt").write_bytes(b"SECRET_FUTURE_ATTACHMENT\n")
    rows = [
        ("Context", "Email", "Dispatch", "Desk", "There are two rescheduling options: 15:00 or 17:00. [Terms](attachments/visible.txt)"),
        ("Escalation", "Customer portal", "Ari, recipient", "Desk", "I cannot attend. Can you move my delivery?"),
        ("Agent action", "Customer portal", "Desk", "Ari", "SECRET_FUTURE_ACTION choose a slot."),
        ("Follow-through / confirmation", "Email", "Dispatch", "Desk", "SECRET_FUTURE_CONFIRMATION [Receipt](attachments/future.txt)"),
    ]
    text = "# Case history\n\n"
    for ordinal, (stage, channel, sender, recipient, body) in enumerate(rows, 1):
        text += (f'<a id="event-{ordinal:03d}"></a>\n'
                 f"## 2026-02-02 09:{ordinal:02d}:00 UTC — event {ordinal:03d}\n\n"
                 f"- **Stage:** {stage}\n- **Channel:** {channel}\n"
                 f"- **From:** {sender}\n- **To:** {recipient}\n\n{body}\n\n")
    (case / "history.md").write_text(text, encoding="utf-8")
    return case
