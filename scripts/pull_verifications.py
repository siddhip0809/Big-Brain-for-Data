#!/usr/bin/env python3
"""Merge verification flags set in the atlas back into data/relationships.json.

The atlas stores each claim's flags as a document verifications/<key> in the
artifact's shared database (key = "<type>__<from node>__<to node>"). Export
that collection with the Artifact tool (read_db, collection "verifications",
out_dir <dir>) and run:
    python3 scripts/pull_verifications.py <dir>/verifications
Each relationship gains `verified_by`: {research_team, siddhi, ward} -> date
or null. Nothing else on the relationship is touched.
"""
import json, glob, os, sys
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
src = sys.argv[1]
docs = {}
for f in glob.glob(os.path.join(src, "*.json")):
    d = json.load(open(f)); docs[os.path.basename(f)[:-5]] = d.get("data", d)
def node_ref(node_id):  # atlas node id -> relationship endpoint
    return node_id if node_id.startswith("investor:") else "company:" + node_id
rels = json.load(open(f"{REPO}/data/relationships.json"))
by_key = {}
for r in rels:
    for k in ("from", "to"): pass
    a = r["from"].split(":", 1)[1] if r["from"].startswith("company:") else r["from"]
    b = r["to"].split(":", 1)[1] if r["to"].startswith("company:") else r["to"]
    by_key[f"{r['type']}__{a}__{b}"] = r
applied = 0
for key, d in docs.items():
    r = by_key.get(key)
    if not r: print("no relationship for", key); continue
    r["verified_by"] = {f: d.get(f) for f in ("research_team", "siddhi", "ward") if d.get(f)}
    applied += 1
json.dump(rels, open(f"{REPO}/data/relationships.json", "w"), indent=2, ensure_ascii=False); open(f"{REPO}/data/relationships.json", "a").write("\n")
print(f"applied {applied} verification documents")
