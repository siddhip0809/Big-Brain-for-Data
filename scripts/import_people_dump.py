#!/usr/bin/env python3
"""Import a flat people dump (Id, Name, Title, Company, LinkedIn URL, Tags)
and keep only the profiles at companies already tracked in the brain.

PRIVACY: the source file carries Preferred Email and Preferred Phone. Those
columns are never read into a record — the brain stores neither (see
docs/schema.md). Compensation is likewise never stored.

These are directory-grade profiles: name, title, employer, LinkedIn, nothing
else. They are marked `record_grade: "directory"` so they can be told apart
from the Clockwork candidates, which carry career history, location and
pipeline. Dedupe is by LinkedIn handle first, then exact name at the same
employer.

Usage: python3 scripts/import_people_dump.py <dump.csv> [--apply] [--min-rank N]
       --min-rank 4 keeps Manager/Lead and above (0 = C-suite … 5 = IC)
"""
import csv, json, glob, os, re, sys, collections
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enrich_people import seniority_for, function_for            # same rules as the rest of the brain

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APPLY = "--apply" in sys.argv
MIN_RANK = int(sys.argv[sys.argv.index("--min-rank") + 1]) if "--min-rank" in sys.argv else 5
CSVP = [a for a in sys.argv[1:] if a.endswith(".csv")][0]
TODAY = str(date.today())
DROP_COLUMNS = ("Preferred Email", "Preferred Phone")            # never stored

norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
STRIP = re.compile(r"\b(inc|llc|ltd|limited|corp|corporation|company|co|group|plc|holdings|the|us|usa|construction|contractors?|data ?cent(er|re)s?|datacenters?|engineering|engineers|properties|realty|partners|technologies|technology|solutions|services|international|global)\b\.?", re.I)
loose = lambda x: re.sub(r"[^a-z0-9]", "", STRIP.sub("", (x or "")).lower())
slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower().strip()).strip("-")
handle = lambda u: (u or "").lower().rstrip("/").split("linkedin.com/in/")[-1].split("?")[0]

companies = {}
for f in glob.glob(f"{REPO}/data/companies/*.json"):
    c = json.load(open(f)); companies[c["id"]] = c
by_norm, by_loose = {}, collections.defaultdict(set)
for cid, c in companies.items():
    for nm in [c["name"]] + (c.get("aliases") or []):
        by_norm[norm(nm)] = cid
        if len(loose(nm)) >= 4: by_loose[loose(nm)].add(cid)
def resolve(name):
    k = norm(name)
    if k in by_norm: return by_norm[k]
    l = loose(name)
    if l and len(by_loose.get(l, ())) == 1: return next(iter(by_loose[l]))
    return None

seen_handle, seen_name_at = set(), set()
for f in glob.glob(f"{REPO}/data/people/*.json"):
    p = json.load(open(f))
    h = handle(p.get("linkedin"))
    if h: seen_handle.add(h)
    seen_name_at.add((norm(p["name"]), p.get("current_company_id")))

rows = list(csv.DictReader(open(CSVP, encoding="utf-8-sig")))
stats = collections.Counter(); per_company = collections.Counter(); created = []
for r in rows:
    for col in DROP_COLUMNS: r.pop(col, None)
    name, title = (r.get("Name") or "").strip(), (r.get("Title") or "").strip()
    cid = resolve(r.get("Company"))
    if not name: stats["no name"] += 1; continue
    if not cid: stats["employer not tracked"] += 1; continue
    h = handle(r.get("LinkedIn URL"))
    if h and h in seen_handle: stats["already in brain (LinkedIn)"] += 1; continue
    if (norm(name), cid) in seen_name_at: stats["already in brain (name at employer)"] += 1; continue
    probe = {"current_title": title, "seniority": None, "department": None}
    rank, label, _ = seniority_for(probe)
    if rank > MIN_RANK: stats["below seniority cut"] += 1; continue
    fn, fn_src = function_for(probe)
    slug = f"{slugify(name)}-{(r.get('Id') or '')[:8]}"
    doc = {"id": slug, "type": "person", "name": name, "current_title": title or None,
           "current_company": companies[cid]["name"], "current_company_id": cid,
           "linkedin": (r.get("LinkedIn URL") or "").strip() or None, "location": None,
           "seniority": None, "seniority_rank": rank, "seniority_label": label, "seniority_source": "derived from title",
           "function": fn, "function_source": fn_src, "industry_segment": None,
           "career_history": None, "career": [], "do_not_contact": False, "pipeline": [],
           "department": None, "record_grade": "directory",
           "tags": [t.strip() for t in (r.get("Tags") or "").split(";") if t.strip()],
           "notes": "Directory-grade profile from a bulk people export: name, title, employer and LinkedIn only — no career history, location or pipeline. Not verified against Clockwork.",
           "sources": [f"Bulk people export ({os.path.basename(CSVP)}), imported {TODAY}"], "last_updated": TODAY}
    created.append(doc); seen_handle.add(h) if h else None; seen_name_at.add((norm(name), cid))
    per_company[companies[cid]["name"]] += 1; stats["imported"] += 1
    stats["  " + label] += 1
    if APPLY:
        path = f"{REPO}/data/people/{slug}.json"
        json.dump(doc, open(path, "w"), indent=2, ensure_ascii=False); open(path, "a").write("\n")

print(f"rows {len(rows)} | min-rank {MIN_RANK}")
for k, v in stats.most_common(): print(f"  {k}: {v}")
print("top companies gaining people:", per_company.most_common(12))
print("APPLIED" if APPLY else "dry run")
