#!/usr/bin/env python3
"""
Builds the companies + investors graph for the 3D atlas, plus the people
behind each company for its org chart.

Output: graph3d_data.json -> {categories, parent_industry_meta, nodes, links, people, functions, stats}

Every company carries a `roles` list (single source of truth, stored on the
record itself since the 2026-09-05 import of Siddhi's curated lists). A
company can hold several roles -- e.g. AECOM is a civil/land engineer, an
industrial developer AND a general contractor; TeraWulf is a crypto-mining
pivot AND typed "Neocloud" on Siddhi's sheet -- and the atlas renders those
as multi-colour nodes. The first role by ROLE_PRIORITY is the node's
primary tier (its colour body and its invisible layout anchor).
"""
import json, glob, os, re, sys
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from build_talent_flows import flows as talent_flows

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
COMPANIES_DIR = os.path.join(REPO, "data/companies")
INVESTORS_DIR = os.path.join(REPO, "data/investors")
PEOPLE_DIR = os.path.join(REPO, "data/people")

# Company departments a title is filed under (derived on the person record as
# `function`, see docs/schema.md). Order = column order in the org chart.
FUNCTIONS = ["Executive leadership", "Development & Real Estate", "Sales & Leasing",
             "Pre-Construction & Cost", "Construction & Delivery", "Energy & Utilities",
             "Design & Engineering", "Strategy, Finance & Investment", "Operations & Facilities",
             "Procurement & Supply Chain", "Legal, People & Support", "Unclassified"]

# Order matters: legend order, anchor order, and primary-role priority.
# Colours validated as a 9-colour CVD-safe set on the dark surface (the one
# remaining pink<->green warning sits in the legal 6-8 band because every
# node has a direct label on hover/focus).
CATS = {
    "hyperscaler":        {"name": "Hyperscaler",                          "color": "#d97706", "adjacent": False},
    "neocloud":           {"name": "NeoCloud / AI Infra",                  "color": "#16a34a", "adjacent": False},
    "cryptomining":       {"name": "Cryptomining pivot",                   "color": "#db2777", "adjacent": False},
    "developer_operator": {"name": "Data Center Developer / Operator",     "color": "#0891b2", "adjacent": False},
    "energy_developer":   {"name": "Energy developer / utility",           "color": "#b45309", "adjacent": True},
    "general_contractor": {"name": "General contractor",                   "color": "#2563eb", "adjacent": True},
    "civil_land_engineering":         {"name": "Civil / land engineering",  "color": "#dc2626", "adjacent": True},
    "industrial_logistics_developer": {"name": "Industrial developer",              "color": "#4d7c0f", "adjacent": True},
    "real_estate_developer":          {"name": "Real estate developer",             "color": "#64748b", "adjacent": True},
    "investor":           {"name": "Investor",                             "color": "#9333ea", "adjacent": False},
}
ROLE_PRIORITY = [c for c in CATS if c != "investor"]

def primary_role(roles):
    for r in ROLE_PRIORITY:
        if r in roles: return r
    return roles[0] if roles else "developer_operator"

# `parent_industry` says WHY a company is in the data center business:
# its own dedicated business ("pure_play" -- direct-tap recruiting pool),
# or one arm of a broader real estate / energy / telecom / construction /
# conglomerate business (needs a closer look at what a candidate does).
PARENT_INDUSTRY_META = {
    "pure_play":               {"name": "Pure-play data center company",            "note": "Data centers are the company's own dedicated business."},
    "real_estate":             {"name": "Real estate / industrial developer",       "note": "A property developer or REIT with a data center arm (e.g. Prologis, Panattoni)."},
    "energy_utilities":        {"name": "Energy / utility company",                 "note": "An energy or power company expanding into data center development."},
    "telecom":                 {"name": "Telecom / network operator",               "note": "A telecom company expanding into data center development."},
    "construction_engineering":{"name": "Construction / engineering / consultancy", "note": "A GC, EPC, or engineering/consultancy firm with a data center practice."},
    "diversified_conglomerate":{"name": "Diversified conglomerate",                 "note": "A diversified holding company or alt-asset manager with a data center arm."},
}

def line_style(rtype, status, confidence):
    """How the atlas draws an edge: solid / dashed / dotted. Acquisitions
    encode status (completed / announced / terminated); every other edge
    encodes confidence (high = solid, anything less = dashed = verify)."""
    st = (status or "").lower()
    if any(w in st for w in ("terminated", "rejected", "withdrawn", "abandoned", "cancelled")): return "dotted"
    if rtype == "acquired":
        return "solid" if "completed" in st else "dashed"
    if rtype in ("contractor_for", "supplies_power_to", "site_partner") and any(w in st for w in ("announced", "mou", "proposed", "planned")):
        return "dashed"  # not yet delivering
    return "solid" if (confidence or "").lower() == "high" else "dashed"

def load_json(path):
    with open(path) as f:
        return json.load(f)

nodes, node_ids = [], set()
company_files = sorted(glob.glob(os.path.join(COMPANIES_DIR, "*.json")))
for path in company_files:
    d = load_json(path)
    roles = [r for r in d["roles"] if r in CATS]  # every record carries roles (seeded 2026-09-05)
    if not roles:
        raise SystemExit(f"{path}: no recognised role in {d['roles']}")
    parent_industry = d.get("parent_industry", "pure_play")
    nodes.append({
        "id": d["id"], "name": d["name"], "kind": "company",
        "category": primary_role(roles), "roles": roles,
        "is_adjacent_only": all(CATS[r]["adjacent"] for r in roles),
        "parent_industry": parent_industry, "is_pure_play": parent_industry == "pure_play",
        "industry_role": d.get("industry_role"), "headquarters": d.get("headquarters"),
        "founded": d.get("founded"), "website": d.get("website"), "linkedin": d.get("linkedin"),
        "headcount": d.get("headcount"), "description": d.get("description"),
        "tags": d.get("tags", []), "aliases": d.get("aliases", []),
        "hyperscale_focus": d.get("hyperscale_focus"), "capacity_mw": d.get("capacity_mw"),
        "dc_exposure_level": d.get("dc_exposure_level"), "source_lists": d.get("source_lists", []),
        "list_attributes": d.get("list_attributes", {}),
        "notes": d.get("notes"), "sources": d.get("sources", []),
    })
    node_ids.add(d["id"])

rel_path = os.path.join(REPO, "data/relationships.json")
relationships = load_json(rel_path) if os.path.exists(rel_path) else []
# investor backing confidence lives on the invested_in relationship
backing_rel = {(r["from"].split(":", 1)[-1], r["to"].split(":", 1)[-1]): r
               for r in relationships if r.get("type") == "invested_in"}

investor_files = sorted(glob.glob(os.path.join(INVESTORS_DIR, "*.json")))
links = []
for path in investor_files:
    d = load_json(path)
    valid = [c for c in (d.get("investments") or []) if c in node_ids]
    # investor nodes live in their own id space ("investor:<id>") because six
    # names are both a company and a strategic investor (Google, NVIDIA,
    # Galaxy Digital, Actis, GI Partners, Generate Capital)
    nodes.append({
        "id": f"investor:{d['id']}", "record_id": d["id"], "name": d["name"], "kind": "investor", "category": "investor",
        "roles": ["investor"], "investor_type": d.get("investor_type"), "hq": d.get("hq"),
        "aum": d.get("aum"), "investments": valid, "notable_deals": d.get("notable_deals"),
        "notes": d.get("notes"), "sources": d.get("sources", []),
    })
    for cid in valid:
        rel = backing_rel.get((d["id"], cid), {})
        links.append({"source": f"investor:{d['id']}", "target": cid, "type": "invested_in",
                      "confidence": rel.get("confidence"), "style": line_style("invested_in", None, rel.get("confidence")),
                      "detail": rel.get("detail"), "sources": rel.get("sources", []),
                      "verified_by": rel.get("verified_by") or {}})

# company<->company (and investor<->investor) deal edges live in
# data/relationships.json: acquisitions, tenant/lease relationships, JVs.
# Only edges whose two endpoints are both nodes in this graph are emitted.
DEAL_TYPES = {"acquired", "tenant_of", "jv_partner",
              # adjacent industry -> data-center core (added 2026-09-08)
              "contractor_for", "supplies_power_to", "site_partner"}
all_ids = {n["id"] for n in nodes}
deal_edges = 0
if True:
    for r in relationships:
        if r.get("type") not in DEAL_TYPES: continue
        # "company:x" -> node "x"; "investor:x" -> node "investor:x"
        node_ref = lambda ref: ref.split(":", 1)[-1] if ref.startswith("company:") else ref
        src_id, dst_id = node_ref(r["from"]), node_ref(r["to"])
        if src_id in all_ids and dst_id in all_ids:
            links.append({"source": src_id, "target": dst_id, "type": r["type"],
                          "detail": r.get("detail"), "status": r.get("status"),
                          "confidence": r.get("confidence"), "sources": r.get("sources", []),
                          "verified_by": r.get("verified_by") or {},
                          "style": line_style(r["type"], r.get("status"), r.get("confidence"))})
            deal_edges += 1

# people, grouped by the company they work at today. Only the fields the org
# chart needs -- never email, phone, or compensation (those stay in Clockwork).
people = {}
people_count = 0
for path in sorted(glob.glob(os.path.join(PEOPLE_DIR, "*.json"))):
    d = load_json(path)
    cid = d.get("current_company_id")
    if cid not in node_ids: continue
    current = [c for c in d.get("career", []) if c.get("current") and c.get("company")]
    norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
    here = norm(d.get("current_company"))
    past = [{"company": c["company"], "title": c.get("title"), "start": c.get("start"), "end": c.get("end"),
             "same_employer": bool(here) and (norm(c["company"]) == here or here in norm(c["company"]) or norm(c["company"]) in here)}
            for c in d.get("career", []) if c.get("company") and not c.get("current")]
    people.setdefault(cid, []).append({
        "id": d["id"], "name": d["name"], "title": d.get("current_title"),
        "function": d.get("function") or "Unclassified", "function_source": d.get("function_source"),
        "rank": d.get("seniority_rank", 5), "seniority": d.get("seniority_label"),
        "location": d.get("location"), "loc": d.get("location_norm"), "linkedin": d.get("linkedin"),
        "department": d.get("department"), "do_not_contact": bool(d.get("do_not_contact")),
        "since": (current[0].get("start") if current else None), "past": past,
    })
    people_count += 1
# talent flows (scripts/build_talent_flows.py): previous employer -> current employer
moves, recent = talent_flows()
move_by_person = {m["person_id"]: m for m in moves}
recent_ids = {m["person_id"] for m in recent}
hires_from, alumni_at = {}, {}   # company -> Counter of names
for m in moves:
    hires_from.setdefault(m["to_id"], {}); hires_from[m["to_id"]][m["from_name"]] = hires_from[m["to_id"]].get(m["from_name"], 0) + 1
    if m["from_id"]:
        alumni_at.setdefault(m["from_id"], {}); alumni_at[m["from_id"]][m["to_name"]] = alumni_at[m["from_id"]].get(m["to_name"], 0) + 1
flow_pairs = {}
for m in moves:
    if m["from_id"] and m["from_id"] in node_ids:
        flow_pairs.setdefault((m["from_id"], m["to_id"]), []).append(m["person"])
for (a, b), names in flow_pairs.items():
    links.append({"source": a, "target": b, "type": "talent_flow", "style": "solid", "count": len(names),
                  "detail": f"{len(names)} moved {a} -> {b}: " + ", ".join(sorted(names)[:8]) + (" …" if len(names) > 8 else "")})
for cid, ppl in people.items():
    ppl.sort(key=lambda x: (x["rank"], x["name"]))
    for p in ppl:
        m = move_by_person.get(p["id"])
        p["prev"] = m["from_name"] if m else None
        p["prev_tracked"] = bool(m and m["from_id"])
        p["recent"] = p["id"] in recent_ids
    node = next(n for n in nodes if n["id"] == cid)
    node["people_count"] = len(ppl)
    node["hires_from"] = sorted(hires_from.get(cid, {}).items(), key=lambda kv: -kv[1])[:12]
    node["alumni_at"] = sorted(alumni_at.get(cid, {}).items(), key=lambda kv: -kv[1])[:12]
    node["recent_joiners"] = sum(1 for p in ppl if p["recent"])

# every link gets a stable key -- the id of its verification document in the
# atlas's shared store (scripts/pull_verifications.py reads them back)
for l in links:
    l["key"] = f"{l['type']}__{l['source']}__{l['target']}"

# legend counts = how many nodes HOLD each role (a multi-role company counts once per role)
role_counts = {c: 0 for c in CATS}
for n in nodes:
    for r in n["roles"]:
        role_counts[r] += 1
categories_out = [{"id": cid, "name": m["name"], "color": m["color"], "adjacent": m["adjacent"],
                   "count": role_counts[cid]} for cid, m in CATS.items()]

pi_counts = {}
for n in nodes:
    if n["kind"] == "company":
        pi_counts[n["parent_industry"]] = pi_counts.get(n["parent_industry"], 0) + 1

dc_companies = sum(1 for n in nodes if n["kind"] == "company" and not n["is_adjacent_only"])
adjacent_only = sum(1 for n in nodes if n["kind"] == "company" and n["is_adjacent_only"])
multi_role = sum(1 for n in nodes if n["kind"] == "company" and len(n["roles"]) > 1)

out = {
    "categories": categories_out,
    "parent_industry_meta": [{"id": pid, "name": m["name"], "note": m["note"], "count": pi_counts.get(pid, 0)}
                             for pid, m in PARENT_INDUSTRY_META.items()],
    "nodes": nodes, "links": links, "people": people, "functions": FUNCTIONS,
    "stats": {"people": people_count, "companies_with_people": len(people),
              "moves": len(moves), "flow_pairs": len(flow_pairs), "recent_joiners": len(recent),
              "companies": len(company_files), "dc_companies": dc_companies,
              "adjacent_companies": adjacent_only, "multi_role_companies": multi_role,
              "investors": len(investor_files), "links": len(links), "deal_links": deal_edges,
              "generated": date.today().isoformat()},
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph3d_data.json")
with open(out_path, "w") as f:
    json.dump(out, f)

print("companies:", len(company_files), "| DC-tier:", dc_companies, "| adjacent-only:", adjacent_only,
      "| multi-role:", multi_role)
print("investors:", len(investor_files), "| links:", len(links), "| of which deal links:", deal_edges)
print("people:", people_count, "at", len(people), "companies", "| talent moves:", len(moves), "| flow pairs between tracked companies:", len(flow_pairs), "| recent joiners:", len(recent))
style_counts = {}
for l in links: style_counts[(l["type"], l["style"])] = style_counts.get((l["type"], l["style"]), 0) + 1
print("line styles:", style_counts)
print("role counts:", role_counts)
print("wrote:", out_path, os.path.getsize(out_path), "bytes")
