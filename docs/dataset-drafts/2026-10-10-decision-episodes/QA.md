# Package QA and reproduction

## Status

The package is a draft authoring kit, not a deployed evaluation runner. The command below is a **read-only structural check**, not a semantic judge or a replay engine. It needs Python 3.9+ and the existing `jsonschema` package; it makes no network calls and writes no files.

Run from the repository root:

```bash
python3 - docs/dataset-drafts/2026-10-10-decision-episodes <<'PY'
import collections, hashlib, json, pathlib, re, sys
from datetime import datetime
from jsonschema import Draft202012Validator, FormatChecker

root = pathlib.Path(sys.argv[1]).resolve()
schemas = {p.stem.split(".")[0]: json.loads(p.read_text()) for p in (root/"schemas").glob("*.json")}
validators = {}
for name, schema in schemas.items():
    Draft202012Validator.check_schema(schema)
    validators[name] = Draft202012Validator(schema, format_checker=FormatChecker())
rows = [json.loads(line) for line in (root/"examples/manifest.jsonl").read_text().splitlines() if line.strip()]
seen, inputs, labels, families, stages, episodes = set(), {}, {}, {}, collections.Counter(), set()
dt = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
for row in rows:
    validators["manifest"].validate(row)
    key = row["decision_id"]
    assert key not in seen, ("duplicate decision", key)
    seen.add(key)
    families.setdefault(row["family_id"], set()).add(row["split"])
    assert row["split"] == "development" and not row["human_reviewed"]
    for field, schema in (("input", "input"), ("label", "label")):
        path = (root/"examples"/row[field+"_path"]).resolve()
        assert path.is_relative_to(root/"examples")
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row[field+"_sha256"], ("hash", key, field)
        value = json.loads(raw)
        validators[schema].validate(value)
        assert value["decision_id"] == key
        (inputs if field == "input" else labels)[key] = value
    inp, lab = inputs[key], labels[key]
    assert inp["episode_id"] == row["episode_id"]
    assert not lab["human_reviewed"] and lab["annotation_status"] == "assistant_authored_draft"
    p = inp["payload"]
    stages[inp["stage"]] += 1
    episodes.add(inp["episode_id"])
    assert p["policy_snapshot"] is None or p["policy_snapshot"]["synthetic"] is True
    assert all(c["mode"] in ("propose_only", "simulated_only") for c in p["capabilities"])
    assert all(a["execution_mode"] in ("propose_only", "simulated_only") for a in lab["acceptable_next_actions"])
    actors = {x["participant_id"] for x in p["participants"]}
    assert len(actors) == len(p["participants"])
    eids = {e["event_id"] for e in p["events"]}
    assert len(eids) == len(p["events"])
    for event in p["events"]:
        assert event["sender_id"] in actors
        assert dt(event["observed_at"]) <= dt(inp["as_of"]), ("future event", key)
        assert dt(event["occurred_at"]) <= dt(event["observed_at"])
    for artifact in p["artifacts"]:
        assert artifact["source_event_id"] in eids
        if artifact["read_status"] != "readable":
            assert artifact["extracted_content"] is None
        else:
            assert artifact["content_kind"] == "simulated_extraction"
    refs = set(eids)
    for group, field in (("artifacts","artifact_id"),("approvals","approval_id"),("tool_receipts","receipt_id")):
        refs.update(x[field] for x in p.get(group, []))
    if "gate_receipt" in p:
        refs.add(p["gate_receipt"]["gate_id"])
        assert p["gate_receipt"]["operation"] == p["operation"]
        assert p["gate_receipt"]["allowed"] is True
    for record in p.get("approvals", []) + p.get("tool_receipts", []):
        assert dt(record["observed_at"]) <= dt(inp["as_of"])
    for action in lab["acceptable_next_actions"]:
        assert action["recipient_id"] is None or action["recipient_id"] in actors
    assert set(lab["evidence_refs"]) <= refs, ("unknown evidence", key)
    policy_ids = {r["rule_id"] for r in (p["policy_snapshot"] or {}).get("rules", [])}
    assert set(lab["policy_refs"]) <= policy_ids
    assert set(lab["human_involvement"]["information_participants"]) <= actors
assert all(len(splits) == 1 for splits in families.values()), "family split leakage"
for path in sorted((root/"examples/simulator").glob("*.json")):
    sim = json.loads(path.read_text())
    validators["simulator"].validate(sim)
    assert sim["episode_id"] in episodes
    assert inputs[sim["initial_decision_id"]]["episode_id"] == sim["episode_id"]
    for edge in sim["transitions"]:
        src = inputs[edge["from_decision_id"]]
        assert src["episode_id"] == sim["episode_id"]
        dst_id = edge["next_decision_id"]
        assert (dst_id is None) != (edge["terminal"] is None)
        if dst_id is not None:
            dst = inputs[dst_id]
            assert dst["episode_id"] == sim["episode_id"]
            assert dt(dst["as_of"]) >= dt(src["as_of"])
            previous = {e["event_id"] for e in src["payload"]["events"]}
            next_events = {e["event_id"]: e for e in dst["payload"]["events"]}
            expected_new = set(next_events) - previous
            assert {e["event_id"] for e in edge["inject_events"]} == expected_new
            for e in edge["inject_events"]:
                assert e == next_events[e["event_id"]]
                assert dt(src["as_of"]) < dt(e["observed_at"]) <= dt(dst["as_of"])
assert set(inputs) == {p.stem for p in (root/"examples/agent_inputs").glob("*.json")}
assert set(labels) == {p.stem for p in (root/"examples/private_labels").glob("*.json")}
for path in root.glob("*.md"):
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        if not re.match(r"^[a-z]+:", target):
            assert (path.parent/target.split("#")[0]).exists(), ("broken link", path.name, target)
assert len(rows) == 19 and len(families) == 3 and len(episodes) == 7
assert set(stages) == {"intake","decide","authorize","execute","verify","resume"}
print(json.dumps({"status":"PASS", "decision_snapshots":len(rows), "families":len(families), "episodes":len(episodes), "stages":dict(stages), "scope":"schema, references, hashes, temporal visibility, isolation markers; not model quality"}, indent=2))
PY
```

Expected inventory: 19 decisions, 3 families, 7 episodes, all development. Stages: intake 1, decide 8, authorize 4, execute 1, verify 2, resume 3.

Checks: schemas, unique decision IDs, exact-byte hashes, file links, actor/evidence/policy references, observation cutoffs, simulated-only capability markers, episode membership, future-event transition boundaries, no family crossing splits, and complete inventory.

These checks do **not** detect all semantic leakage, prove source authenticity, implement a gate, run a case through a model, execute simulator transitions, validate the policies, or establish dataset independence. Review the input/label pairs manually before using them as references.

## Semantic review checklist

- d001–d003: claim of an attachment vs readable content; one targeted evidence request.
- d004–d005: new evidence resolves the old question; authority remains a separate blocker.
- d006–d008: missing approval blocks; matching approval allows only the bound simulation; changed amount/revision blocks again.
- d009–d012: actual offered options and customer choice; refusal is not cancellation; routine policy permits monitored simulation.
- d013–d015: accepted is not completed; crash is not failed; only matching authoritative readback supports simulated completion.
- d016–d019: inline receipt vs absent receipt vs conflict vs policy-defined timeout.

Assistant inspection of these examples is not human calibration. All reference labels remain draft.

## Deferred work

No current-runner import, LLM-as-judge requests, model training, end-to-end replay, production authentication, real media understanding or sealed evaluation has been performed as part of this package.
