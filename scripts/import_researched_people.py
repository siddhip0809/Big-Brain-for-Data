#!/usr/bin/env python3
"""Import people found in open sources into data/people/.

Input is a JSON list, one object per person:
  {"name", "company", "title", "source",            # all required
   "prev_title", "prev_company", "note",            # optional
   "reports_to_name"}                               # optional: their manager, only when the
                                                    # source states it -- becomes `reports_to`

Rules this enforces, so a research round can never quietly degrade the brain:
  - a person with no `source` URL is refused outright (CLAUDE.md rule 3)
  - the company must already be a record here; it never invents one
  - a name already at that company is reported as a duplicate and skipped,
    never silently overwritten
  - NO email, phone or compensation is read or written, ever (rule 1)

Records are written with record_grade "researched" so the atlas can tell them
apart from the Clockwork-sourced ones and from the bulk directory import.

    python3 scripts/import_researched_people.py <file.json>            # dry run
    python3 scripts/import_researched_people.py <file.json> --apply
"""
import json, glob, os, re, sys, hashlib

APPLY = "--apply" in sys.argv
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PEOPLE_DIR = os.path.join(REPO, "data/people")

norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
SUFFIXES = r"\b(inc|llc|ltd|limited|corp|corporation|group|holdings|plc|sa|nv|gmbh|co|company|the)\b"
loose = lambda s: norm(re.sub(SUFFIXES, " ", (s or "").lower()))


def company_index():
    by_norm, by_loose = {}, {}
    for f in glob.glob(f"{REPO}/data/companies/*.json"):
        c = json.load(open(f))
        for n in [c["name"]] + (c.get("aliases") or []):
            by_norm.setdefault(norm(n), set()).add(c["id"])
            by_loose.setdefault(loose(n), set()).add(c["id"])
    return by_norm, by_loose


def match_company(name, by_norm, by_loose):
    """norm first, then a loose pass, and only when the loose match is unique."""
    hit = by_norm.get(norm(name))
    if hit and len(hit) == 1: return next(iter(hit)), "exact"
    hit = by_loose.get(loose(name))
    if hit and len(hit) == 1: return next(iter(hit)), "loose"
    return None, ("ambiguous" if hit else "no match")


def existing_people():
    """(normalised name, company id) -> person id, so we never duplicate a person
    and can resolve a stated manager."""
    out = {}
    for f in glob.glob(f"{PEOPLE_DIR}/*.json"):
        p = json.load(open(f))
        out[(norm(p.get("name")), p.get("current_company_id"))] = p["id"]
    return out


def person_id(name, company_id):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{slug}-{hashlib.sha1((slug + '|' + company_id).encode()).hexdigest()[:8]}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    rows = json.load(open(args[0]))
    by_norm, by_loose = company_index()
    seen = existing_people()

    added, dupes, refused, pending, pending_ids, unresolved = [], [], [], set(), {}, []
    for r in rows:
        name, comp, title, src = r.get("name"), r.get("company"), r.get("title"), r.get("source")
        if not (name and comp and title and src and src.startswith("http")):
            refused.append((name or "?", comp or "?", "missing name, company, title or a source URL")); continue
        cid, how = match_company(comp, by_norm, by_loose)
        if not cid:
            refused.append((name, comp, f"company {how}")); continue
        key = (norm(name), cid)
        if key in seen or key in pending:
            dupes.append((name, comp, seen.get(key, "added earlier in this file"))); continue

        pid = person_id(name, cid)
        mgr = None
        if r.get("reports_to_name"):
            mgr = seen.get((norm(r["reports_to_name"]), cid)) or pending_ids.get((norm(r["reports_to_name"]), cid))
            if not mgr: unresolved.append((name, r["reports_to_name"], comp))
        rec = {
            "id": pid, "type": "person", "name": name,
            "current_title": title, "current_company": comp, "current_company_id": cid,
            "record_grade": "researched",
            "notes": r.get("note") or "",
            "sources": [src],
            "last_updated": "2026-09-13",
        }
        if r.get("prev_company"):
            rec["career_history"] = f"{r.get('prev_title') or 'role not stated'} at {r['prev_company']}"
        if mgr: rec["reports_to"] = mgr
        rec = {k: v for k, v in rec.items() if v not in (None, "")}
        if APPLY:
            path = os.path.join(PEOPLE_DIR, pid + ".json")
            json.dump(rec, open(path, "w"), indent=2, ensure_ascii=False); open(path, "a").write("\n")
        pending.add(key); pending_ids[key] = pid
        added.append((name, title, comp, cid, r.get("prev_company") or "", src))

    print(f"added: {len(added)}   already there: {len(dupes)}   refused: {len(refused)}")
    for n, c, why in refused: print(f"  REFUSED  {n} ({c}): {why}")
    for n, c, where in dupes: print(f"  already there  {n} at {c}  -> {where}")
    for n, m, c in unresolved: print(f"  reports_to NOT set  {n} -> {m} ({c}): manager is not a person record here")
    print()
    for n, t, c, cid, prev, src in added:
        print(f"  + {n} — {t} @ {c}" + (f"   (from {prev})" if prev else ""))
    print("\nAPPLIED — now re-run enrich_people, build_talent_flows, build_org_tree" if APPLY else "\ndry run")


if __name__ == "__main__":
    main()
