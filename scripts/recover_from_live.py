#!/usr/bin/env python3
"""Bring into the repo whatever the published atlas holds that the repo does not.

Two Claude accounts work on this brain. Each can publish the page, and a publish from a
checkout that never pushed leaves companies, deals and notes that exist only on the page.
This reads a saved copy of the page (Artifact tool, action "read": it saves the HTML) or
its graph JSON, and writes the difference back under the repo's own rules:

  companies   one on the page and not in data/companies/ becomes a record. For one in both,
              the repo wins wherever it has a value, the page fills the gaps, and roles,
              aliases, tags and sources are unioned. `region` / `region_basis` are taken
              from the page (the repo has no other source for them yet).
  deals       an edge on the page and not in data/relationships.json is added. One with no
              source URL is written as confidence "low", status "unsupported", whatever
              the page claimed -- rule 3 -- with the page's claim kept under `claimed`.
  notes       never written here: scripts/import_notes.py is the only writer of data/notes/.
              With --notes-out FILE (outside the repo) the page's notes that are not in the
              repo are written as a draft for it, so its refusals (pay, contact details,
              special-category matters, searches not on file) still apply.
  people, searches, org trees   reported if they differ; never written. Those come from
              Clockwork and the importers, and the page carries only part of each record.

Nothing here stores an email address, a phone number or pay: a company or deal string that
contains one is scrubbed with scrub_people.scrub_text before it is written.

    python3 scripts/recover_from_live.py <page.html | graph.json>                      # dry run
    python3 scripts/recover_from_live.py <page.html> --notes-out /tmp/x/notes.json --apply
"""
import json, glob, os, re, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrub_people import scrub_text
from tiers import TIERS

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TODAY = str(date.today())
FILL = ("industry_role", "headquarters", "founded", "website", "linkedin", "headcount", "description",
        "hyperscale_focus", "capacity_mw", "dc_exposure_level", "list_attributes", "parent_industry")
UNION = ("roles", "aliases", "tags", "sources")
is_url = lambda s: isinstance(s, str) and s.startswith("http")
empty = lambda v: v in (None, "", [], {})


def clean(v):
    """Scrub contact details and pay from every string in a value (rule 1)."""
    if isinstance(v, str): return scrub_text(v)[0]
    if isinstance(v, list): return [clean(x) for x in v]
    if isinstance(v, dict): return {k: clean(x) for k, x in v.items()}
    return v


def load_graph(path):
    text = open(path, encoding="utf-8").read()
    if path.endswith(".json"): return json.loads(text)
    m = re.search(r'<script type="application/json" id="graph-data">(.*?)</script>', text, re.S)
    if not m: sys.exit("no graph-data block in " + path)
    return json.loads(m.group(1))


def dump(path, obj):
    json.dump(obj, open(path, "w"), indent=2, ensure_ascii=False); open(path, "a").write("\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_ = "--apply" in sys.argv
    notes_out = sys.argv[sys.argv.index("--notes-out") + 1] if "--notes-out" in sys.argv else None
    if notes_out: args.remove(notes_out)
    if not args: print(__doc__); sys.exit(2)
    if notes_out and os.path.abspath(notes_out).startswith(REPO + os.sep):
        sys.exit("--notes-out must be outside the repo: it holds draft notes that have not been through import_notes.py")
    g = load_graph(args[0])

    unknown = [c for c in g["categories"] if c["id"] not in TIERS]
    if unknown:
        print("the page uses tiers the repo does not define. Add them to scripts/tiers.py first:")
        for c in unknown: print("   ", json.dumps(c, ensure_ascii=False))
        sys.exit(1)

    companies = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{REPO}/data/companies/*.json")}
    investors = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{REPO}/data/investors/*.json")}
    people = {os.path.basename(f)[:-5] for f in glob.glob(f"{REPO}/data/people/*.json")}
    searches = {os.path.basename(f)[:-5] for f in glob.glob(f"{REPO}/data/searches/*.json")}
    rels = json.load(open(f"{REPO}/data/relationships.json"))

    # ---- companies ----
    new, changed, kept = [], {}, []
    for n in g["nodes"]:
        if n["kind"] != "company": continue
        n = clean(n); cid = n["id"]
        if cid not in companies:
            rec = {"id": cid, "type": "company", "name": n["name"], "aliases": n.get("aliases") or [],
                   "roles": n["roles"], "parent_industry": n.get("parent_industry") or "pure_play",
                   **{k: n.get(k) for k in ("industry_role", "headquarters", "founded", "website", "linkedin", "headcount", "description")},
                   "tags": n.get("tags") or [], "source_lists": [], "list_attributes": n.get("list_attributes") or {},
                   **{k: n[k] for k in ("hyperscale_focus", "capacity_mw", "dc_exposure_level") if not empty(n.get(k))},
                   "notes": n.get("notes"), "sources": n.get("sources") or [],
                   **{k: n[k] for k in ("region", "region_basis") if not empty(n.get(k))}, "last_updated": TODAY}
            companies[cid] = rec; new.append(cid); changed[cid] = rec; continue
        rec = companies[cid]; before = json.dumps(rec, sort_keys=True)
        for k in UNION:
            rec[k] = list(dict.fromkeys((rec.get(k) or []) + (n.get(k) or [])))
        for k in FILL:
            if empty(rec.get(k)) and not empty(n.get(k)): rec[k] = n[k]
            elif not empty(n.get(k)) and n[k] != rec.get(k): kept.append(f"{cid}.{k}")
        note = n.get("notes")
        if note and (empty(rec.get("notes")) or (note != rec["notes"] and note.startswith(rec["notes"]))): rec["notes"] = note
        elif note and note != rec.get("notes"): kept.append(f"{cid}.notes")
        for k in ("region", "region_basis"):
            if not empty(n.get(k)): rec[k] = n[k]
            else: rec.pop(k, None)
        if json.dumps(rec, sort_keys=True) != before: rec["last_updated"] = TODAY; changed[cid] = rec
    print(f"companies: {len(new)} new, {len(changed) - len(new)} updated; the repo's own value kept over the page's in {len(kept)} fields")
    if kept: print("   kept (repo value differs from the page):", ", ".join(kept[:12]) + (" ..." if len(kept) > 12 else ""))
    for n in g["nodes"]:
        if n["kind"] == "investor" and n["id"].split(":", 1)[1] not in investors: print("   investor on the page, not in the repo (not written):", n["id"])

    # ---- deals ----
    ref = lambda nid: nid if nid.startswith("investor:") else "company:" + nid
    have = {(r["from"], r["to"], r["type"]) for r in rels}
    added, unsupported, dangling, differ = [], 0, [], 0
    for l in g["links"]:
        if l["type"] == "talent_flow": continue
        key = (ref(l["source"]), ref(l["target"]), l["type"])
        if key in have:
            cur = next(r for r in rels if (r["from"], r["to"], r["type"]) == key)
            if l["type"] != "invested_in" and (l.get("detail") or "") != (cur.get("detail") or ""): differ += 1
            continue
        if any(e.startswith("company:") and e[8:] not in companies for e in key[:2]): dangling.append(key); continue
        if l["type"] == "invested_in" and key[0].startswith("investor:"):
            inv = investors[key[0][9:]]
            if key[1][8:] not in (inv.get("investments") or []):
                inv.setdefault("investments", []).append(key[1][8:])
                if apply_: dump(f"{REPO}/data/investors/{key[0][9:]}.json", inv)
        l = clean(l)
        edge = {"from": key[0], "to": key[1], "type": l["type"], "detail": l.get("detail"), "status": l.get("status"),
                "confidence": l.get("confidence"), "sources": l.get("sources") or []}
        if not any(is_url(s) for s in edge["sources"]):
            edge["claimed"] = {"status": edge["status"], "confidence": edge["confidence"]}
            edge["status"], edge["confidence"] = "unsupported", "low"; unsupported += 1
        if l.get("basis"): edge["basis"] = l["basis"]
        if l.get("verified_by"): edge["verified_by"] = l["verified_by"]
        edge["last_updated"] = TODAY
        rels.append(edge); have.add(key); added.append(key)
    print(f"deals: {len(added)} new ({unsupported} had no source URL and are written as low / unsupported); "
          f"{differ} on both sides with different wording (repo kept); {len(dangling)} skipped for a missing endpoint")

    # ---- notes: a draft for import_notes.py ----
    on_file = {(d.get("date"), d.get("summary")) for d in (json.load(open(f)) for f in glob.glob(f"{REPO}/data/notes/*.json"))}
    def note_ref(x):
        if x.startswith(("search:", "investor:", "company:", "person:")): return x
        return "company:" + x if x in companies else "person:" + x if x in people else x
    rows = []
    for n in g.get("notes") or []:
        if (n.get("date"), n.get("summary")) in on_file: continue
        via = n.get("via") or ""
        channel = "teams" if via.lower().startswith("teams") else "email" if "outlook" in via.lower() else \
                  "atlas" if "atlas" in via.lower() else "document" if "sharepoint" in (n.get("link") or "") else "other"
        rows.append({"date": n["date"], "kind": n["kind"], "basis": n["basis"], "summary": n["summary"],
                     "refs": [note_ref(x) for x in n.get("about") or []], "discretion": bool(n.get("discretion")),
                     "signals": [{k: (note_ref(v) if k in ("person", "company", "counterparty") else v) for k, v in s.items()} for s in n.get("signals") or []],
                     "source": {"channel": channel, "date": n["date"], "from": n.get("from"), "via": via, "subject": n.get("subject"),
                                "link": n.get("link"), "message_id": n.get("link") or n.get("id")}})
    print(f"notes: {len(rows)} on the page and not in the repo" + (f" -> draft written to {notes_out}; run import_notes.py on it" if notes_out and rows else ""))
    if notes_out and rows: json.dump(rows, open(notes_out, "w"), indent=1, ensure_ascii=False)

    # ---- reported only ----
    live_people = {p["id"] for v in g["people"].values() for p in v}
    print(f"people: {len(live_people - people)} on the page and not in the repo, {len(people - live_people)} the other way (not written)")
    live_s = {s.get("slug") or s.get("id") for s in g["searches"]}
    print(f"searches: {len(live_s - searches)} on the page and not in the repo (not written)")

    if apply_:
        for cid, rec in changed.items(): dump(f"{REPO}/data/companies/{cid}.json", rec)
        if added: dump(f"{REPO}/data/relationships.json", rels)
        print("\nAPPLIED -- run the pipeline, then compare the build with the page before publishing")
    else: print("\ndry run")


if __name__ == "__main__":
    main()
