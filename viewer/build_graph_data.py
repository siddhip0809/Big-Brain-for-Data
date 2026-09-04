"""
Builds a nested tree (root -> company -> department -> person, with the
investor as an extra child of its company) for the radial-tree graph viewer.

People whose current employer isn't one of the classified data-center
companies are grouped under one "Contractors & Consultants" branch,
split the same way by department.
"""
import json, os, glob

REPO = "/home/user/Big-Brain-for-Data"
OUT = "/tmp/claude-0/-home-user-Big-Brain-for-Data/9bbb68cd-c59d-5396-8d24-4524d326a6f6/scratchpad/tree_data.json"

companies = {}
for path in glob.glob(os.path.join(REPO, "data/companies/*.json")):
    c = json.load(open(path))
    companies[c["id"]] = c

investors = {}
for path in glob.glob(os.path.join(REPO, "data/investors/*.json")):
    i = json.load(open(path))
    investors[i["id"]] = i

people = [json.load(open(p)) for p in glob.glob(os.path.join(REPO, "data/people/*.json"))]

DEPT_KEY = {"Sales": "sales", "Development": "development"}

def person_node(p):
    return {
        "id": f"person:{p['id']}",
        "kind": "person",
        "label": p["name"],
        "department": p["department"],
        "current_title": p.get("current_title"),
        "current_company": p.get("current_company"),
        "location": p.get("location"),
        "seniority": p.get("seniority"),
        "industry_segment": p.get("industry_segment"),
        "career_history": p.get("career_history"),
        "do_not_contact": p.get("do_not_contact", False),
        "pipeline": p.get("pipeline", []),
    }

def dept_node(dept_label, dept_people):
    return {
        "id": f"dept:{dept_label}:" + "-".join(sorted(p['id'] for p in dept_people))[:8],
        "kind": "department",
        "label": dept_label,
        "department": dept_label,
        "children": [person_node(p) for p in dept_people],
    }

# group people by (company bucket)
by_company = {}
for p in people:
    cid = p.get("current_company_id") or "__other__"
    by_company.setdefault(cid, []).append(p)

# Client companies we track (Pure, STACK) always get a node, even with zero
# current employees among these candidates -- so e.g. the investor link
# (Oaktree -> Pure Data Centers) still has a company node to attach to.
for cid in ("pure-data-centers", "stack-infrastructure"):
    by_company.setdefault(cid, [])

def company_children(cid, bucket_people):
    depts = {}
    for p in bucket_people:
        depts.setdefault(p["department"], []).append(p)
    children = []
    for dept_label in ("Sales", "Development"):
        if dept_label in depts:
            dn = dept_node(dept_label, depts[dept_label])
            dn["id"] = f"dept:{cid}:{dept_label}"
            children.append(dn)
    return children

company_nodes = []
for cid, bucket_people in by_company.items():
    if cid == "__other__":
        continue
    c = companies.get(cid, {"id": cid, "name": cid})
    node = {
        "id": f"company:{cid}",
        "kind": "company",
        "label": c.get("name", cid),
        "industry_role": c.get("industry_role"),
        "description": c.get("description"),
        "tags": c.get("tags", []),
        "notes": c.get("notes"),
        "children": company_children(cid, bucket_people),
    }
    # attach investor(s) as an extra child leaf
    for inv_id, inv in investors.items():
        if cid in inv.get("investments", []):
            node["children"].append({
                "id": f"investor:{inv_id}",
                "kind": "investor",
                "label": inv["name"],
                "investor_type": inv.get("investor_type"),
                "investments": inv.get("investments", []),
                "notes": inv.get("notes"),
                "children": [],
            })
    company_nodes.append(node)

# sort real companies by total people descending
def count_leaves(n):
    if not n.get("children"):
        return 1
    return sum(count_leaves(c) for c in n["children"])

company_nodes.sort(key=lambda n: -count_leaves(n))

# "Contractors & Consultants" aggregate bucket
other_people = by_company.get("__other__", [])
other_node = {
    "id": "company:contractors-consultants",
    "kind": "company",
    "label": "Contractors & Consultants",
    "industry_role": "aggregate: general contractors, cost consultants, engineering firms",
    "description": (
        "People whose current employer builds or advises on data centers "
        "(general contractors, cost consultants, engineering firms) rather "
        "than owning/operating them. Grouped together here rather than given "
        "individual company nodes; their real current employer is still on "
        "each person's own record."
    ),
    "tags": ["aggregate"],
    "notes": None,
    "children": company_children("__other__", other_people),
}

root = {
    "id": "root",
    "kind": "root",
    "label": "Data Center Companies",
    "children": company_nodes + [other_node],
}

with open(OUT, "w") as f:
    json.dump(root, f, ensure_ascii=False)

total_people = count_leaves(root)
print(f"companies: {len(company_nodes)}  + aggregate bucket ({len(other_people)} people)")
print(f"total people in tree: {total_people}")
print(f"size: {os.path.getsize(OUT)/1024:.1f} KB")
