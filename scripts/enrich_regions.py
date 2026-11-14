#!/usr/bin/env python3
"""Give a company with a headquarters and no `region` the region its neighbours have.

`region` (USA / EMEA / APAC / Americas (other) / Multi-region) arrived with the companies
recovered from the published atlas on 2026-11-14, already set. Rather than keep a country
table, this learns from those records: the last part of `headquarters` ("..., United
Kingdom") decides the region when every company that already has one agrees on it. A place
no record vouches for is left blank and listed, never guessed.

    python3 scripts/enrich_regions.py            # dry run
    python3 scripts/enrich_regions.py --apply
"""
import json, glob, os, sys, collections

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
place = lambda hq: hq.split(",")[-1].strip().lower()


def main():
    apply_ = "--apply" in sys.argv
    recs = {f: json.load(open(f)) for f in sorted(glob.glob(f"{REPO}/data/companies/*.json"))}
    seen = collections.defaultdict(set)
    for c in recs.values():
        if c.get("headquarters") and c.get("region") and not c.get("region_basis"): seen[place(c["headquarters"])].add(c["region"])
    filled, unknown = [], collections.Counter()
    for f, c in recs.items():
        if c.get("region") or not c.get("headquarters"): continue
        regions = seen.get(place(c["headquarters"]), set())
        if len(regions) != 1: unknown[c["headquarters"].split(",")[-1].strip()] += 1; continue
        c["region"] = next(iter(regions)); filled.append(f"{c['id']} -> {c['region']}")
        if apply_:
            json.dump(c, open(f, "w"), indent=2, ensure_ascii=False); open(f, "a").write("\n")
    print(f"regions filled: {len(filled)}" + ("" if apply_ else "  (dry run)"))
    for x in filled[:30]: print("  ", x)
    if unknown: print("no region yet, place not vouched for by another record:", ", ".join(f"{k} ({v})" for k, v in unknown.most_common()))


if __name__ == "__main__":
    main()
