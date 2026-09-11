#!/usr/bin/env python3
"""Index the job titles in use, by company and by department (function), so a
search can start from the exact wording each company uses.

Writes data/derived/job_titles.csv (company, function, title, count, people)
and data/derived/job_titles_by_function.csv (function, title, count, companies).
"""
import json, glob, os, csv, collections
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(REPO, "data/derived")
os.makedirs(OUT, exist_ok=True)

def clean(t):  # collapse whitespace; keep the company's wording otherwise
    return " ".join((t or "").split())

def main():
    by_company = collections.defaultdict(lambda: collections.defaultdict(list))   # company -> function -> [(title, name)]
    by_function = collections.defaultdict(lambda: collections.defaultdict(set))   # function -> title -> {companies}
    count_function = collections.Counter()
    for path in glob.glob(os.path.join(REPO, "data/people/*.json")):
        p = json.load(open(path))
        title = clean(p.get("current_title"))
        if not title: continue
        company = p.get("current_company") or "(unknown employer)"
        fn = p.get("function") or "Unclassified"
        by_company[company][fn].append((title, p["name"]))
        by_function[fn][title].add(company)
        count_function[(fn, title)] += 1

    rows = []
    for company in sorted(by_company, key=str.lower):
        for fn, pairs in sorted(by_company[company].items()):
            titles = collections.defaultdict(list)
            for t, n in pairs: titles[t].append(n)
            for t, names in sorted(titles.items(), key=lambda kv: (-len(kv[1]), kv[0].lower())):
                rows.append({"company": company, "function": fn, "title": t, "count": len(names), "people": "; ".join(sorted(names))})
    with open(os.path.join(OUT, "job_titles.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["company", "function", "title", "count", "people"]); w.writeheader(); w.writerows(rows)

    rows2 = []
    for fn in sorted(by_function):
        for t, companies in sorted(by_function[fn].items(), key=lambda kv: (-count_function[(fn, kv[0])], kv[0].lower())):
            rows2.append({"function": fn, "title": t, "count": count_function[(fn, t)], "companies": len(companies),
                          "used_at": "; ".join(sorted(companies, key=str.lower))})
    with open(os.path.join(OUT, "job_titles_by_function.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["function", "title", "count", "companies", "used_at"]); w.writeheader(); w.writerows(rows2)

    print(f"{len(rows)} company/function/title rows across {len(by_company)} companies; {len(rows2)} distinct function/title pairs")


if __name__ == "__main__":
    main()
