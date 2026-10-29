#!/usr/bin/env python3
"""Add Clockwork searches drafted by an agent (see "Clockwork" in CLAUDE.md) to data/searches/.

Clockwork is reachable only through MCP tools, so an agent pulls the projects and writes a
JSON list of search records (the shape of any file in data/searches/). This script is the
only writer, and it enforces what the pull must never get wrong:
  - a record flagged isConfidential / confidential is refused outright (rule 2)
  - internal "[M] ..." mapping twins are refused
  - a salary range in the brief is redacted; placement keeps title, start date and person
    only -- never compensation (rule 1)
  - a search already on file (same Clockwork id) is skipped, never overwritten
  - pipeline rows are kept only at status rank >= 100 and linked to brain people by the
    Clockwork person id (the 8-char suffix of the person filename); no person is created
  - each matched candidate gets a candidate_for edge to the search, as on the first pull
It also re-matches the client company of every on-file search that has none, which picks
up clients added to data/companies/ since (AVK|SEG, Goldacre ...).

    python3 scripts/import_searches.py <drafts.json>           # dry run
    python3 scripts/import_searches.py <drafts.json> --apply
"""
import json, glob, os, re, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrub_people import scrub_text
from import_researched_companies import company_index, match

APPLY = "--apply" in sys.argv
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SDIR, REL = os.path.join(REPO, "data/searches"), os.path.join(REPO, "data/relationships.json")
TODAY = str(date.today())
PAY_RANGE = re.compile(r"(\$|£|€)\s?\d[\d,.]*\s?[kKmM]?\s*(-|–|to)\s*(\$|£|€)?\s?\d[\d,.]*\s?[kKmM]?")
slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def clean(t):
    if not t: return None
    return scrub_text(PAY_RANGE.sub("[pay range removed]", t))[0]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: print(__doc__); sys.exit(2)
    drafts = json.load(open(args[0]))
    by_norm, by_loose, _ = company_index()
    on_file = {json.load(open(f))["id"]: os.path.basename(f)[:-5] for f in glob.glob(f"{SDIR}/*.json")}
    people = {os.path.basename(f)[:-5].rsplit("-", 1)[-1]: os.path.basename(f)[:-5] for f in glob.glob(f"{REPO}/data/people/*.json")}
    rels = json.load(open(REL)); have = {(r["from"], r["to"], r["type"]) for r in rels}
    added, skipped, refused, edges = [], [], [], 0

    for d in drafts:
        name, cid = d.get("name") or "", d.get("id")
        if d.get("isConfidential") or d.get("confidential"): refused.append("a confidential search (not named)"); continue
        if d.get("isInternal") or name.startswith("[M]"): refused.append(f"{name}: internal mapping project"); continue
        if not cid: refused.append(f"{name}: no Clockwork id"); continue
        if cid in on_file: skipped.append(f"{name} ({d.get('client_company')}) already on file as {on_file[cid]}"); continue
        slug = slugify(name) or cid[:8]
        if os.path.exists(f"{SDIR}/{slug}.json") or slug in on_file.values(): slug = f"{slug}-{cid[:8]}"
        pipe = []
        for e in d.get("pipeline") or []:
            if (e.get("rank") or 0) < 100: continue
            pid = e.get("clockwork_person_id") or ""
            bp = e.get("brain_person_id") or people.get(pid[:8])
            pipe.append({"person": e.get("person") or e.get("name"), "clockwork_person_id": pid or None, "brain_person_id": bp,
                         "status": e.get("status"), "category": e.get("category") or e.get("cat"), "rank": e.get("rank")})
        pl = d.get("placement") or None
        if pl: pl = {"person": pl.get("person"), "person_id": pl.get("person_id") or pl.get("clockwork_person_id"),
                     "title": pl.get("title"), "start_date": pl.get("start_date")}
        cat = lambda p: [x for x in pipe if (x["category"] or "").startswith(p)]
        rec = {"id": cid, "type": "search", "name": name, "client_company": d.get("client_company"),
               "client_company_id": match(d.get("client_company") or "", by_norm, by_loose),
               "status": d.get("status"), "project_type": d.get("project_type"),
               "started_at": d.get("started_at"), "closed_at": d.get("closed_at"), "closing_reason": d.get("closing_reason"),
               "strategy": clean(d.get("strategy")), "job_description": clean(d.get("job_description")),
               "job_requirements": clean(d.get("job_requirements")), "placement": pl, "pipeline": pipe,
               "counts": {"pipeline": len(pipe), "placed": len(cat("in-placed")), "active": len(cat("in-")), "out": len(cat("out-"))},
               "sources": [f"Clockwork API, pulled {TODAY}"], "last_updated": TODAY}
        for e in pipe:
            key = (f"person:{e['brain_person_id']}", f"search:{slug}", "candidate_for")
            if e["brain_person_id"] and key not in have:
                rels.append({"from": key[0], "to": key[1], "type": "candidate_for",
                             "detail": f"{e['status']} ({e['category']})", "status": e["status"], "confidence": "high",
                             "sources": [f"Clockwork API, pulled {TODAY}"], "last_updated": TODAY})
                have.add(key); edges += 1
        if APPLY:
            json.dump(rec, open(f"{SDIR}/{slug}.json", "w"), indent=2, ensure_ascii=False); open(f"{SDIR}/{slug}.json", "a").write("\n")
        added.append(f"{slug}: {rec['client_company']} \\ {name} [{rec['status']}] pipeline {len(pipe)}"
                     + ("" if rec["client_company_id"] else "  (client not in the brain)"))

    rematched = []
    for f in sorted(glob.glob(f"{SDIR}/*.json")):
        s = json.load(open(f))
        if s.get("client_company_id") or not s.get("client_company"): continue
        c = match(s["client_company"], by_norm, by_loose)
        if c:
            rematched.append(f"{os.path.basename(f)[:-5]}: {s['client_company']} -> {c}")
            if APPLY:
                s["client_company_id"] = c; s["last_updated"] = TODAY
                json.dump(s, open(f, "w"), indent=2, ensure_ascii=False); open(f, "a").write("\n")

    if APPLY:
        json.dump(rels, open(REL, "w"), indent=2, ensure_ascii=False); open(REL, "a").write("\n")
    print(f"searches added {len(added)}   already on file {len(skipped)}   refused {len(refused)}   candidate_for edges {edges}   clients re-matched {len(rematched)}")
    for x in refused: print("  REFUSED ", x)
    for x in added: print("  + ", x)
    for x in rematched: print("  client ", x)
    print("\nAPPLIED -- rerun the pipeline" if APPLY else "\ndry run")


if __name__ == "__main__":
    main()
