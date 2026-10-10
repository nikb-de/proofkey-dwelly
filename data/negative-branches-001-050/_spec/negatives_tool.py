#!/usr/bin/env python3
"""Validate negatives/0NN.json and render negatives/0NN.md plus negatives/README.md.

Usage: python3 negatives_tool.py [--public <public Delivery & Logistics dir>]
Exits 1 if any file has errors.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
NEG = HERE.parent / "negatives"

FAILURE_MODES = {"NO_REPLY", "AMBIGUOUS_REPLY", "UNAUTHORISED_REPLY", "CHANNEL_FAILURE", "STALE_STATE",
                 "CUSTOMER_CANCELS", "DUPLICATE_REQUEST", "CONFLICTING_RECORDS", "OUT_OF_POLICY_ASK",
                 "PHYSICAL_FAILURE", "NEEDS_HUMAN", "SNAPSHOT_CONFLICT"}
DECISIONS = {"ASK_CUSTOMER", "REQUEST_ACTION", "GET_OPTIONS", "VERIFY_FIRST", "ESCALATE_OPERATOR",
             "WAIT_WITH_DEADLINE", "DECLINE_EXPLAIN", "RECORD_STOP", "RECORD_REFUSAL", "RESOLVE_DUPLICATE",
             "SEPARATE_AUTHORITY", "RECONCILE_CONFLICT"}
SHEETS = {"A", "B", "C", "R", "D", "E", "F", "Z"}
CHANNELS = {"Email", "Customer portal", "Business portal", "Dispatch chat", "Call transcript",
            "Pickup-point portal", "Depot work queue", "Freight portal", "Safety incident queue",
            "Warehouse work queue", "Broker portal"}
MUST_HAVE_ONE_OF = {"CHANNEL_FAILURE", "STALE_STATE", "CONFLICTING_RECORDS"}
TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$")
NEG_KEYS = {"id", "label", "failure_mode", "insert_after", "new_event", "expected_decision", "sheet",
            "expected_action", "must_not", "done_means"}
EV_KEYS = {"timestamp", "channel", "from", "to", "text"}


def event_times(public_dir: Path, n: str):
    """Return {event_num: timestamp} from the public history, if available."""
    out = {}
    if not public_dir:
        return out
    h = public_dir / n / "history.md"
    if not h.exists():
        return out
    for m in re.finditer(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC) — event (\d{3})$", h.read_text(encoding="utf-8"), re.M):
        out[m.group(2)] = m.group(1)
    return out


def public_title(public_dir: Path, n: str):
    if not public_dir:
        return None
    p = public_dir / n / "index.md"
    if not p.exists():
        return None
    m = re.search(rf"^# Case {n}: (.+)$", p.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else None


def render(d: dict) -> str:
    lines = [f"# Case {d['case']} negatives — {d['title']}", "",
             f"**Snapshot (events 001–002):** {d['snapshot']}", "",
             f"**Recorded action (event 003):** {d['recorded_action']}", ""]
    for neg in d["negatives"]:
        ev = neg["new_event"]
        lines += [f"## {neg['id']} · {neg['label']}", "",
                  f"- **Failure mode:** {neg['failure_mode']} · **Sheet:** {neg['sheet']} · **Inserted after event:** {neg['insert_after']}",
                  f"- **New event:** {ev['timestamp']} · {ev['channel']} · {ev['from']} → {ev['to']}", "",
                  f"> {ev['text']}", "",
                  f"- **Expected decision:** {neg['expected_decision']}",
                  f"- **Expected action:** {neg['expected_action']}",
                  f"- **Must not:** {neg['must_not']}",
                  f"- **Done means:** {neg['done_means']}", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", default="")
    args = ap.parse_args()
    pub = Path(args.public) if args.public else None

    errors = {}
    stats_fm, stats_dec, stats_sheet = Counter(), Counter(), Counter()
    rows = []
    for i in range(1, 51):
        n = f"{i:03d}"
        p = NEG / f"{n}.json"
        if not p.exists():
            errors[n] = ["missing json"]
            continue
        errs = []
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errors[n] = [f"invalid json: {e}"]
            continue
        if d.get("case") != n:
            errs.append(f"case field {d.get('case')!r}")
        pt = public_title(pub, n)
        if pt and d.get("title") != pt:
            errs.append(f"title differs from public: {d.get('title')!r}")
        for k in ("snapshot", "recorded_action"):
            if not isinstance(d.get(k), str) or len(d[k].split()) < 8:
                errs.append(f"{k} missing or too short")
        negs = d.get("negatives") or []
        if not 4 <= len(negs) <= 6:
            errs.append(f"{len(negs)} negatives (expected 4-6)")
        fms = [x.get("failure_mode") for x in negs]
        if len(set(fms)) != len(fms):
            errs.append(f"repeated failure modes: {fms}")
        if not set(fms) & MUST_HAVE_ONE_OF:
            errs.append("no CHANNEL_FAILURE / STALE_STATE / CONFLICTING_RECORDS branch")
        times = event_times(pub, n)
        ids = set()
        for j, neg in enumerate(negs, 1):
            tag = f"N{j}"
            missing = NEG_KEYS - set(neg)
            if missing:
                errs.append(f"{tag}: missing keys {sorted(missing)}")
                continue
            if neg["id"] in ids or neg["id"] != f"{n}-N{j}":
                errs.append(f"{tag}: id {neg['id']!r}")
            ids.add(neg["id"])
            if neg["failure_mode"] not in FAILURE_MODES:
                errs.append(f"{tag}: failure_mode {neg['failure_mode']!r}")
            if neg["expected_decision"] not in DECISIONS:
                errs.append(f"{tag}: expected_decision {neg['expected_decision']!r}")
            if neg["sheet"] not in SHEETS:
                errs.append(f"{tag}: sheet {neg['sheet']!r}")
            if neg["insert_after"] not in ("002", "003", "004"):
                errs.append(f"{tag}: insert_after {neg['insert_after']!r}")
            if neg["failure_mode"] == "SNAPSHOT_CONFLICT" and neg["insert_after"] != "002":
                errs.append(f"{tag}: SNAPSHOT_CONFLICT must insert after 002")
            ev = neg["new_event"]
            if not isinstance(ev, dict) or EV_KEYS - set(ev):
                errs.append(f"{tag}: new_event keys")
                continue
            if not TS.match(ev["timestamp"]):
                errs.append(f"{tag}: timestamp {ev['timestamp']!r}")
            elif neg["insert_after"] in times:
                t_new = datetime.strptime(ev["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
                t_ref = datetime.strptime(times[neg["insert_after"]][:19], "%Y-%m-%d %H:%M:%S")
                if t_new <= t_ref:
                    errs.append(f"{tag}: timestamp not after event {neg['insert_after']}")
                if (t_new - t_ref).days > 1:
                    errs.append(f"{tag}: timestamp more than a day after event {neg['insert_after']}")
            if ev["channel"] not in CHANNELS:
                errs.append(f"{tag}: channel {ev['channel']!r}")
            wc = len(ev["text"].split())
            if wc < 12 or wc > 100:
                errs.append(f"{tag}: new_event text {wc} words")
            for k in ("expected_action", "must_not", "done_means", "label"):
                if not isinstance(neg[k], str) or not neg[k].strip():
                    errs.append(f"{tag}: {k} empty")
            blob = " ".join([ev["text"], neg["expected_action"], neg["must_not"], neg["done_means"], neg["label"]])
            if "—" in blob:
                errs.append(f"{tag}: em-dash in text")
            stats_fm[neg["failure_mode"]] += 1
            stats_dec[neg["expected_decision"]] += 1
            stats_sheet[neg["sheet"]] += 1
        if errs:
            errors[n] = errs
        else:
            (NEG / f"{n}.md").write_text(render(d), encoding="utf-8")
        rows.append((n, d.get("title", ""), len(negs), ", ".join(fms)))

    readme = ["# Negative branches for public cases 001–050", "",
              "Each case: snapshot at escalation, the recorded next action, and 4–6 alternative continuations "
              "(a new event inserted after a recorded one) with the decision the coordinator should take. "
              "JSON is the source; the .md files are rendered from it by `_spec/negatives_tool.py`.", "",
              "| Case | Title | Branches | Failure modes |", "|---|---|---|---|"]
    for n, t, k, fms in rows:
        readme.append(f"| [{n}]({n}.md) | {t} | {k} | {fms} |")
    readme += ["", "## Totals", "", "| Failure mode | Branches |", "|---|---|"]
    readme += [f"| {k} | {v} |" for k, v in sorted(stats_fm.items(), key=lambda x: -x[1])]
    readme += ["", "| Expected decision | Branches |", "|---|---|"]
    readme += [f"| {k} | {v} |" for k, v in sorted(stats_dec.items(), key=lambda x: -x[1])]
    readme += ["", "| Sheet | Branches |", "|---|---|"]
    readme += [f"| {k} | {v} |" for k, v in sorted(stats_sheet.items())]
    NEG.mkdir(exist_ok=True)
    (NEG / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    total = sum(stats_fm.values())
    print(f"files: {len(rows)}; ok: {len(rows) - len([n for n in errors if n in dict((r[0], r) for r in rows)])}; "
          f"with errors: {len(errors)}; branches: {total}")
    for n in sorted(errors):
        print(f"\n[{n}]")
        for e in errors[n]:
            print("  -", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
