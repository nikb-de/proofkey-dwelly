#!/usr/bin/env python3
"""Build one case folder per negative branch, in the public-case format.

Layout written under --out:
  0NN/N{k}-{FAILURE_MODE}/index.md
  0NN/N{k}-{FAILURE_MODE}/history.md      events 001..K from the public case, then the branch's
                                           new event, the coordinator's action, one confirmation
  0NN/N{k}-{FAILURE_MODE}/attachments/     only if a retained event references one
  index.csv                                one row per branch

Usage: python3 negatives_build.py --public "<public Delivery & Logistics dir>" --out "<folder>"
Reads negatives/0NN.json (with agent_event and followup_event). Exits 1 on any error.
"""
import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
NEG = HERE.parent / "negatives"
COORD = "Iona Quill, Rivet Delivery Desk"
STATUS = "Completed — specific coordination task only"
DATA = "Entirely synthetic; English; fictional geography; all times UTC"
ATTACH_NONE = "None. Any documentary record is an explicitly inline excerpt in the history, not a separate file."
TSF = "%Y-%m-%d %H:%M:%S"


def field(block: str, name: str) -> str:
    m = re.search(rf"^- \*\*{re.escape(name)}:\*\* (.+)$", block, re.M)
    return m.group(1).strip() if m else ""


def section(text: str, name: str) -> str:
    m = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def parse_events(hist: str):
    parts = re.split(r'^<a id="event-(\d{3})"></a>\n', hist, flags=re.M)
    events = []
    for i in range(1, len(parts), 2):
        body = parts[i + 1].strip()
        head = re.match(r"^## (.+?) — event (\d{3})\n\n(.*?)\n\n(.*)$", body, re.S)
        if not head:
            raise ValueError(f"malformed event {parts[i]}")
        ts, num, fields, text = head.groups()
        events.append({"ts": ts, "num": num, "stage": field(fields, "Stage"), "channel": field(fields, "Channel"),
                       "from": field(fields, "From"), "to": field(fields, "To"), "text": text.strip()})
    return events


def emit_event(num: int, ts: str, stage: str, channel: str, frm: str, to: str, text: str) -> str:
    return (f'<a id="event-{num:03d}"></a>\n## {ts} — event {num:03d}\n\n'
            f"- **Stage:** {stage}\n- **Channel:** {channel}\n- **From:** {frm}\n- **To:** {to}\n\n{text}\n")


def parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts.replace(" UTC", ""), TSF)


def fmt_ts(dt: datetime) -> str:
    return dt.strftime(TSF) + " UTC"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    pub = Path(args.public)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    errors = {}
    rows = []
    built = 0
    for i in range(1, 51):
        n = f"{i:03d}"
        src = NEG / f"{n}.json"
        if not src.exists():
            errors[n] = ["missing json"]
            continue
        d = json.loads(src.read_text(encoding="utf-8"))
        idx = (pub / n / "index.md").read_text(encoding="utf-8")
        hist = (pub / n / "history.md").read_text(encoding="utf-8")
        try:
            events = parse_events(hist)
        except ValueError as e:
            errors[n] = [str(e)]
            continue
        title = re.search(rf"^# Case {n}: (.+)$", idx, re.M).group(1).strip()
        details = section(idx, "Case details")
        primary_line = next((ln for ln in details.splitlines()
                             if ln.startswith("- **Primary shipment:**") or ln.startswith("- **Primary task reference:**")), "")
        errs = []
        for k, neg in enumerate(d["negatives"], 1):
            tag = f"N{k}"
            ae, fe = neg.get("agent_event"), neg.get("followup_event")
            if not ae or not fe:
                errs.append(f"{tag}: agent_event/followup_event missing")
                continue
            for key in ("channel", "to", "text"):
                if not ae.get(key):
                    errs.append(f"{tag}: agent_event.{key} empty")
            for key in ("timestamp", "channel", "from", "to", "text"):
                if not fe.get(key):
                    errs.append(f"{tag}: followup_event.{key} empty")
            if errs and errs[-1].startswith(tag):
                continue
            K = int(neg["insert_after"])
            retained = events[:K]
            ev = neg["new_event"]
            t_new = parse_ts(ev["timestamp"])
            t_agent = parse_ts(ae["timestamp"]) if ae.get("timestamp") else t_new + timedelta(minutes=15)
            if t_agent <= t_new:
                errs.append(f"{tag}: agent action timestamp not after the new event")
                continue
            t_fu = parse_ts(fe["timestamp"])
            if t_fu <= t_agent:
                errs.append(f"{tag}: followup timestamp {fe['timestamp']} not after agent action {fmt_ts(t_agent)}")
                continue
            if (t_fu - t_agent).days > 1:
                errs.append(f"{tag}: followup more than a day after the agent action")
            for key, txt in (("agent", ae["text"]), ("followup", fe["text"])):
                wc = len(txt.split())
                if wc < 12 or wc > 100:
                    errs.append(f"{tag}: {key} text {wc} words")
                if "—" in txt:
                    errs.append(f"{tag}: em-dash in {key} text")
            n_new, n_agent, n_fu = K + 1, K + 2, K + 3
            folder = out / n / f"{tag}-{neg['failure_mode']}"
            folder.mkdir(parents=True, exist_ok=True)
            branch_title = f"{title} ({neg['label']})"

            # attachments referenced in retained events
            attach = []
            for e in retained:
                for m in re.finditer(r"\(attachments/([^)]+)\)", e["text"]):
                    name = m.group(1)
                    srcf = pub / n / "attachments" / name
                    if srcf.exists() and name not in attach:
                        (folder / "attachments").mkdir(exist_ok=True)
                        shutil.copy2(srcf, folder / "attachments" / name)
                        attach.append(name)

            # history.md
            h = [f"# Case {n}-{tag} history — {branch_title}", "",
                 f"All identities, records and communications are fictional. Total events: {n_fu}. "
                 f"Events 001–{K:03d} are retained from public case {n}; events {n_new:03d}–{n_fu:03d} are this branch.", ""]
            for j, e in enumerate(retained, 1):
                h.append(emit_event(j, e["ts"], e["stage"], e["channel"], e["from"], e["to"], e["text"]))
            h.append(emit_event(n_new, ev["timestamp"], "Escalation", ev["channel"], ev["from"], ev["to"], ev["text"]))
            h.append(emit_event(n_agent, fmt_ts(t_agent), "Agent action", ae["channel"], COORD, ae["to"], ae["text"]))
            h.append(emit_event(n_fu, fe["timestamp"], "Follow-through / confirmation", fe["channel"], fe["from"], fe["to"], fe["text"]))
            (folder / "history.md").write_text("\n".join(h), encoding="utf-8")

            # index.md
            attach_section = ATTACH_NONE if not attach else "\n".join(f"- [{a}](attachments/{a})" for a in attach)
            ix = f"""# Case {n}-{tag}: {branch_title}

## Case details

- **Source role:** {ev['from']}
- **Status:** {STATUS}
- **Created:** {retained[0]['ts']}
- **Escalated:** {ev['timestamp']}
- **Updated:** {fe['timestamp']}
- **Completed:** {fe['timestamp']}
{primary_line}
- **Coordinator:** {COORD}
- **Data:** {DATA}
- **Derived from:** Public case {n}, events 001–{K:03d} retained; branch {neg['failure_mode']}

## Context

{d['snapshot']} This branch diverges after event {K:03d}: {neg['label'].rstrip('.')}.

## Initial request

{ev['text']}

## Overview

The escalation snapshot comprises history events 001–{n_new:03d}. Event {n_agent:03d} records the next agent action; the subsequent events provide the disclosed calibration follow-through. Facts learned later must not be used as if already known at escalation.

## Next action at escalation

{neg['expected_action']}

- **Recipient:** {ae['to']}
- **Channel:** {ae['channel']}
- **Recorded action:** [History event {n_agent:03d}](history.md#event-{n_agent:03d})
- **Expected decision:** {neg['expected_decision']} (workflow sheet {neg['sheet']})

## Outcome

{neg['done_means']}

## Boundaries and remaining work

Must not: {neg['must_not'].rstrip('.')}.

## History

[Read the complete dated history](history.md).

## Attachments

{attach_section}
"""
            (folder / "index.md").write_text(ix, encoding="utf-8")
            built += 1
            rows.append({"case": n, "branch": neg["id"], "folder": f"{n}/{tag}-{neg['failure_mode']}",
                         "failure_mode": neg["failure_mode"], "expected_decision": neg["expected_decision"],
                         "sheet": neg["sheet"], "insert_after": neg["insert_after"], "label": neg["label"],
                         "title": title})
        if errs:
            errors[n] = errs

    with (out / "index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["case", "branch", "folder", "failure_mode", "expected_decision", "sheet",
                                          "insert_after", "label", "title"])
        w.writeheader()
        w.writerows(rows)
    print(f"branches built: {built}; cases with errors: {len(errors)}; index: {out / 'index.csv'}")
    for n in sorted(errors):
        print(f"\n[{n}]")
        for e in errors[n]:
            print("  -", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
