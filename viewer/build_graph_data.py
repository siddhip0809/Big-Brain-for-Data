import json, os, glob

REPO = "/home/user/Big-Brain-for-Data"
OUT = "/tmp/claude-0/-home-user-Big-Brain-for-Data/9bbb68cd-c59d-5396-8d24-4524d326a6f6/scratchpad/graph_data.json"

nodes = []
node_index = {}

def add_node(n):
    nodes.append(n)
    node_index[n["id"]] = n

# Companies
for path in sorted(glob.glob(os.path.join(REPO, "data/companies/*.json"))):
    c = json.load(open(path))
    add_node({
        "id": f"company:{c['id']}",
        "kind": "hub",
        "group": "company",
        "label": c["name"],
        "description": c.get("description"),
        "industry_role": c.get("industry_role"),
        "tags": c.get("tags", []),
        "notes": c.get("notes"),
    })

# Investors
for path in sorted(glob.glob(os.path.join(REPO, "data/investors/*.json"))):
    i = json.load(open(path))
    add_node({
        "id": f"investor:{i['id']}",
        "kind": "hub",
        "group": "investor",
        "label": i["name"],
        "investor_type": i.get("investor_type"),
        "investments": i.get("investments", []),
        "notes": i.get("notes"),
    })

# People
cluster_map = {"pure-data-centers": "pure", "stack-infrastructure": "stack"}
for path in sorted(glob.glob(os.path.join(REPO, "data/people/*.json"))):
    p = json.load(open(path))
    pipeline = p.get("pipeline", [])
    cluster = None
    for entry in pipeline:
        cc = entry.get("client_company")
        if cc in cluster_map:
            cluster = cluster_map[cc]
            break
    seniority = (p.get("seniority") or "")
    size_bump = 0
    sl = seniority.lower()
    if "vice president" in sl or "vp" in sl:
        size_bump = 2.5
    elif "director" in sl:
        size_bump = 2
    elif "senior" in sl or "sr" in sl or "sr." in sl:
        size_bump = 1
    add_node({
        "id": f"person:{p['id']}",
        "kind": "person",
        "group": cluster or "other",
        "label": p["name"],
        "current_title": p.get("current_title"),
        "current_company": p.get("current_company"),
        "location": p.get("location"),
        "seniority": p.get("seniority"),
        "industry_segment": p.get("industry_segment"),
        "career_history": p.get("career_history"),
        "do_not_contact": p.get("do_not_contact", False),
        "pipeline": pipeline,
        "size_bump": size_bump,
    })

# Relationships -> links
rels = json.load(open(os.path.join(REPO, "data/relationships.json")))
links = []
for r in rels:
    src, dst = r["from"], r["to"]
    if src in node_index and dst in node_index:
        links.append({
            "source": src,
            "target": dst,
            "type": r["type"],
            "detail": r.get("detail"),
        })

data = {"nodes": nodes, "links": links}
with open(OUT, "w") as f:
    json.dump(data, f, ensure_ascii=False)

print(f"nodes: {len(nodes)}  links: {len(links)}")
print(f"size: {os.path.getsize(OUT)/1024:.1f} KB")
