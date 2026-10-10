#!/usr/bin/env python3
"""Validate generated cases 051–100 against the public-case format and the manifest.

Usage: python3 validate.py [--public <path to public Delivery & Logistics dir>]
Writes labels.csv next to the manifest. Exits 1 if any case has errors.
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent / "Delivery & Logistics"
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))

OVERVIEW = ("The escalation snapshot comprises history events 001–002. Event 003 records the next agent action; "
            "the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be "
            "used as if already known at escalation.")
STATUS = "Completed — specific coordination task only"
DATA = "Entirely synthetic; English; fictional geography; all times UTC"
COORD = "Iona Quill, Rivet Delivery Desk"
ATTACH = "None. Any documentary record is an explicitly inline excerpt in the history, not a separate file."
HIST_LINK = "[Read the complete dated history](history.md)."
INDEX_SECTIONS = ["Case details", "Context", "Initial request", "Overview", "Next action at escalation",
                  "Outcome", "Boundaries and remaining work", "History", "Attachments"]
CHANNELS = {"Email", "Customer portal", "Business portal", "Dispatch chat", "Call transcript",
            "Pickup-point portal", "Depot work queue", "Freight portal", "Safety incident queue",
            "Warehouse work queue", "Broker portal"}
TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC$")


def section(text: str, name: str) -> str:
    m = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def field(block: str, name: str) -> str:
    m = re.search(rf"^- \*\*{re.escape(name)}:\*\* (.+)$", block, re.M)
    return m.group(1).strip() if m else ""


def parse_events(hist: str):
    parts = re.split(r'^<a id="event-(\d{3})"></a>\n', hist, flags=re.M)
    events = []
    for i in range(1, len(parts), 2):
        num, body = parts[i], parts[i + 1]
        head = re.match(r"^## (.+?) — event (\d{3})\n\n(.*?)\n\n(.*)$", body.strip(), re.S)
        if not head:
            events.append({"num": num, "bad": True})
            continue
        ts, num2, fields, text = head.groups()
        events.append({
            "num": num, "num2": num2, "ts": ts,
            "stage": field(fields, "Stage"), "channel": field(fields, "Channel"),
            "from": field(fields, "From"), "to": field(fields, "To"),
            "text": text.strip(), "bad": False,
        })
    return events


def public_names(public_dir: Path):
    names = set()
    if not public_dir or not public_dir.exists():
        return names
    for idx in public_dir.glob("*/index.md"):
        sr = field(idx.read_text(encoding="utf-8"), "Source role")
        if sr:
            names.add(sr.split(",")[0].strip())
    for h in public_dir.glob("*/history.md"):
        for m in re.finditer(r"^- \*\*(?:From|To):\*\* (.+)$", h.read_text(encoding="utf-8"), re.M):
            for part in m.group(1).split(";"):
                n = part.split(",")[0].strip()
                if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+$", n):
                    names.add(n)
    return names


def person_names(text: str):
    return set(re.findall(r"\b([A-Z][a-z]{2,} [A-Z][a-z]{2,})\b", text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", default="")
    args = ap.parse_args()
    pub_names = public_names(Path(args.public)) if args.public else set()

    errors = {}
    labels = []
    seen_names = {}
    for m in MANIFEST:
        n = m["case"]
        errs = []
        d = ROOT / n
        idx_p, hist_p = d / "index.md", d / "history.md"
        if not idx_p.exists() or not hist_p.exists():
            errors[n] = ["missing index.md or history.md"]
            continue
        extra = [p.name for p in d.iterdir() if p.name not in ("index.md", "history.md")]
        if extra:
            errs.append(f"extra entries in folder: {extra}")
        idx = idx_p.read_text(encoding="utf-8")
        hist = hist_p.read_text(encoding="utf-8")

        # ---- index.md
        title_m = re.match(rf"^# Case {n}: (.+)$", idx, re.M)
        title = title_m.group(1).strip() if title_m else ""
        if not title:
            errs.append("index: missing '# Case 0NN: Title'")
        elif title != m["title"]:
            errs.append(f"index: title differs from manifest: {title!r}")
        heads = re.findall(r"^## (.+)$", idx, re.M)
        if heads != INDEX_SECTIONS:
            errs.append(f"index: sections {heads}")
        details = section(idx, "Case details")
        for k, want in (("Status", STATUS), ("Coordinator", COORD), ("Data", DATA)):
            if field(details, k) != want:
                errs.append(f"index: {k} = {field(details, k)!r}")
        primary = field(details, "Primary shipment") or field(details, "Primary task reference")
        want_primary = m.get("primary_ref", f"DL-{n}")
        if primary != want_primary:
            errs.append(f"index: primary ref {primary!r} != {want_primary!r}")
        created, escalated = field(details, "Created"), field(details, "Escalated")
        updated, completed = field(details, "Updated"), field(details, "Completed")
        if created != f"{m['date']} 09:00:00 UTC":
            errs.append(f"index: Created {created!r}")
        if escalated != f"{m['date']} 09:10:00 UTC":
            errs.append(f"index: Escalated {escalated!r}")
        if updated != completed:
            errs.append("index: Updated != Completed")
        if section(idx, "Overview") != OVERVIEW:
            errs.append("index: Overview paragraph not verbatim")
        if section(idx, "History") != HIST_LINK:
            errs.append("index: History section not verbatim")
        if section(idx, "Attachments") != ATTACH:
            errs.append("index: Attachments section not verbatim")
        na = section(idx, "Next action at escalation")
        na_recipient, na_channel = field(na, "Recipient"), field(na, "Channel")
        if "[History event 003](history.md#event-003)" not in na:
            errs.append("index: Recorded action link missing")
        if na_channel != m["action_channel"]:
            errs.append(f"index: Next-action channel {na_channel!r} != manifest {m['action_channel']!r}")
        na_sentence = na.split("\n")[0].strip()
        source_role = field(details, "Source role")
        boundaries = section(idx, "Boundaries and remaining work")
        if " not " not in boundaries and "n't" not in boundaries and "never" not in boundaries:
            errs.append("index: Boundaries lacks an explicit limit ('X is not Y')")

        # ---- history.md
        hm = re.match(rf"^# Case {n} history — (.+)$", hist, re.M)
        if not hm or hm.group(1).strip() != title:
            errs.append("history: title line missing or differs from index")
        tm = re.search(r"Total events: (\d+)\.", hist)
        events = parse_events(hist)
        if not tm or int(tm.group(1)) != len(events):
            errs.append(f"history: Total events {tm.group(1) if tm else None} vs parsed {len(events)}")
        if len(events) not in (4, 5):
            errs.append(f"history: {len(events)} events (expected 4 or 5)")
        prev = None
        for i, e in enumerate(events, 1):
            if e["bad"]:
                errs.append(f"history: event {e['num']} malformed")
                continue
            if e["num"] != f"{i:03d}" or e["num2"] != f"{i:03d}":
                errs.append(f"history: event numbering at {e['num']}/{e['num2']}")
            tsm = TS.match(e["ts"])
            if not tsm:
                errs.append(f"history: bad timestamp {e['ts']!r}")
            else:
                t = datetime.strptime(tsm.group(1), "%Y-%m-%d %H:%M:%S")
                if prev and t <= prev:
                    errs.append(f"history: timestamps not increasing at event {e['num']}")
                prev = t
            want_stage = {1: "Context", 2: "Escalation", 3: "Agent action"}.get(i, "Follow-through / confirmation")
            if e["stage"] != want_stage:
                errs.append(f"history: event {e['num']} stage {e['stage']!r} != {want_stage!r}")
            if e["channel"] not in CHANNELS:
                errs.append(f"history: event {e['num']} channel {e['channel']!r}")
            if not e["from"] or not e["to"]:
                errs.append(f"history: event {e['num']} missing From/To")
            if i in (1, 2) and COORD not in e["to"]:
                errs.append(f"history: event {e['num']} To should include coordinator")
            if i == 3:
                if e["from"] != COORD:
                    errs.append("history: event 003 From must be the coordinator")
                if e["channel"] != m["action_channel"]:
                    errs.append(f"history: event 003 channel {e['channel']!r} != manifest")
                if na_recipient and na_recipient != e["to"]:
                    errs.append(f"index/history: Next-action Recipient {na_recipient!r} != event 003 To {e['to']!r}")
            if "Plover Arc Logistics" not in e["from"] and i == 1 and "supervisor" not in e["from"].lower() \
                    and "Counter" not in e["from"]:
                errs.append(f"history: event 001 From should be carrier side: {e['from']!r}")
            wc = len(e["text"].split())
            if wc < 12 or wc > 110:
                errs.append(f"history: event {e['num']} text length {wc} words")
            if "—" in e["text"]:
                errs.append(f"history: em-dash in event {e['num']} text")
        if events and not events[0]["bad"] and events[0]["ts"] != created:
            errs.append("history: event 001 timestamp != Created")
        if len(events) > 1 and not events[1]["bad"]:
            if events[1]["ts"] != escalated:
                errs.append("history: event 002 timestamp != Escalated")
            if events[1]["text"] != section(idx, "Initial request"):
                errs.append("index: Initial request != event 002 text")
        if events and not events[-1]["bad"] and events[-1]["ts"] != completed:
            errs.append("history: last event timestamp != Completed")
        if events and len(events) >= 3 and not events[2]["bad"] and events[2]["ts"] != f"{m['date']} 09:25:00 UTC":
            errs.append("history: event 003 not at 09:25")
        for s in ("Context", "Outcome", "Boundaries and remaining work"):
            if "—" in section(idx, s):
                errs.append(f"index: em-dash in {s}")
        for bad in (r"\bhackathon\b", r"\bAI\b", r"\bLLM\b", r"\blanguage model\b"):
            if re.search(bad, idx + hist, re.I if "AI" not in bad else 0):
                errs.append(f"text mentions {bad!r}")

        # ---- names
        names = person_names(idx + "\n" + hist) - {"Iona Quill", "Plover Arc", "Rivet Delivery", "Arc Logistics",
                                                    "Delivery Desk", "Customer portal", "Business portal"}
        names = {x for x in names if not any(w in x for w in ("Counter", "Court", "Mews", "Quay", "Row", "Lane",
                                                                "Logistics", "Desk", "Press", "Spur", "Portal",
                                                                "Delivery", "Dispatch", "Depot", "Freight", "Route",
                                                                "Total", "Stage", "Channel", "Case", "Event", "Customer",
                                                                "Business", "Safety", "Operations", "Account", "Returns",
                                                                "Collections", "Notification", "Tracking", "Parcel",
                                                                "Recipient", "Address", "Compliance", "Scheduling",
                                                                "Routing", "Next", "Initial", "Boundaries", "Primary",
                                                                "Source", "Entirely", "Please", "Read", "None", "All",
                                                                "Facts", "Event", "The", "This", "Our", "Your", "Do", "We"))}
        for nm in names:
            if nm in pub_names:
                errs.append(f"name reused from public cases: {nm}")
            if nm in seen_names and seen_names[nm] != n:
                errs.append(f"name {nm} also used in case {seen_names[nm]}")
            seen_names.setdefault(nm, n)

        if errs:
            errors[n] = errs
        labels.append({
            "case": n, "difficulty": m["difficulty"], "decision_type": m["decision_type"], "sheet": m["sheet"],
            "scenario": m["scenario"], "title": title, "source_role": source_role, "stage": m["stage"],
            "action_to": events[2]["to"] if len(events) > 2 and not events[2]["bad"] else "",
            "action_channel": na_channel, "next_action": na_sentence, "boundary": boundaries.replace("\n", " "),
            "outcome": section(idx, "Outcome").replace("\n", " "), "events": len(events), "date": m["date"],
            "errors": len(errs),
        })

    out = HERE / "labels.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(labels[0].keys()) if labels else ["case"])
        w.writeheader()
        w.writerows(labels)

    ok = len(MANIFEST) - len(errors)
    print(f"cases checked: {len(labels)}; ok: {ok}; with errors: {len(errors)}")
    for n in sorted(errors):
        print(f"\n[{n}]")
        for e in errors[n]:
            print("  -", e)
    print(f"\nlabels written: {out}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
