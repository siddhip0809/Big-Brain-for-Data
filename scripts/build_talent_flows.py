#!/usr/bin/env python3
"""Talent flows: who hires from whom, derived from each person's parsed career.

A "move" is a person's most recent change of employer: previous employer ->
current employer. Writes
  data/derived/talent_flows.csv   from_company, to_company, moves, people, functions, latest move
  data/derived/recent_moves.csv   everyone who started their current role in the last 6 months
and (when imported) exposes flows() for the atlas build.
"""
import json, glob, os, re, csv, collections
from datetime import date
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RECENT_MONTHS = 6

norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
STRIP = re.compile(r"\b(inc|llc|ltd|limited|corp|corporation|company|co|group|plc|holdings|the|us|usa|construction|contractors?|data ?cent(er|re)s?|engineering)\b\.?", re.I)
loose = lambda x: re.sub(r"[^a-z0-9]", "", STRIP.sub("", (x or "")).lower())

def ym(s):
    m = re.match(r"(?:(\d{1,2})/)?(\d{4})$", (s or "").strip())
    return (int(m.group(2)), int(m.group(1) or 6)) if m else None

def load():
    companies = {}
    for f in glob.glob(f"{REPO}/data/companies/*.json"):
        c = json.load(open(f)); companies[c["id"]] = c
    by_norm, by_loose = {}, collections.defaultdict(set)
    for cid, c in companies.items():
        for nm in [c["name"]] + (c.get("aliases") or []):
            by_norm[norm(nm)] = cid
            if loose(nm): by_loose[loose(nm)].add(cid)
    def resolve(name):
        n = norm(name)
        if n in by_norm: return by_norm[n]
        l = loose(name)
        if l and len(by_loose.get(l, ())) == 1: return next(iter(by_loose[l]))
        return None
    people = [json.load(open(f)) for f in glob.glob(f"{REPO}/data/people/*.json")]
    return companies, people, resolve

def flows():
    """-> (moves, recent). moves: list of dicts {person, from_name, from_id, to_id, to_name, function, title, start}."""
    companies, people, resolve = load()
    today = date.today(); cutoff = (today.year + (today.month - RECENT_MONTHS - 1) // 12, (today.month - RECENT_MONTHS - 1) % 12 + 1)
    moves, recent = [], []
    for p in people:
        cur_id = p.get("current_company_id")
        if not cur_id: continue
        career = [c for c in p.get("career", []) if c.get("company")]
        current = [c for c in career if c.get("current")]
        start = None
        if current:
            starts = [ym(c.get("start")) for c in current if ym(c.get("start"))]
            start = min(starts) if starts else None
        # previous employer = the most recent non-current entry at a different company
        here = norm(p.get("current_company"))
        prev = None
        for c in sorted([c for c in career if not c.get("current")], key=lambda c: ym(c.get("end")) or (0, 0), reverse=True):
            if norm(c["company"]) != here and not (here and (here in norm(c["company"]) or norm(c["company"]) in here)):
                prev = c; break
        rec = {"person": p["name"], "person_id": p["id"], "to_id": cur_id, "to_name": companies[cur_id]["name"],
               "function": p.get("function"), "title": p.get("current_title"), "start": f"{start[1]}/{start[0]}" if start else None,
               "from_name": prev["company"] if prev else None, "from_id": resolve(prev["company"]) if prev else None,
               "from_title": prev.get("title") if prev else None}
        if prev and rec["from_id"] != cur_id: moves.append(rec)  # a rename/alias of the same employer is not a move
        if start and start >= cutoff: recent.append(rec)
    return moves, recent

if __name__ == "__main__":
    companies, _, _ = load()
    moves, recent = flows()
    agg = collections.defaultdict(list)
    for m in moves: agg[(m["from_id"] or m["from_name"], m["to_id"])].append(m)
    rows = []
    for (frm, to), ms in agg.items():
        rows.append({"from_company": companies[frm]["name"] if frm in companies else frm, "from_tracked": frm in companies,
                     "to_company": companies[to]["name"], "moves": len(ms),
                     "people": "; ".join(sorted(m["person"] for m in ms)),
                     "functions": "; ".join(f"{k} {v}" for k, v in collections.Counter(m["function"] for m in ms).most_common()),
                     "latest_start": max((m["start"] or "" for m in ms), key=lambda s: ym(s) or (0, 0))})
    rows.sort(key=lambda r: (-r["moves"], r["to_company"], r["from_company"]))
    os.makedirs(f"{REPO}/data/derived", exist_ok=True)
    with open(f"{REPO}/data/derived/talent_flows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    recent.sort(key=lambda m: ym(m["start"]), reverse=True)
    with open(f"{REPO}/data/derived/recent_moves.csv", "w", newline="") as f:
        cols = ["person", "title", "to_name", "function", "start", "from_name", "from_title"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(recent)
    tracked = sum(1 for r in rows if r["from_tracked"])
    print(f"moves: {len(moves)} | flow pairs: {len(rows)} ({tracked} between tracked companies) | recent joiners (<= {RECENT_MONTHS} months): {len(recent)}")
    print("top flows:", [(r['from_company'], r['to_company'], r['moves']) for r in rows[:12]])
