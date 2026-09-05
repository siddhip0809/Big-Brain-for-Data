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

# The CRM's "Hyperscaler" tag turned out to mean "this company's people
# have worked on hyperscaler-related projects" (Clockwork's "Organisation
# Experience" tag), not "this company IS a hyperscaler" — it was firing
# on ~94 companies, nearly all of them data center developers/operators
# who build and run facilities FOR hyperscalers rather than being one
# themselves. Per Siddhi's correction (2026-09-05): a true hyperscaler is
# one of the handful of companies that owns and operates its own global
# hyperscale cloud/compute platform. That's a short, explicit allowlist,
# not a tag — everyone else who was tag-Hyperscaler falls back to
# Developer/Operator (or NeoCloud/Cryptomining if they qualify for those).
TRUE_HYPERSCALER_IDS = {"aws", "google", "microsoft", "meta", "apple"}

# Same problem showed up in the "Neo Clouds/AI Infra" tag: it was firing on
# companies (Computacenter, Datum Datacentres, BGO Data Centre) that are a
# regional colocation specialist, a UK colo operator, and a real-estate
# fund's DC vehicle respectively -- not AI-cloud/neocloud businesses. Moved
# to an explicit allowlist of confirmed AI-cloud / neocloud operators.
TRUE_NEOCLOUD_IDS = {
    "iren", "nebius", "crusoe", "openai", "together-ai",
    "applied-digital", "sesterce",
    "bit-digital",  # crypto-mining pivot, but the most complete one -- fully
                    # exited mining, so treated like IREN/Applied Digital below
}

# Per Siddhi's note (2026-09-05): several US Bitcoin/crypto mining companies
# have pivoted into AI/HPC data center hosting, since the power, cooling, and
# high-density rack infrastructure required is largely the same. These are
# an explicit allowlist too, same reasoning as the two above -- and checked
# AFTER neocloud/hyperscaler, so a company that's fully pivoted to being an
# AI-cloud business (IREN, Applied Digital, Bit Digital) stays classified
# there; this tier is for ones still closer to "data center host with a
# crypto-mining legacy" than "AI-cloud platform." A dedicated 2026-09-05
# research round confirmed the rest of this list beyond the original three.
TRUE_CRYPTOMINING_IDS = {
    "terawulf", "hut-8", "core-scientific",
    "cipher-mining", "riot-platforms", "mara-holdings", "cleanspark",
    "bitfarms", "bitdeer-technologies", "sphere-3d", "digihost",
    "soluna-holdings", "mawson-infrastructure-group",
}

def classify_company(company_id, tags):
    if company_id in TRUE_NEOCLOUD_IDS:
        return "neocloud"
    if company_id in TRUE_HYPERSCALER_IDS:
        return "hyperscaler"
    if company_id in TRUE_CRYPTOMINING_IDS:
        return "cryptomining"
    return "developer_operator"

# Within Developer/Operator (and, in principle, any tier), a company's
# `parent_industry` says WHY it's in the data center business: its own
# dedicated business ("pure_play" -- direct-tap recruiting pool), or an
# arm of a broader real estate, energy/utility, telecom, or construction/
# engineering company (needs a closer look at what a candidate actually
# works on), or some other diversified conglomerate/holding company.
PARENT_INDUSTRY_META = {
    "pure_play":               {"name": "Pure-play data center company",            "note": "Data centers are the company's own dedicated business."},
    "real_estate":             {"name": "Real estate / industrial developer",       "note": "A property developer or REIT with a data center arm (e.g. Prologis, Panattoni)."},
    "energy_utilities":        {"name": "Energy / utility company",                 "note": "An energy or power company expanding into data center development."},
    "telecom":                 {"name": "Telecom / network operator",               "note": "A telecom company expanding into data center development."},
    "construction_engineering":{"name": "Construction / engineering / consultancy", "note": "A GC, EPC, or engineering/consultancy firm with a data center practice."},
    "diversified_conglomerate":{"name": "Diversified conglomerate",                 "note": "A diversified holding company or alt-asset manager with a data center arm."},
}

def load_json(path):
    with open(path) as f:
        return json.load(f)

nodes = []
node_ids = set()

company_files = sorted(glob.glob(os.path.join(COMPANIES_DIR, "*.json")))
for path in company_files:
    d = load_json(path)
    cat = classify_company(d["id"], d.get("tags"))
    parent_industry = d.get("parent_industry") or "pure_play"
    nodes.append({
        "id": d["id"],
        "name": d["name"],
        "kind": "company",
        "category": cat,
        "parent_industry": parent_industry,
        "is_pure_play": parent_industry == "pure_play",
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

parent_industry_counts = {}
for n in nodes:
    if n["kind"] == "company":
        parent_industry_counts[n["parent_industry"]] = parent_industry_counts.get(n["parent_industry"], 0) + 1

out = {
    "categories": categories_out,
    "parent_industry_meta": [
        {"id": pid, "name": meta["name"], "note": meta["note"], "count": parent_industry_counts.get(pid, 0)}
        for pid, meta in PARENT_INDUSTRY_META.items()
    ],
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
