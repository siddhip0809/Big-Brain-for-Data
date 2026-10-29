#!/usr/bin/env python3
"""Turn what Ward hears -- from candidates, clients, the market -- into notes in the brain.

A note is one piece of intelligence, linked to the people, companies and search it
is about. Input is a JSON list drafted by Claude from emails, call transcripts,
Word documents or the atlas note box (see "Intake" in CLAUDE.md):

  {"date": "2026-10-27",                 # when we heard it
   "kind": "client_brief",               # see KINDS
   "basis": "reported",                  # reported = someone told us; ward_judgement = our own view
   "summary": "...",                     # 1-4 sentences in our words, never pasted text
   "companies": ["Equinix"], "people": ["Jane Doe"],   # names; resolved against the brain
   "search": "vp-development-emea",      # a search on file (slug or name), or null
   "search_check": "...",                # required when the note is about a search NOT on
                                         # file: the Clockwork confidential check, e.g.
                                         # "clockwork 2026-10-29: not confidential"
   "discretion": true,                   # the person asked for discretion / it was told in confidence
   "signals": [{"type": "open_to_move", "person": "Jane Doe"}, ...],   # see SIGNALS
   "source": {"channel": "email", "date": "...", "from": "Ward", "subject": "...",
              "message_id": "<...>"}}    # message_id is hashed, never stored
  {"skip": "admin", "source": {...}}     # a message read and judged not worth a note: logged only
  "names": [...] instead of companies/people: each is tried as a company, then a person.

Or a folder: the atlas note box's saved notes, exported with the Artifact tool
(read_db, collection "notes_inbox"). Each becomes a note with channel "atlas".

Rules this enforces, so intake can never quietly break the brain's hard rules:
  - rule 1: email addresses, phone numbers and pay figures are stripped from every
    string; a note that talks about pay at all (salary, bonus, compensation, OTE,
    day rate ...) is refused, as is one touching health, family, religion or other
    special-category matters. Nothing is kept from the raw message but a hash.
  - rule 2: a note about a search that is not on file is refused unless it carries a
    search_check saying Clockwork marks it not confidential.
  - rule 3: every note carries its source (channel, date, who it came from).
  - rule 4: basis says whether it is a fact we were told or Ward's judgement.
  - the same message never produces the same note twice; data/intake_log.json records
    every message read (as a hash), so the next run starts where this one stopped.

    python3 scripts/import_notes.py <file.json | notes_inbox folder>   # dry run
    python3 scripts/import_notes.py <file.json> --apply
"""
import json, glob, os, re, sys, hashlib
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrub_people import scrub_text
from import_researched_companies import company_index, investor_index, match, norm

APPLY = "--apply" in sys.argv
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NOTES = os.path.join(REPO, "data/notes")
LOG = os.path.join(REPO, "data/intake_log.json")
TODAY = str(date.today())

KINDS = {"candidate_update", "client_brief", "client_feedback", "search_strategy", "market_intel", "relationship"}
SEARCH_KINDS = {"client_brief", "client_feedback", "search_strategy"}
BASES = {"reported", "ward_judgement"}
CHANNELS = {"email", "teams", "call", "meeting", "transcript", "document", "linkedin", "atlas", "other"}
SIGNALS = {  # type -> fields it needs
    "open_to_move": ["person"], "not_looking": ["person"], "moved": ["person", "company"],
    "interviewing": ["person"], "hiring": ["company"], "target_company": ["company"],
    "deal": ["company", "counterparty"],
}
PAY_TALK = re.compile(r"\b(salar(y|ies)|compensation|remuneration|bonus(es)?|base pay|OTE|on[- ]target earnings|day rate|pay (rise|cut|expectation)|package (of|at|around))\b", re.I)
SPECIAL = re.compile(r"\b(pregnan\w*|maternity|paternity|illness|ill health|health (scare|issue|problem|condition)s?|sick\w*|hospital\w*|diagnos\w*|cancer|surgery|mental health|disab\w*|divorc\w*|religio\w*|sexual\w*|ethnicit\w*|criminal|bereave\w*|funeral|medical)\b", re.I)
# any run of 9+ digits with separators is treated as a phone number in a note -- stricter than the
# people scrubber, whose pattern has to tolerate figures in 9,000 imported biographies
def phoneish(text): return any(sum(c.isdigit() for c in m) >= 9 for m in re.findall(r"\+?\d[\d ()\-.]{7,}\d", text))


def people_index():
    by_name = {}
    for f in glob.glob(f"{REPO}/data/people/*.json"):
        p = json.load(open(f))
        by_name.setdefault(norm(p.get("name")), []).append((p["id"], p.get("current_company_id")))
    return by_name


def search_index():
    out = {}
    for f in glob.glob(f"{REPO}/data/searches/*.json"):
        s = json.load(open(f)); slug = os.path.basename(f)[:-5]
        out[slug] = (slug, s.get("client_company_id"))
        out.setdefault(norm(s.get("name")) + "|" + norm(s.get("client_company")), (slug, s.get("client_company_id")))
        out.setdefault(norm(s.get("name")), (slug, s.get("client_company_id")))
    return out


def load_rows(path):
    if not os.path.isdir(path): return json.load(open(path))
    rows = []
    for f in sorted(glob.glob(os.path.join(path, "*.json"))):
        d = json.load(open(f)); d = d.get("data", d); aid = os.path.basename(f)[:-5]
        rows.append({**{k: d.get(k) for k in ("date", "kind", "basis", "summary", "names", "search", "search_check")},
                     "recorded_by": d.get("by") or "atlas note box",
                     "source": {"channel": "atlas", "date": d.get("date"), "from": d.get("by") or "atlas note box",
                                "atlas_id": aid, "message_id": "atlas:" + aid}})
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: print(__doc__); sys.exit(2)
    rows = load_rows(args[0])
    by_norm, by_loose, _ = company_index(); investors = investor_index()
    people, searches = people_index(), search_index()
    log = json.load(open(LOG)) if os.path.exists(LOG) else []
    have = {os.path.basename(f)[:-5] for f in glob.glob(f"{NOTES}/*.json")}
    added, refused, skipped, unmatched = [], [], [], []

    def company_ref(name):
        cid = match(name, by_norm, by_loose)
        if cid: return f"company:{cid}"
        iid = investors.get(norm(name))
        return f"investor:{iid}" if iid else None

    def person_ref(name, company_ids):
        hits = people.get(norm(name)) or []
        if len(hits) == 1: return f"person:{hits[0][0]}"
        near = [pid for pid, cid in hits if cid in company_ids]
        return f"person:{near[0]}" if len(near) == 1 else None

    def search_ref(s):
        if not s: return None, None
        return searches.get(s) or searches.get(norm(s)) or (None, None)

    def clean(s): return scrub_text(s or "")[0].strip()

    for r in rows:
        src = dict(r.get("source") or {})
        mid = src.pop("message_id", None) or src.pop("id", None)
        ref = "sha1:" + hashlib.sha1((mid or json.dumps(r, sort_keys=True)).encode()).hexdigest()[:16]
        src = {k: clean(str(v)) for k, v in src.items() if v}
        label = f"{src.get('date', '?')} {src.get('subject') or clean(r.get('summary'))[:50]}"
        if r.get("skip"):
            skipped.append(f"{label}  ({r['skip']})")
            log.append({"ref": ref, "date": src.get("date"), "outcome": "skipped: " + clean(r["skip"])[:40], "logged": TODAY}); continue

        why = []
        summary = clean(r.get("summary"))
        if not summary: why.append("no summary")
        if r.get("kind") not in KINDS: why.append(f"kind `{r.get('kind')}` not one of {sorted(KINDS)}")
        if r.get("basis") not in BASES: why.append("basis must be reported or ward_judgement")
        if src.get("channel") not in CHANNELS or not src.get("date"): why.append("source needs a channel and a date")
        text = " ".join([summary, json.dumps(r.get("signals") or []), src.get("from", ""), src.get("subject", "")])
        if PAY_TALK.search(text): why.append(f"talks about pay (`{PAY_TALK.search(text).group(0)}`) -- rule 1")
        if SPECIAL.search(text): why.append(f"special-category detail (`{SPECIAL.search(text).group(0)}`) -- leave it out")
        if phoneish(text) or "[email removed]" in text: why.append("contains contact details -- rule 1")

        names = [clean(n) for n in r.get("names") or []]
        r_people = list(r.get("people") or []) + [n for n in names if not company_ref(n)]
        r_comps = list(r.get("companies") or []) + [n for n in names if company_ref(n)]
        companies = [x for x in (company_ref(n) for n in r_comps) if x]
        miss = [n for n in r_comps if not company_ref(n)]
        slug, client = search_ref(r.get("search"))
        if r.get("search") and not slug: miss.append(f"search: {r['search']}")
        if client and f"company:{client}" not in companies: companies.append(f"company:{client}")
        cids = {c.split(":", 1)[1] for c in companies}
        persons = []
        for n in r_people:
            p = person_ref(n, cids)
            (persons.append(p) if p else miss.append(n))
        is_search = r.get("kind") in SEARCH_KINDS or any(s.get("type") == "interviewing" for s in r.get("signals") or [])
        check = clean(r.get("search_check"))
        if is_search and not slug and "not confidential" not in check.lower():
            why.append("about a search that is not on file: needs search_check confirming Clockwork marks it not confidential -- rule 2")

        sigs = []
        for s in r.get("signals") or []:
            t = s.get("type")
            if t not in SIGNALS: why.append(f"signal type `{t}`"); continue
            out = {"type": t}
            for fld in ("person", "company", "counterparty", "search", "title", "relation"):
                v = s.get(fld)
                if not v: continue
                v = clean(v)
                rv = person_ref(v, cids) if fld == "person" else company_ref(v) if fld in ("company", "counterparty") else \
                     (("search:" + search_ref(v)[0]) if search_ref(v)[0] else None) if fld == "search" else None
                out[fld] = rv or v                      # unresolved names stay as text, flagged below
                if fld in ("person", "company", "counterparty") and not rv: miss.append(v)
            if any(f not in out for f in SIGNALS[t]): why.append(f"signal {t} needs {SIGNALS[t]}")
            sigs.append(out)

        nid = f"{r.get('date') or src.get('date', '')[:10]}-" + hashlib.sha1((ref + (r.get('kind') or '') + summary).encode()).hexdigest()[:8]
        if why: refused.append(f"{label}: " + "; ".join(why)); continue
        if nid in have: skipped.append(f"{label}  (already in the brain as {nid})"); continue
        about = list(dict.fromkeys(persons + companies + ([f"search:{slug}"] if slug else [])))
        note = {"id": nid, "type": "note", "date": r.get("date") or src["date"][:10], "kind": r["kind"], "basis": r["basis"],
                "summary": summary, "about": about, "signals": sigs, "mentions_unmatched": sorted(set(miss)),
                "search_check": check if (is_search and not slug) else None,
                "discretion": True if r.get("discretion") else None,
                "source": dict(src, ref=ref), "recorded_on": TODAY,
                "recorded_by": clean(r.get("recorded_by")) or "Claude (intake)"}
        note = {k: v for k, v in note.items() if v not in (None, [], "")}
        if APPLY:
            p = os.path.join(NOTES, nid + ".json")
            json.dump(note, open(p, "w"), indent=2, ensure_ascii=False); open(p, "a").write("\n")
        have.add(nid); added.append(f"{note['date']} {note['kind']:16s} {summary[:90]}  -> {len(about)} links")
        if miss: unmatched.append(f"{nid}: " + ", ".join(sorted(set(miss))))
        if not any(e["ref"] == ref and e["outcome"] == "notes" for e in log):
            log.append({"ref": ref, "date": src.get("date"), "outcome": "notes", "logged": TODAY})

    if APPLY:
        json.dump(log, open(LOG, "w"), indent=1, ensure_ascii=False); open(LOG, "a").write("\n")
    print(f"notes added {len(added)}   refused {len(refused)}   skipped {len(skipped)}")
    for x in refused: print("  REFUSED ", x)
    for x in added: print("  + ", x)
    for x in unmatched: print("  not in the brain yet ", x)
    print("\nAPPLIED -- rerun the pipeline" if APPLY else "\ndry run")


if __name__ == "__main__":
    main()
