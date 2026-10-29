#!/usr/bin/env python3
"""Import companies, extra roles and company-to-company edges found in open sources.

Input is one JSON object:
  {"companies":  [{"name", "roles", "sources",                       # required; sources = list of URLs
                   "aliases", "industry_role", "parent_industry",    # optional
                   "headquarters", "website", "description", "notes"}],
   "add_roles":  [{"company", "role", "source", "note"}],           # give an existing company one more role
   "add_aliases":[{"company", "aliases": [...]}],                    # e.g. an acquired brand now trading under the parent
   "add_sources":[{"company", "sources": [...], "note"}],            # attach evidence to a record that already exists
   "edges":      [{"from", "to", "type", "sources",                  # company names, a deal type, URLs
                   "detail", "status", "confidence"}]}

Rules this enforces (CLAUDE.md rules 1 and 3):
  - a company with no source URL is refused; it never invents a website or an HQ
  - a company whose name already matches a record (norm, then a unique loose match)
    is reported and skipped, never overwritten -- use add_roles for those
  - an edge end may be a company or (by name) an investor; one that does not resolve is refused; an exact duplicate
    (same from, to, type) is skipped; an edge with no URL is written low / unsupported
  - roles and edge types must come from the known sets
  - nothing about a person is read or written here, so no email, phone or pay

    python3 scripts/import_researched_companies.py <file.json>            # dry run
    python3 scripts/import_researched_companies.py <file.json> --apply
"""
import json, glob, os, re, sys
from datetime import date

APPLY = "--apply" in sys.argv
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
COMP_DIR = os.path.join(REPO, "data/companies")
REL_PATH = os.path.join(REPO, "data/relationships.json")
TODAY = str(date.today())

ROLES = {"hyperscaler", "neocloud", "cryptomining", "developer_operator", "energy_developer",
         "general_contractor", "civil_land_engineering", "real_estate_developer", "consultancy"}
PARENTS = {"pure_play", "real_estate", "energy_utilities", "telecom", "construction_engineering", "diversified_conglomerate"}
DEAL = {"invested_in", "acquired", "tenant_of", "jv_partner", "contractor_for", "supplies_power_to", "site_partner", "consulted_for"}

norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
SUFFIXES = r"\b(inc|llc|ltd|limited|corp|corporation|group|holdings|plc|sa|nv|gmbh|co|company|the)\b"
loose = lambda s: norm(re.sub(SUFFIXES, " ", (s or "").lower()))
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", (s or "").lower().replace("&", " and ")).strip("-")


def company_index():
    by_norm, by_loose, recs = {}, {}, {}
    for f in glob.glob(f"{COMP_DIR}/*.json"):
        c = json.load(open(f)); recs[c["id"]] = c
        for n in [c["name"]] + (c.get("aliases") or []):
            by_norm.setdefault(norm(n), set()).add(c["id"])
            by_loose.setdefault(loose(n), set()).add(c["id"])
    return by_norm, by_loose, recs


def investor_index():
    out = {}
    for f in glob.glob(os.path.join(REPO, "data/investors/*.json")):
        i = json.load(open(f))
        for n in [i["name"]] + (i.get("aliases") or []): out.setdefault(norm(n), i["id"])
    return out


def match(name, by_norm, by_loose):
    hit = by_norm.get(norm(name))
    if hit and len(hit) == 1: return next(iter(hit))
    hit = by_loose.get(loose(name))
    if hit and len(hit) == 1: return next(iter(hit))
    return None


def urls(x):
    if isinstance(x, str): x = [x]
    return [u for u in (x or []) if isinstance(u, str) and u.startswith("http")]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: print(__doc__); sys.exit(2)
    spec = json.load(open(args[0]))
    by_norm, by_loose, recs = company_index()
    investors = investor_index()
    rels = json.load(open(REL_PATH))
    have = {(r["from"], r["to"], r["type"]) for r in rels}
    report = {"companies added": [], "companies skipped": [], "roles added": [], "aliases added": [], "sources added": [], "edges added": [], "refused": []}

    def save(c):
        if APPLY:
            p = os.path.join(COMP_DIR, c["id"] + ".json")
            json.dump(c, open(p, "w"), indent=2, ensure_ascii=False); open(p, "a").write("\n")

    def endpoint(name):
        """company:<id> or investor:<id> for a name, else None."""
        cid = match(name, by_norm, by_loose)
        if cid: return f"company:{cid}"
        iid = investors.get(norm(name))
        return f"investor:{iid}" if iid else None

    def register(c):
        recs[c["id"]] = c
        for n in [c["name"]] + (c.get("aliases") or []):
            by_norm.setdefault(norm(n), set()).add(c["id"]); by_loose.setdefault(loose(n), set()).add(c["id"])

    for c in spec.get("companies") or []:
        name, roles, src = c.get("name"), set(c.get("roles") or []), urls(c.get("sources"))
        if not (name and roles and src): report["refused"].append(f"company {name or '?'}: needs name, roles and a source URL"); continue
        if roles - ROLES: report["refused"].append(f"company {name}: unknown roles {roles - ROLES}"); continue
        hit = match(name, by_norm, by_loose)
        if hit: report["companies skipped"].append(f"{name} -> already here as {hit}"); continue
        cid = slug(name)
        if cid in recs: report["refused"].append(f"company {name}: id {cid} already taken"); continue
        parent = c.get("parent_industry") or "construction_engineering"
        if parent not in PARENTS: report["refused"].append(f"company {name}: unknown parent_industry {parent}"); continue
        rec = {"id": cid, "type": "company", "name": name, "aliases": c.get("aliases") or [],
               "roles": sorted(roles), "parent_industry": parent,
               "industry_role": c.get("industry_role"), "headquarters": c.get("headquarters"), "founded": None,
               "website": c.get("website") if (c.get("website") or "").startswith("http") else None,
               "linkedin": None, "headcount": None, "description": c.get("description"), "tags": [],
               "source_lists": [], "list_attributes": {},
               "notes": (c.get("notes") or "") + f" Added {TODAY} from open-source research (import_researched_companies.py).",
               "sources": src, "last_updated": TODAY}
        if APPLY:
            p = os.path.join(COMP_DIR, cid + ".json")
            json.dump(rec, open(p, "w"), indent=2, ensure_ascii=False); open(p, "a").write("\n")
        register(rec); report["companies added"].append(f"{name} ({cid}) roles={rec['roles']}")

    for a in spec.get("add_roles") or []:
        cid = match(a.get("company"), by_norm, by_loose)
        role, src = a.get("role"), urls(a.get("source") or a.get("sources"))
        if not cid: report["refused"].append(f"add_roles {a.get('company')}: company not found"); continue
        if role not in ROLES or not src: report["refused"].append(f"add_roles {a.get('company')}: unknown role or no URL"); continue
        c = recs[cid]
        if role in c["roles"]: report["companies skipped"].append(f"{c['name']} already has role {role}"); continue
        c["roles"].append(role)
        c["notes"] = (c.get("notes") or "").rstrip() + f" Role {role} added {TODAY}: {a.get('note') or 'data-center practice evidenced in the source'}."
        c["sources"] = list(dict.fromkeys((c.get("sources") or []) + src)); c["last_updated"] = TODAY
        save(c); report["roles added"].append(f"{c['name']} += {role}")

    for a in spec.get("add_aliases") or []:
        cid = match(a.get("company"), by_norm, by_loose)
        if not cid: report["refused"].append(f"add_aliases {a.get('company')}: company not found"); continue
        c = recs[cid]; new = [x for x in (a.get("aliases") or []) if x and norm(x) not in {norm(n) for n in [c["name"]] + (c.get("aliases") or [])}]
        if not new: continue
        c["aliases"] = (c.get("aliases") or []) + new
        if a.get("note"): c["notes"] = (c.get("notes") or "").rstrip() + f" {a['note']} ({TODAY})."
        c["last_updated"] = TODAY; save(c); register(c)
        report["aliases added"].append(f"{c['name']} += {new}")

    for a in spec.get("add_sources") or []:
        cid = match(a.get("company"), by_norm, by_loose)
        src = urls(a.get("sources") or a.get("source"))
        if not cid or not src: report["refused"].append(f"add_sources {a.get('company')}: company not found or no URL"); continue
        c = recs[cid]; new = [u for u in src if u not in (c.get("sources") or [])]
        if not new: continue
        c["sources"] = (c.get("sources") or []) + new
        if a.get("note"): c["notes"] = (c.get("notes") or "").rstrip() + f" {a['note']} ({TODAY})."
        c["last_updated"] = TODAY; save(c)
        report["sources added"].append(f"{c['name']} += {len(new)} URL(s)")

    for e in spec.get("edges") or []:
        f, t, typ = endpoint(e.get("from")), endpoint(e.get("to")), e.get("type")
        if typ not in DEAL: report["refused"].append(f"edge {e.get('from')} -> {e.get('to')}: unknown type {typ}"); continue
        if not (f and t): report["refused"].append(f"edge {e.get('from')} -> {e.get('to')}: " + ("from" if not f else "to") + " not a company or investor here"); continue
        if f == t: report["refused"].append(f"edge {e.get('from')}: points at itself"); continue
        key = (f, t, typ)
        if key in have: report["companies skipped"].append(f"edge {typ} {f} -> {t} already here"); continue
        src = urls(e.get("sources") or e.get("source"))
        rec = {"from": key[0], "to": key[1], "type": typ, "detail": e.get("detail") or "",
               "status": e.get("status") or ("unsupported" if not src else "reported"),
               "confidence": (e.get("confidence") or "high") if src else "low",
               "sources": src, "last_updated": TODAY}
        rels.append(rec); have.add(key); report["edges added"].append(f"{typ} {f} -> {t}" + ("" if src else "  (NO URL: low/unsupported)"))

    if APPLY:
        json.dump(rels, open(REL_PATH, "w"), indent=2, ensure_ascii=False); open(REL_PATH, "a").write("\n")
    for k, v in report.items():
        print(f"\n{k.upper()} ({len(v)})")
        for line in v: print("  ", line)
    print("\nAPPLIED" if APPLY else "\ndry run")


if __name__ == "__main__":
    main()
