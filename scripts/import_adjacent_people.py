#!/usr/bin/env python3
"""Re-import the Clockwork candidates whose current employer is an
adjacent-industry company (GCs, energy developers, civil/land engineers,
industrial developers). The 2026-09-05 import kept only people at
data-center-tier employers; Siddhi asked (2026-09-09) for the others back.

Never stores email, phone or compensation. Dry run by default; --apply writes.
Usage: python3 scripts/import_adjacent_people.py [--apply] <export.xlsx>...
"""
import json, os, re, sys, glob, collections
from datetime import date
import openpyxl

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APPLY = "--apply" in sys.argv
FILES = [a for a in sys.argv[1:] if a.endswith(".xlsx")]
TODAY = str(date.today())

# which export -> which Ward Search department / project
def source_meta(path):
    base = os.path.basename(path)
    if "Sales__Main" in base:        return "Sales", "Long Term Mapping - Sales - Main List", None
    if "Precon" in base:             return "Pre-Construction", "Long Term Mapping - Precon", None
    if "Development__Main" in base:  return "Development", "Long Term Mapping - Development - Main List", None
    if "Construction__Main" in base: return "Construction", "Long Term Mapping - Construction - Main List", None
    if "Utilities__Main" in base:    return "Energy & Utilities", "Long Term Mapping - Utilities - Main List", None
    if "VP_Sales" in base:           return "Sales", "VP Sales", "Pure Data Centers"
    if "Cost_Strategy" in base:      return "Pre-Construction", "Director / Sr Director Cost Strategy", "STACK Infrastructure"
    raise SystemExit(f"unknown export: {base}")

norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
STRIP = re.compile(r"\b(inc|llc|ltd|limited|corp|corporation|company|co|group|plc|holdings|the|us|usa|construction|contractors?|engineering|engineers)\b\.?", re.I)
loose = lambda x: re.sub(r"[^a-z0-9]", "", STRIP.sub("", (x or "")).lower())
slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower().strip()).strip("-")
clean = lambda v: (v.strip() or None) if isinstance(v, str) else v

companies = {}
for f in glob.glob(f"{REPO}/data/companies/*.json"):
    c = json.load(open(f)); companies[c["id"]] = c
ADJ = {"energy_developer", "general_contractor", "civil_land_engineering", "real_estate_developer"}
adjacent_only = {cid for cid, c in companies.items() if c.get("roles") and all(r in ADJ for r in c["roles"])}
by_norm, by_loose = {}, collections.defaultdict(set)
for cid in adjacent_only:
    for nm in [companies[cid]["name"]] + (companies[cid].get("aliases") or []):
        by_norm[norm(nm)] = cid
        if loose(nm): by_loose[loose(nm)].add(cid)
def resolve(name):
    n = norm(name)
    if n in by_norm: return by_norm[n]
    l = loose(name)
    if l and len(by_loose.get(l, ())) == 1: return next(iter(by_loose[l]))
    return None

existing = {}
for f in glob.glob(f"{REPO}/data/people/*.json"):
    existing[os.path.basename(f)[:-5].rsplit("-", 1)[-1]] = f

new = merged = 0; pending = set(); per_company = collections.Counter(); unmatched = collections.Counter()
for path in FILES:
    department, project, client = source_meta(path)
    ws = openpyxl.load_workbook(path, data_only=True, read_only=True)["Candidates"]
    rows = list(ws.iter_rows(values_only=True)); idx = {h: i for i, h in enumerate(rows[0])}
    col = lambda row, h: clean(row[idx[h]]) if h in idx else None
    for row in rows[1:]:
        pid, name, company = row[idx["Person Id"]], col(row, "Name"), col(row, "Company")
        if not pid or not name or not company: continue
        cid = resolve(company)
        if not cid:
            unmatched[company] += 1; continue
        suffix = pid[:8]
        entry = {"project": project, "client_company": client, "stage": col(row, "Candidate Status"), "rank": row[idx["Rank"]],
                 "date_added": str(row[idx["Date Added"]]) if row[idx["Date Added"]] else None,
                 "date_updated": str(row[idx["Date Updated"]]) if row[idx["Date Updated"]] else None,
                 "sourced_by": col(row, "User Added"), "client_visibility_flag": col(row, "Visibility")}
        src_note = f"Clockwork export: {os.path.basename(path).split('-', 1)[-1]}, imported {TODAY}"
        if suffix in pending: merged += 1; continue  # dry run: same person on a second list
        if suffix in existing:
            p = json.load(open(existing[suffix]))
            if not any(e["project"] == project for e in p.get("pipeline", [])): p.setdefault("pipeline", []).append(entry)
            if src_note not in p["sources"]: p["sources"].append(src_note)
            if not p.get("current_company_id"): p["current_company_id"] = cid
            p["last_updated"] = TODAY
            if APPLY: json.dump(p, open(existing[suffix], "w"), indent=2, ensure_ascii=False); open(existing[suffix], "a").write("\n")
            merged += 1; continue
        location = col(row, "Summary Location") or col(row, "Located In")
        if location: location = re.sub(r"<[^>]+>", "", location).strip()
        sen = col(row, "Tag E   Seniority"); sen = None if sen in (None, "Not applicable") else sen
        seg = col(row, "Tag E   Asset Class"); seg = None if seg in (None, "Not applicable") else seg
        slug = f"{slugify(name)}-{suffix}"
        doc = {"id": slug, "type": "person", "name": name, "current_title": col(row, "Position"), "current_company": company,
               "linkedin": col(row, "LinkedIn URL"), "location": location, "seniority": sen, "industry_segment": seg,
               "career_history": col(row, "All Positions"), "do_not_contact": False, "pipeline": [entry],
               "department": department, "current_company_id": cid,
               "notes": "Works at an adjacent-industry company (GC / energy / civil / industrial); re-imported 2026-09-09 at Siddhi's request.",
               "sources": [src_note], "last_updated": TODAY}
        out = f"{REPO}/data/people/{slug}.json"
        if APPLY:
            json.dump(doc, open(out, "w"), indent=2, ensure_ascii=False); open(out, "a").write("\n")
            existing[suffix] = out
        else:
            pending.add(suffix)
        new += 1; per_company[companies[cid]["name"]] += 1

print(f"new people: {new} | merged into existing: {merged} | adjacent companies gaining people: {len(per_company)}")
print("top:", per_company.most_common(15))
print("unmatched employers (not adjacent, not resolvable):", len(unmatched), unmatched.most_common(12))
print("APPLIED" if APPLY else "dry run")
