#!/usr/bin/env python3
"""List every signal the notes carry -- who is open to a move, who has moved, who is
hiring, which companies a search should target, which deals we have heard about --
as one sheet to act on: data/derived/note_signals.csv, newest first.

A `moved` signal is a lead, not a fact: the person record is NOT changed. Check it,
then update the person by hand or in the next people import.
Reads only data/; no email, phone or pay ever reaches a note (import_notes refuses it).
"""
import json, glob, os, csv

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    names = {}
    for sub, prefix in (("companies", "company"), ("people", "person"), ("investors", "investor"), ("searches", "search")):
        for f in glob.glob(f"{REPO}/data/{sub}/*.json"):
            d = json.load(open(f)); names[f"{prefix}:{os.path.basename(f)[:-5]}"] = d.get("name")
    label = lambda v: names.get(v, v) if v else ""
    rows = []
    for f in glob.glob(f"{REPO}/data/notes/*.json"):
        n = json.load(open(f))
        for s in n.get("signals") or []:
            rows.append({"date": n["date"], "signal": s["type"], "person": label(s.get("person")),
                         "company": label(s.get("company")), "counterparty": label(s.get("counterparty")),
                         "search": label(s.get("search")), "title": s.get("title", ""),
                         "basis": "Ward's view" if n["basis"] == "ward_judgement" else "reported",
                         "note": n["summary"], "heard via": " · ".join(x for x in (n["source"].get("channel"), n["source"].get("from")) if x),
                         "note id": n["id"]})
    rows.sort(key=lambda r: r["date"], reverse=True)
    path = f"{REPO}/data/derived/note_signals.csv"
    cols = ["date", "signal", "person", "company", "counterparty", "search", "title", "basis", "note", "heard via", "note id"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} signals -> {path}")


if __name__ == "__main__":
    main()
