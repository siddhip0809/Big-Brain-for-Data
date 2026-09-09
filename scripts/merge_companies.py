#!/usr/bin/env python3
"""Merge one company record into another (duplicates such as "NTT" and
"NTT Global Data Centers"). Usage:
    python3 scripts/merge_companies.py <keep_id> <drop_id> [--apply]
Keeps <keep_id>: fills its empty fields from the dropped record, unions
aliases/tags/source_lists/sources, merges list_attributes and capacity_mw,
adds the dropped name as an alias, repoints people, relationships and
investor portfolios, and deletes the dropped file. Dry run unless --apply."""
import json, glob, os, sys
from datetime import date
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
keep_id, drop_id = sys.argv[1], sys.argv[2]; APPLY = "--apply" in sys.argv
kp, dp = f"{REPO}/data/companies/{keep_id}.json", f"{REPO}/data/companies/{drop_id}.json"
keep, drop = json.load(open(kp)), json.load(open(dp))

for k, v in drop.items():
    if k in ("id", "name", "type"): continue
    if isinstance(v, list):
        keep[k] = list(dict.fromkeys((keep.get(k) or []) + v))
    elif isinstance(v, dict):
        merged = dict(keep.get(k) or {}); [merged.setdefault(kk, vv) for kk, vv in v.items()]; keep[k] = merged
    elif keep.get(k) in (None, "", [], {}) and v not in (None, ""):
        keep[k] = v
for alias in [drop["name"]] + (drop.get("aliases") or []):
    if alias != keep["name"] and alias not in keep["aliases"]: keep["aliases"].append(alias)
keep["notes"] = ((keep.get("notes") or "") + f"\n\nMerged {date.today()}: absorbed duplicate record '{drop['name']}' ({drop_id}).").strip()
keep["last_updated"] = str(date.today())

touched = {"people": 0, "relationships": 0, "investors": 0}
people = []
for f in glob.glob(f"{REPO}/data/people/*.json"):
    p = json.load(open(f))
    if p.get("current_company_id") == drop_id: p["current_company_id"] = keep_id; people.append((f, p)); touched["people"] += 1
# repoint; drop only a repointed edge that now exactly duplicates an existing one
rels = json.load(open(f"{REPO}/data/relationships.json"))
existing = {(r["from"], r["to"], r["type"]) for r in rels}
out = []
for r in rels:
    hit = False
    for k in ("from", "to"):
        if r[k] == f"company:{drop_id}": r[k] = f"company:{keep_id}"; hit = True
    if hit:
        touched["relationships"] += 1
        if (r["from"], r["to"], r["type"]) in existing: continue
        existing.add((r["from"], r["to"], r["type"]))
    out.append(r)
investors = []
for f in glob.glob(f"{REPO}/data/investors/*.json"):
    inv = json.load(open(f))
    if drop_id in (inv.get("investments") or []):
        inv["investments"] = list(dict.fromkeys(keep_id if x == drop_id else x for x in inv["investments"])); investors.append((f, inv)); touched["investors"] += 1

print("keep:", json.dumps({k: keep[k] for k in ("name", "aliases", "headquarters", "website", "parent_industry", "roles", "source_lists", "hyperscale_focus")}, ensure_ascii=False))
print("repointed:", touched, "| relationships:", len(out), "of", len(rels))
if APPLY:
    dump = lambda path, obj: (json.dump(obj, open(path, "w"), indent=2, ensure_ascii=False), open(path, "a").write("\n"))
    dump(kp, keep)
    for f, p in people: dump(f, p)
    for f, inv in investors: dump(f, inv)
    dump(f"{REPO}/data/relationships.json", out)
    os.remove(dp)
    print("APPLIED — removed", dp)
else: print("dry run")
