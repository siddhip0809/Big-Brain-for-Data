#!/usr/bin/env python3
"""Derive a reporting tree for every company, so the org chart is a real
hierarchy rather than columns of cards.

Two kinds of line, never mixed up in the UI:

  researched  a `reports_to` on the person record, put there because a source
              says so ("X will report to Y" in the appointment release). These
              are the truth. Nothing here invents one.

  inferred    everything else. Within a company: the most senior person overall
              is the top; the most senior person in each department is that
              department's head and hangs off the top; everyone else in the
              department hangs off their department head, and below that off the
              nearest person one seniority rank above them. It is a reading of
              the titles, not a fact, and the atlas labels it as such.

Writes data/derived/org_tree.json: {company_id: [{id, parent, basis}, ...]}.
Reads only; never writes to data/people/. No email, phone or compensation.
"""
import json, glob, os, collections

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# a department head reports to the top of the house; ranks are 0 C-suite .. 5 IC
TOP_RANK = 1          # C-suite and EVP/SVP/MD are candidates for the top of a company
HEAD_RANK = 3         # a department head must be at least Director


def load_people():
    by_company = collections.defaultdict(list)
    for f in glob.glob(f"{REPO}/data/people/*.json"):
        p = json.load(open(f))
        cid = p.get("current_company_id")
        if not cid: continue
        by_company[cid].append({
            "id": p["id"], "name": p["name"], "title": p.get("current_title") or "",
            "fn": p.get("function") or "Miscellaneous",
            "rank": p.get("seniority_rank", 5),
            "reports_to": p.get("reports_to"),          # researched, id or None
            "grade": p.get("record_grade") or "full",
        })
    return by_company


def tree_for(people):
    """-> [{id, parent, basis}] for one company. Parent None = top of the tree."""
    by_id = {p["id"]: p for p in people}
    # sort: most senior first, then a named title, then alphabetical -- stable and
    # explainable, so the same person is the head every time the script runs
    order = sorted(people, key=lambda p: (p["rank"], p["grade"] != "full", p["name"]))
    if not order: return []

    # the top of the house: the single most senior person, preferring one whose
    # title reads like a company lead rather than a department lead
    top = order[0]
    rows = [{"id": top["id"], "parent": None, "basis": "most senior person mapped"}]
    placed = {top["id"]}

    # department heads. The top person already heads their own department -- giving
    # it a second head would hang the rest of the C-suite under one of their peers.
    heads = {top["fn"]: top}
    for fn in sorted({p["fn"] for p in people}):
        if fn == top["fn"]: continue
        cands = [p for p in order if p["fn"] == fn and p["id"] not in placed]
        if not cands: continue
        head = cands[0]
        heads[fn] = head
        rows.append({"id": head["id"], "parent": top["id"],
                     "basis": f"most senior in {fn}" if head["rank"] <= HEAD_RANK
                              else f"only person mapped in {fn}"})
        placed.add(head["id"])

    # everyone else: nearest person above them in their own department
    for fn in sorted({p["fn"] for p in people}):
        chain = [p for p in order if p["fn"] == fn and p["id"] in placed]   # heads first
        for p in [x for x in order if x["fn"] == fn and x["id"] not in placed]:
            # nearest above = the smallest seniority gap, and among equals the most
            # senior by the sort, so peers never end up chained under one another
            above = [c for c in chain if c["rank"] < p["rank"]]
            if above:
                nearest = max(c["rank"] for c in above)
                parent = next(c for c in above if c["rank"] == nearest)
            else:
                parent = heads.get(fn, top)
            rows.append({"id": p["id"], "parent": parent["id"],
                         "basis": f"one level under {parent['title'] or parent['name']}"})
            placed.add(p["id"]); chain.append(p)

    # researched lines override whatever was inferred, as long as both ends are here
    by_row = {r["id"]: r for r in rows}
    for p in people:
        rt = p.get("reports_to")
        if rt and rt in by_id and rt != p["id"] and p["id"] in by_row:
            by_row[p["id"]]["parent"] = rt
            by_row[p["id"]]["basis"] = "researched"
    # a researched line could point back down into a subtree; drop any cycle
    for r in rows:
        seen, cur = {r["id"]}, by_row.get(r["parent"])
        while cur:
            if cur["id"] in seen:
                r["parent"] = top["id"] if r["id"] != top["id"] else None
                r["basis"] += " (a researched line looped, so re-hung at the top)"
                break
            seen.add(cur["id"]); cur = by_row.get(cur["parent"])
    return rows


def main():
    by_company = load_people()
    out, researched, total = {}, 0, 0
    for cid, people in by_company.items():
        rows = tree_for(people)
        if not rows: continue
        out[cid] = rows
        total += len(rows)
        researched += sum(1 for r in rows if r["basis"] == "researched")
    path = os.path.join(REPO, "data/derived/org_tree.json")
    json.dump(out, open(path, "w"), indent=1)
    depth = collections.Counter()
    for cid, rows in out.items():
        parent = {r["id"]: r["parent"] for r in rows}
        for r in rows:
            d, cur = 0, r["parent"]
            while cur is not None and d < 20:
                d += 1; cur = parent.get(cur)
            depth[d] += 1
    print(f"companies: {len(out)}  people placed: {total}")
    print(f"reporting lines: {total - len(out)} ({researched} researched, {total - len(out) - researched} inferred from seniority)")
    print("depth from the top:", dict(sorted(depth.items())))
    print("wrote:", path)


if __name__ == "__main__":
    main()
