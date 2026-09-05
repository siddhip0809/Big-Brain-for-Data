#!/usr/bin/env python3
"""
Builds a companies + investors ONLY graph for the 3D atlas prototype
(step-back per user request: strip out people for now, keep companies
and private-equity backers, and make the company "tiers" visually
distinct: Hyperscaler / NeoCloud / Developer-Operator / Cryptomining).

Output: graph3d_data.json -> {categories:[...], nodes:[...], links:[...]}
"""
import json, glob, os

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
COMPANIES_DIR = os.path.join(REPO, "data/companies")
INVESTORS_DIR = os.path.join(REPO, "data/investors")

CATS = {
    "neocloud":           {"name": "NeoCloud / AI Infra",             "color": "#16a34a"},
    "hyperscaler":        {"name": "Hyperscaler",                     "color": "#d97706"},
    "cryptomining":       {"name": "Cryptomining",                    "color": "#db2777"},
    "developer_operator": {"name": "Data Center Developer / Operator","color": "#0891b2"},
    "investor":           {"name": "Investor",                       "color": "#9333ea"},
}

def classify_company(tags):
    tagset = set(tags or [])
    if "Neo Clouds/AI Infra" in tagset:
        return "neocloud"
    if "Hyperscaler" in tagset or "hyperscale" in tagset:
        return "hyperscaler"
    if any("crypto" in t.lower() for t in tagset):
        return "cryptomining"
    return "developer_operator"

def load_json(path):
    with open(path) as f:
        return json.load(f)

nodes = []
node_ids = set()

company_files = sorted(glob.glob(os.path.join(COMPANIES_DIR, "*.json")))
for path in company_files:
    d = load_json(path)
    cat = classify_company(d.get("tags"))
    nodes.append({
        "id": d["id"],
        "name": d["name"],
        "kind": "company",
        "category": cat,
        "industry_role": d.get("industry_role"),
        "headquarters": d.get("headquarters"),
        "founded": d.get("founded"),
        "website": d.get("website"),
        "description": d.get("description"),
        "tags": d.get("tags", []),
        "notes": d.get("notes"),
        "sources": d.get("sources", []),
    })
    node_ids.add(d["id"])

investor_files = sorted(glob.glob(os.path.join(INVESTORS_DIR, "*.json")))
investor_ids = set()
links = []
for path in investor_files:
    d = load_json(path)
    investor_ids.add(d["id"])
    investments = d.get("investments") or []
    valid_investments = [c for c in investments if c in node_ids]
    nodes.append({
        "id": d["id"],
        "name": d["name"],
        "kind": "investor",
        "category": "investor",
        "investor_type": d.get("investor_type"),
        "hq": d.get("hq"),
        "aum": d.get("aum"),
        "investments": valid_investments,
        "notable_deals": d.get("notable_deals"),
        "notes": d.get("notes"),
        "sources": d.get("sources", []),
    })
    for cid in valid_investments:
        links.append({"source": d["id"], "target": cid, "type": "invested_in"})

# category counts
counts = {}
for n in nodes:
    counts[n["category"]] = counts.get(n["category"], 0) + 1

categories_out = []
for cid, meta in CATS.items():
    categories_out.append({
        "id": cid,
        "name": meta["name"],
        "color": meta["color"],
        "count": counts.get(cid, 0),
    })

out = {
    "categories": categories_out,
    "nodes": nodes,
    "links": links,
    "stats": {
        "companies": len(company_files),
        "investors": len(investor_files),
        "links": len(links),
    },
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph3d_data.json")
with open(out_path, "w") as f:
    json.dump(out, f)

print("companies:", len(company_files))
print("investors:", len(investor_files))
print("links:", len(links))
print("category counts:", counts)
print("wrote:", out_path, os.path.getsize(out_path), "bytes")
