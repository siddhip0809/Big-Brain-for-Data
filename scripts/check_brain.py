#!/usr/bin/env python3
"""Integrity check over everything in data/. Run it after any import.

Exits non-zero if anything is wrong, so it can gate a commit. Checks:
  privacy      no email, phone or pay figure in any record (CLAUDE.md rule 1)
  references   every relationship endpoint, current_company_id, client_company_id,
               pipeline brain_person_id and investor portfolio entry resolves
  sourcing     every researched person and every deal edge carries a source;
               a deal edge with no URL is marked low / unsupported, not silent
  shape        every company has roles from the known set; every person has a
               function from the known set and a seniority rank; no "Unclassified"
  duplicates   no two people with the same name at the same company;
               no two companies with the same normalised name
  searches     status and closing_reason in the known sets; a placement only
               where the search closed on one
  derived      data/derived/ is not stale against data/
"""
import json, glob, os, re, sys, collections

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
D = lambda *p: os.path.join(REPO, "data", *p)

ROLES = {"hyperscaler", "neocloud", "cryptomining", "developer_operator",
         "energy_developer", "general_contractor", "civil_land_engineering", "real_estate_developer"}
FUNCTIONS = {"Executive leadership", "Development & Real Estate", "Sales & Leasing",
             "Pre-Construction & Cost", "Construction & Delivery", "Energy & Utilities",
             "Design & Engineering", "Strategy, Finance & Investment", "Operations & Facilities",
             "Procurement & Supply Chain", "Legal, People & Support", "Miscellaneous"}
STATUSES = {"active", "on_hold", "pitch", "closed"}
CLOSING = {"Placement", "Cancelled", "Terminated", "Internal Hire", None}
DEAL = {"invested_in", "acquired", "tenant_of", "jv_partner", "contractor_for", "supplies_power_to", "site_partner"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# a phone: 9+ digits with separators, not preceded by a URL character. Dates and
# UUIDs are excluded by the separator classes.
PHONE = re.compile(r"(?<![\w/=&.-])\+?\(?\d{2,4}\)?[ .-]\d{3,4}[ .-]\d{3,4}(?![\w/])")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrub_people import PAY   # one definition of "a pay figure", shared with the scrubber
norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())

problems = collections.defaultdict(list)
def bad(kind, msg): problems[kind].append(msg)


def load_dir(sub):
    out = {}
    for f in sorted(glob.glob(D(sub, "*.json"))):
        try: d = json.load(open(f))
        except Exception as e: bad("shape", f"{f}: not valid JSON ({e})"); continue
        out[os.path.basename(f)[:-5]] = d
    return out


def main():
    companies, investors, people, searches = load_dir("companies"), load_dir("investors"), load_dir("people"), load_dir("searches")
    rels = json.load(open(D("relationships.json")))

    # ---- privacy, over every record as text ----
    for sub, coll in (("companies", companies), ("investors", investors), ("people", people), ("searches", searches)):
        for k, d in coll.items():
            blob = json.dumps(d, ensure_ascii=False)
            for key in ("email", "phone", "mobile", "compensation", "salary"):
                if key in d: bad("privacy", f"{sub}/{k}: has a `{key}` field")
            if EMAIL.search(blob): bad("privacy", f"{sub}/{k}: email address in record")
            for m in PHONE.finditer(blob):
                bad("privacy", f"{sub}/{k}: phone-like `{m.group(0)}`")
            if sub != "searches" and PAY.search(blob):
                bad("privacy", f"{sub}/{k}: pay wording `{PAY.search(blob).group(0)}`")
    for d in searches.values():
        for fld in ("job_description", "job_requirements", "strategy"):
            t = d.get(fld) or ""
            m = re.search(r"(\$|£|€)\s?\d{2,3},?\d{3}\s*(-|–|to)\s*(\$|£|€)?\s?\d{2,3},?\d{3}", t)
            if m: bad("privacy", f"searches/{d.get('name')}: pay range in {fld}: `{m.group(0)}`")

    # ---- references ----
    node = lambda ref: (ref.split(":", 1)[1] in companies) if ref.startswith("company:") else \
                       (ref.split(":", 1)[1] in investors) if ref.startswith("investor:") else \
                       (ref.split(":", 1)[1] in people) if ref.startswith("person:") else \
                       (ref.split(":", 1)[1] in searches) if ref.startswith("search:") else False
    for r in rels:
        for end in ("from", "to"):
            if not node(r[end]): bad("references", f"relationship {r['type']} {r['from']} → {r['to']}: `{end}` does not resolve")
    for k, p in people.items():
        c = p.get("current_company_id")
        if c and c not in companies: bad("references", f"people/{k}: current_company_id `{c}` is not a company")
        rt = p.get("reports_to")
        if rt and rt not in people: bad("references", f"people/{k}: reports_to `{rt}` is not a person")
    for k, s in searches.items():
        c = s.get("client_company_id")
        if c and c not in companies: bad("references", f"searches/{k}: client_company_id `{c}` is not a company")
        for e in s.get("pipeline") or []:
            b = e.get("brain_person_id")
            if b and b not in people: bad("references", f"searches/{k}: pipeline brain_person_id `{b}` is not a person")
    for k, i in investors.items():
        for c in i.get("investments") or []:
            if c not in companies: bad("references", f"investors/{k}: investment `{c}` is not a company")

    # ---- sourcing ----
    for k, p in people.items():
        if p.get("record_grade") == "researched" and not any(str(s).startswith("http") for s in p.get("sources") or []):
            bad("sourcing", f"people/{k}: researched record with no source URL")
        if not p.get("sources"): bad("sourcing", f"people/{k}: no sources at all")
    for r in rels:
        if r["type"] in DEAL and not any(str(s).startswith("http") for s in r.get("sources") or []):
            if not (r.get("confidence") == "low" or r.get("status") == "unsupported" or r.get("verification")):
                bad("sourcing", f"relationship {r['type']} {r['from']} → {r['to']}: no URL and not marked low/unsupported")

    # ---- shape ----
    for k, c in companies.items():
        roles = set(c.get("roles") or [])
        if not roles: bad("shape", f"companies/{k}: no roles")
        if roles - ROLES: bad("shape", f"companies/{k}: unknown roles {roles - ROLES}")
        if c.get("id") != k: bad("shape", f"companies/{k}: id field `{c.get('id')}` differs from filename")
    for k, p in people.items():
        if p.get("function") not in FUNCTIONS: bad("shape", f"people/{k}: function `{p.get('function')}`")
        if p.get("seniority_rank") not in (0, 1, 2, 3, 4, 5): bad("shape", f"people/{k}: seniority_rank `{p.get('seniority_rank')}`")
        if p.get("id") != k: bad("shape", f"people/{k}: id field differs from filename")
        if not p.get("name"): bad("shape", f"people/{k}: no name")

    # ---- duplicates ----
    seen = collections.defaultdict(list)
    for k, p in people.items(): seen[(norm(p.get("name")), p.get("current_company_id"))].append(k)
    for (n, c), ks in seen.items():
        if len(ks) > 1 and n: bad("duplicates", f"people: {ks} are the same name at {c}")
    cn = collections.defaultdict(list)
    for k, c in companies.items(): cn[norm(c["name"])].append(k)
    for n, ks in cn.items():
        if len(ks) > 1: bad("duplicates", f"companies: {ks} share the name `{n}`")

    # ---- searches ----
    for k, s in searches.items():
        if s.get("status") not in STATUSES: bad("searches", f"{k}: status `{s.get('status')}`")
        if s.get("closing_reason") not in CLOSING: bad("searches", f"{k}: closing_reason `{s.get('closing_reason')}`")
        if s.get("status") != "closed" and s.get("closing_reason"): bad("searches", f"{k}: closing_reason on a search that is not closed")
        placed = (s.get("placement") or {}).get("person")
        if placed and s.get("closing_reason") != "Placement": bad("searches", f"{k}: has a placed person but closing_reason is `{s.get('closing_reason')}`")
        if re.search(r"confidential (search|project|assignment|client|role|mandate)", json.dumps(s), re.I):
            bad("searches", f"{k}: looks like a confidential search \u2014 must not be in the repo")

    # ---- derived freshness ----
    newest_data = max(os.path.getmtime(f) for sub in ("companies", "people", "searches") for f in glob.glob(D(sub, "*.json")))
    newest_data = max(newest_data, os.path.getmtime(D("relationships.json")))
    for f in glob.glob(D("derived", "*")):
        if os.path.getmtime(f) < newest_data - 5:
            bad("derived", f"{os.path.basename(f)} is older than the newest data file — rerun the pipeline")

    # ---- report ----
    counts = {"companies": len(companies), "investors": len(investors), "people": len(people),
              "searches": len(searches), "relationships": len(rels),
              "completed searches": sum(1 for s in searches.values() if s.get("status") == "closed" and s.get("closing_reason") == "Placement"),
              "researched people": sum(1 for p in people.values() if p.get("record_grade") == "researched"),
              "Miscellaneous": sum(1 for p in people.values() if p.get("function") == "Miscellaneous")}
    print("brain:", "  ".join(f"{k} {v:,}" for k, v in counts.items()))
    total = sum(len(v) for v in problems.values())
    if not total:
        print("all checks pass"); return 0
    for kind, msgs in problems.items():
        print(f"\n{kind.upper()} — {len(msgs)}")
        for m in msgs[:25]: print("  ", m)
        if len(msgs) > 25: print(f"   … {len(msgs) - 25} more")
    print(f"\n{total} problem(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
