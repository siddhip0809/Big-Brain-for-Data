#!/usr/bin/env python3
"""Strip contact details and pay figures out of free text on person records.

The importers drop the email and phone COLUMNS at read time, but people also
put their email, mobile and pay expectations inside their LinkedIn "About" text,
and that came through verbatim as `biography`. Rule 1 in CLAUDE.md is absolute,
so this scrubs every string field on every person record, replacing each hit
with a bracketed marker rather than deleting the sentence around it. Source URLs
are left alone.

    python3 scripts/scrub_people.py           # dry run: shows what would change
    python3 scripts/scrub_people.py --apply
"""
import json, glob, os, re, sys

APPLY = "--apply" in sys.argv
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?<![\w/=&.-])\+?\(?\d{2,4}\)?[ .-]\d{3,4}[ .-]\d{3,4}(?![\w/])")
# A pay figure is a money amount sitting next to a pay word. A bare "$850,000,000 of
# preconstruction deliverables" or "projects from $500K to $150M" is a career fact
# and stays; "seeks a minimum 150k EUR base salary" goes.
MONEY = r"(?:[$\u00a3\u20ac]\s?\d{2,3}(?:,\d{3})+|[$\u00a3\u20ac]?\s?\d{2,3}\s?[kK]\b(?:\s?(?:EUR|USD|GBP))?)(?:\s?(?:-|\u2013|to)\s?[$\u00a3\u20ac]?\s?\d{2,3}(?:,\d{3})*\s?[kK]?)?"
PAYWORD = r"(?:salary|salaries|base pay|base of|compensation|comp\b|package|bonus|\bOTE\b|on-target|expects?|expectation|seeking|seeks|asking|minimum of|current(?:ly)? (?:on|earning|paid))"
PAY = re.compile(rf"(?:{PAYWORD}[^.\n]{{0,60}}?{MONEY}|{MONEY}[^.\n]{{0,60}}?{PAYWORD})", re.I)
SKIP_KEYS = {"sources", "id", "linkedin", "current_company_id", "type"}


def scrub_text(s):
    hits = []
    def rep(rx, marker):
        nonlocal s
        for m in rx.finditer(s): hits.append(m.group(0))
        s = rx.sub(marker, s)
    rep(EMAIL, "[email removed]")
    rep(PHONE, "[phone removed]")
    rep(PAY, "[pay figure removed]")
    return s, hits


def scrub(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_KEYS: continue
            new, h = scrub(v, f"{path}.{k}")
            obj[k] = new; hits += h
        return obj, hits
    if isinstance(obj, list):
        out = []
        for v in obj:
            new, h = scrub(v, path); out.append(new); hits += h
        return out, hits
    if isinstance(obj, str) and not obj.startswith("http"):
        new, h = scrub_text(obj)
        return new, [(path, x) for x in h]
    return obj, hits


def main():
    changed, total = 0, 0
    for f in sorted(glob.glob(f"{REPO}/data/people/*.json")):
        p = json.load(open(f))
        p2, hits = scrub(json.loads(json.dumps(p)))
        if not hits: continue
        changed += 1; total += len(hits)
        print(f"{os.path.basename(f)}: " + "; ".join(f"{path.lstrip('.')} → `{x[:40]}`" for path, x in hits[:4]) + (" …" if len(hits) > 4 else ""))
        if APPLY:
            json.dump(p2, open(f, "w"), indent=2, ensure_ascii=False); open(f, "a").write("\n")
    print(f"\n{changed} records, {total} removals — {'APPLIED' if APPLY else 'dry run'}")


if __name__ == "__main__":
    main()
