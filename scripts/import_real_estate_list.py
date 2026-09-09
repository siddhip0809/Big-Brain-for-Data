#!/usr/bin/env python3
"""Import Siddhi's "Real Estate Development USA" list (2026-09-09) as the
adjacent role `real_estate_developer`. Existing companies gain the role and
the sheet's columns; new ones are created. Dry run unless --apply.
Usage: python3 scripts/import_real_estate_list.py <xlsx> [--apply]"""
import json, glob, os, re, sys, collections
from datetime import date
import openpyxl
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APPLY = "--apply" in sys.argv; XLSX = [a for a in sys.argv[1:] if a.endswith(".xlsx")][0]
TODAY = str(date.today()); LIST = "Real Estate Developers USA"; ROLE = "real_estate_developer"

norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
STRIP = re.compile(r"\b(inc|llc|ltd|limited|corp|corporation|company|co|group|plc|holdings|the|us|usa|properties|property|realty|real estate|partners|development|developers|industrial|logistics|trust|reit)\b\.?", re.I)
loose = lambda x: re.sub(r"[^a-z0-9]", "", STRIP.sub("", (x or "")).lower())
slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower().strip()).strip("-")
clean = lambda v: (v.strip() or None) if isinstance(v, str) else v
NOT_SAME = {("bridge industrial or blp - bridge logistics properties", "bridge-industrial")}  # (sheet name, id) pairs to keep apart, if any

companies = {}
for f in glob.glob(f"{REPO}/data/companies/*.json"):
    c = json.load(open(f)); companies[c["id"]] = c
by_norm, by_loose = {}, collections.defaultdict(set)
for cid, c in companies.items():
    for nm in [c["name"]] + (c.get("aliases") or []):
        by_norm[norm(nm)] = cid
        if len(loose(nm)) >= 4: by_loose[loose(nm)].add(cid)
def resolve(name):
    first = name.split(" OR ")[0].strip()  # "Bridge Industrial OR Blp - ..." -> first name
    for cand in (name, first):
        if norm(cand) in by_norm: return by_norm[norm(cand)]
    for cand in (name, first):
        l = loose(cand)
        if l and len(by_loose.get(l, ())) == 1: return next(iter(by_loose[l]))
    return None

ws = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)["Real Estate Development USA"]
rows = list(ws.iter_rows(values_only=True)); hdr = rows[0]; idx = {h: i for i, h in enumerate(hdr)}
col = lambda r, h: clean(r[idx[h]]) if h in idx else None
merged, created, preview = 0, 0, []
for r in rows[1:]:
    name = col(r, "Company Name")
    if not name: continue
    display = name.split(" OR ")[0].strip()
    attrs = {h: col(r, h) for h in ("Primary Scope", "Noise Category", "Multidisciplinary", "Mission Critical / DC Experience", "DC Exposure Level") if col(r, h) is not None}
    hq = ", ".join(x for x in (col(r, "HQ City"), col(r, "HQ State")) if x) or None
    cid = resolve(name)
    if cid and (name.lower(), cid) not in NOT_SAME:
        c = companies[cid]
        if ROLE not in c["roles"]: c["roles"].append(ROLE)
        if LIST not in c.setdefault("source_lists", []): c["source_lists"].append(LIST)
        c.setdefault("list_attributes", {})[LIST] = attrs
        for k, v in (("website", col(r, "Website")), ("linkedin", col(r, "LinkedIn")), ("headcount", col(r, "Head Count")), ("headquarters", hq)):
            if v and not c.get(k): c[k] = v
        if not c.get("dc_exposure_level") and attrs.get("DC Exposure Level"): c["dc_exposure_level"] = attrs["DC Exposure Level"]
        if col(r, "Notes"): c["notes"] = ((c.get("notes") or "") + f"\n\nSiddhi's real-estate sheet note: {col(r, 'Notes')}").strip()
        src = f"Siddhi's Real Estate Development USA list (xlsx), imported {TODAY}"
        if src not in c["sources"]: c["sources"].append(src)
        c["last_updated"] = TODAY
        preview.append(("merge", display, "->", c["name"], "/".join(c["roles"]))); merged += 1
        if APPLY: json.dump(c, open(f"{REPO}/data/companies/{cid}.json", "w"), indent=2, ensure_ascii=False); open(f"{REPO}/data/companies/{cid}.json", "a").write("\n")
    else:
        cid = slugify(display); path = f"{REPO}/data/companies/{cid}.json"
        if os.path.exists(path): cid += "-re"; path = f"{REPO}/data/companies/{cid}.json"
        doc = {"id": cid, "type": "company", "name": display, "aliases": [a.strip() for a in name.split(" OR ")[1:] if a.strip()],
               "industry_role": "real estate developer", "headquarters": hq, "founded": None, "website": col(r, "Website"), "linkedin": col(r, "LinkedIn"),
               "headcount": col(r, "Head Count"), "description": None, "facilities": [], "financials": {}, "tags": [],
               "parent_industry": "real_estate", "roles": [ROLE], "source_lists": [LIST], "dc_exposure_level": attrs.get("DC Exposure Level"),
               "list_attributes": {LIST: attrs},
               "notes": (f"Siddhi's real-estate sheet note: {col(r, 'Notes')}" if col(r, "Notes") else "Added from Siddhi's Real Estate Development USA list; not otherwise independently researched."),
               "sources": [f"Siddhi's Real Estate Development USA list (xlsx), imported {TODAY}"], "last_updated": TODAY}
        preview.append(("create", display)); created += 1
        if APPLY: json.dump(doc, open(path, "w"), indent=2, ensure_ascii=False); open(path, "a").write("\n")
for p in preview:
    if p[0] == "merge": print(*p)
print(f"created {created} | merged into existing {merged}")
print("APPLIED" if APPLY else "dry run")
