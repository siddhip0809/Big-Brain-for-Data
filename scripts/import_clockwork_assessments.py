#!/usr/bin/env python3
"""Import Ward Search's own assessment layer from the Clockwork exports onto
the existing person records: skill confidences, top-tier flags, tenure
judgement, candidate rating, "spoken with before", the hyperscaler-equivalent
seniority tag, education and biography.

"Under Represented Group" is included at Siddhi's explicit instruction
(2026-09-09) for diverse-slate reporting. Note it is Ward's own
observation, not self-declared by the candidate — Clockwork's own
"Not Apparent" value makes that plain — so it belongs in aggregate slate
reporting, not in anything shown to a client or the candidate.

Deliberately NOT imported:
  - email, phone, compensation — the standing rule (see docs/schema.md).

These are Ward's subjective judgements, not researched facts, so everything
lands under `assessment` with `assessment_source` naming the export.

Usage: python3 scripts/import_clockwork_assessments.py <export.xlsx>... [--apply]
"""
import json, glob, os, re, sys, collections
from datetime import date
import openpyxl

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APPLY = "--apply" in sys.argv
FILES = [a for a in sys.argv[1:] if a.endswith(".xlsx")]
TODAY = str(date.today())

# Clockwork column -> the skill name we store
SKILLS = {
    "Tag F   Dev Site Acquisition": "Development · site acquisition",
    "Tag F   Dev Permitting & Entitlements": "Development · permitting & entitlements",
    "Tag F   Dev Financial Modelling": "Development · financial modelling",
    "Tag F   Pre Con Estimating & Control": "Pre-Construction · estimating & cost control",
    "Tag F   Pre Con Project Schedueling": "Pre-Construction · project scheduling",
    "Tag F   Sales Selling": "Sales · selling",
    "Tag F   Sales Leasing": "Sales · leasing",
    "Tag F   Energy (Esa) Negotiation": "Energy · ESA negotiation",
    "Tag F   Energy Interconnection & Transmission Negotiation": "Energy · interconnection & transmission negotiation",
    "Tag F   Energy Transmission Engineering": "Energy · transmission engineering",
    "Tag F   Water Water Service Agreement (Wsa) Negotiation": "Water · WSA negotiation",
    "Tag F   Water Engineering": "Water · engineering",
}
SKIP_VALUES = {None, "", "Not applicable", "Not Applicable", "not applicable"}
EXCLUDED = set()                                # email/phone/comp are never read at all
clean = lambda v: (v.strip() or None) if isinstance(v, str) else v
squash = lambda h: re.sub(r"\s+", " ", h).strip() if isinstance(h, str) else h
SKILLS_SQ = {squash(k): v for k, v in SKILLS.items()}

by_suffix = {}
for f in glob.glob(f"{REPO}/data/people/*.json"):
    by_suffix.setdefault(os.path.basename(f)[:-5].rsplit("-", 1)[-1], f)

found = collections.Counter(); per_field = collections.Counter(); updated = {}
for path in FILES:
    ws = openpyxl.load_workbook(path, data_only=True, read_only=True)["Candidates"]
    rows = list(ws.iter_rows(values_only=True))
    idx = {squash(h): i for i, h in enumerate(rows[0]) if h}
    col = lambda r, h: clean(r[idx[h]]) if h in idx else None
    for r in rows[1:]:
        pid = r[idx["Person Id"]] if "Person Id" in idx else None
        if not pid: continue
        f = by_suffix.get(str(pid)[:8])
        if not f: found["person not in brain"] += 1; continue
        p = updated.get(f) or json.load(open(f))
        a = dict(p.get("assessment") or {})
        skills = dict(a.get("skills") or {})
        for hdr, label in SKILLS_SQ.items():
            v = col(r, hdr)
            if v not in SKIP_VALUES: skills[label] = v
        if skills: a["skills"] = skills; per_field["skills"] += 1
        tt = col(r, "Tag F Top Tier")
        if tt and tt not in SKIP_VALUES:
            a["top_tier"] = sorted({x.strip() for x in str(tt).split(";") if x.strip()}); per_field["top_tier"] += 1
        ten = col(r, "Tenure")
        if ten not in SKIP_VALUES: a["tenure"] = ten; per_field["tenure"] += 1
        rating = col(r, "Candidate Ratings")
        try: rating = float(rating)
        except (TypeError, ValueError): rating = None
        if rating: a["rating"] = rating; per_field["rating"] += 1        # 0.0 means unrated
        if col(r, "Tag Spoken With Before") == "Yes": a["spoken_with_before"] = True; per_field["spoken_with_before"] += 1
        urg = col(r, "Under Represented Group")
        if urg not in SKIP_VALUES:
            a["under_represented_group"] = urg; per_field["under_represented_group"] += 1
        eq = col(r, "Tag E Dc Developer Equivalent Seniority(for Hyperscalers)")
        if eq not in SKIP_VALUES: a["hyperscaler_equivalent_seniority"] = eq; per_field["equivalent_seniority"] += 1
        edu = col(r, "All Education")
        if edu: p["education"] = [e.strip() for e in str(edu).split(";") if e.strip()]; per_field["education"] += 1
        bio = col(r, "Biography")
        if bio: p["biography"] = bio; per_field["biography"] += 1
        if a:
            a["source"] = f"Clockwork export ({os.path.basename(path).split('-', 1)[-1]}), imported {TODAY}"
            a["note"] = "Ward Search's own judgement, not a researched fact."
            p["assessment"] = a
        p["last_updated"] = TODAY
        updated[f] = p; found["matched"] += 1

if APPLY:
    for f, p in updated.items():
        json.dump(p, open(f, "w"), indent=2, ensure_ascii=False); open(f, "a").write("\n")
print("rows:", dict(found), "| people updated:", len(updated))
print("fields written:", dict(per_field))
print("never imported: email / phone / compensation")
print("APPLIED" if APPLY else "dry run")
