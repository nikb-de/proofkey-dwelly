"""Deterministic, snapshot-only draft communications; no operational effects."""
import re


_CUSTOMER = re.compile(r"\b(customer|tenant|resident|occupant|buyer)\b|\S,\s*recipient\s*$", re.I)
_PROVIDER = re.compile(
    r"\b(provider|courier|carrier|driver|supplier|delivery company|logistics|"
    r"dhl|dpd|ups|fedex|evri|yodel|royal mail|parcelforce)\b", re.I)
_CHOICE = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
                     r"morning|afternoon|evening)\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b", re.I)


def _contact(events, role):
    for event in reversed(events):
        for field in ("sender", "recipients"):
            name = event.get(field, "")
            if isinstance(name, str) and role.search(name):
                return name, event.get("channel", "")
    return None


def _missing_details_message(text):
    fields = []
    if re.search(r"\b(apartment|flat)\b", text, re.I):
        fields.append("the missing apartment or flat number")
    if re.search(r"\bpostcode\b", text, re.I):
        fields.append("the missing postcode")
    message = "Please provide " + " and ".join(fields or ["the missing delivery address details"]) + "."
    if re.search(r"\b(access|door code)\b", text, re.I):
        access = "Please confirm how the courier can access the delivery location at delivery time."
        message = message + " " + access if fields else access
    return message


def _offered_choices(events):
    choices = set()
    for event in events:
        for sentence in re.split(r"[.!?\n]", event["body"]):
            alternatives = re.split(r"\bor\b", sentence, flags=re.I)
            if len(alternatives) >= 2 and all(_CHOICE.search(part) for part in alternatives):
                choices.update(match.group().lower() for part in alternatives for match in _CHOICE.finditer(part))
    return choices


def propose(snapshot: dict) -> dict:
    """Return an unsent draft using only the supplied visible event data."""
    events = sorted(snapshot["events"], key=lambda item: (item["occurred_at"], item["event_id"]))
    if not events:
        raise ValueError("A snapshot needs visible events for source citations")
    text = "\n".join(event["body"] for event in events)
    customer, provider = _contact(events, _CUSTOMER), _contact(events, _PROVIDER)
    kind, contact = "operator_review", ("operator", "internal")
    message = "Please review the visible case and establish the appropriate next contact."
    if re.search(r"\b(gas leak|fire|immediate danger|life.threatening|electric shock|"
                 r"unidentified liquid|unknown leak|chemical spill|liquid is leaking|"
                 r"safety (?:lead|review|incident)|food.safety)\b", text, re.I):
        kind = "safety_escalation"
        message = "Urgent operator review requested: assess the reported safety risk and appropriate escalation."
    elif customer:
        choices = _offered_choices(events)
        customer_messages = [event["body"] for event in events if _CUSTOMER.search(event.get("sender", ""))]
        latest_customer = customer_messages[-1].lower() if customer_messages else ""
        selected = bool(re.search(r"\b(choose|select|prefer|works|confirm|book)\b", latest_customer)
                        and any(choice in latest_customer for choice in choices))
        if choices and not selected and re.search(r"reschedul|deliver|slot", text, re.I):
            kind, contact = "request_customer_choice", customer
            message = "Please choose your preferred option from the offered delivery slots before scheduling proceeds."
        elif re.search(r"\b(missing|incomplete|needs?|needed|provide|without|no)\b", text, re.I) and re.search(
                r"\b(address|apartment|flat|access|postcode|door code)\b", text, re.I):
            kind, contact = "request_missing_details", customer
            message = _missing_details_message(text)
        elif re.search(r"\b(photo|photos|photograph|evidence|proof)\b", text, re.I) and re.search(
                r"\b(request|provide|send|need|obtain)\b", text, re.I):
            evidence_contact = provider if (provider and re.search(r"proof of delivery", text, re.I)) else customer
            kind, contact = "request_evidence", evidence_contact
            message = "Please provide the requested supporting evidence or photos so the delivery issue can be reviewed."
    if kind == "operator_review":
        for event in reversed(events):
            if (re.search(r"\b(damage intake|claims team)\b", event["sender"], re.I)
                    and re.search(r"\b(photo|photos|photograph|evidence|proof)\b", event["body"], re.I)
                    and re.search(r"\b(request|provide|send|need|obtain)\b", event["body"], re.I)
                    and event["recipients"].strip().lower() not in {"", "recipient", "unknown"}):
                kind, contact = "request_evidence", (event["recipients"], event["channel"])
                message = "Please provide the requested supporting evidence or photos so the delivery issue can be reviewed."
                break
    if kind == "operator_review" and provider and re.search(
            r"\b(delivery|parcel|package|courier|shipment|driver|logistics)\b", text, re.I):
        kind, contact = "contact_provider", provider
        message = "Please review the reported delivery issue and advise on the current status and available next steps."
    return {
        "schema_version": "dwelly-proposal-v1", "case_id": snapshot["case_id"],
        "input_hash": snapshot["input_hash"], "mode": "deterministic_baseline",
        "status": "proposed_unsent",
        "action": {"kind": kind, "recipient": contact[0], "channel": contact[1], "message": message},
        "evidence_refs": sorted({event["event_id"] for event in events}), "effects": [],
        "limitations": ["Development-only deterministic draft; semantic correctness is unassessed.",
                        "Contacts are inferred from visible message labels, not verified authority."],
    }
