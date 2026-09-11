#!/usr/bin/env python3
"""Build the gap list: the companies the brain holds almost nothing about.

Two questions Siddhi asked (2026-09-11):
  1. Which companies have no connection at all -- no backer, no lease, no
     deal, nothing linking them to anything else?
  2. Which companies are on the map but with nobody recorded as owning or
     backing them?

Plus the thing the brain cannot answer for ANY company: whether it is public,
private, PE-owned or a subsidiary. There is no ownership field on a company
record, so the sheet carries it as a column to fill for every row.

Writes an .xlsx to fill in and a .csv of the same rows for the repo.
Reads only; never writes to data/. Carries no email, phone or compensation.
"""
import json, glob, os, re, sys, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FONT = "Arial"

# a company is "connected" if it sits at either end of one of these. works_at
# is excluded on purpose: people are not nodes in the atlas, so a company with
# staff mapped but no deal still floats free on the map.
DEAL = {"invested_in", "acquired", "tenant_of", "jv_partner", "contractor_for",
        "supplies_power_to", "site_partner", "partnered_with", "competitor_of"}

ROLE_LABEL = {
    "hyperscaler": "Hyperscaler", "neocloud": "NeoCloud / AI infra",
    "cryptomining": "Cryptomining pivot", "developer_operator": "DC developer / operator",
    "energy_developer": "Energy developer / utility", "general_contractor": "General contractor",
    "civil_land_engineering": "Civil / land engineering",
    "real_estate_developer": "Real estate & industrial developer",
}
PARENT_LABEL = {
    "pure_play": "Pure-play data center", "real_estate": "Real estate / industrial",
    "energy_utilities": "Energy / utility", "telecom": "Telecom / network",
    "construction_engineering": "Construction / engineering", "diversified_conglomerate": "Conglomerate",
}

# what we want back, in the order it is easiest to research
FILL_COLS = [
    ("Ownership", 20, '"Public,Private,PE / infra-fund owned,Subsidiary of a listed group,Joint venture,State-owned,Unknown"',
     "Is it listed, privately held, owned by a fund, or an arm of something bigger?"),
    ("Listed as / owned by", 26, None, "Ticker if public, or the parent or fund that owns it."),
    ("Who backs them", 30, None, "Investors, funds or corporate backers. Semicolons between several."),
    ("Who they lease TO", 30, None, "Their customers -- the hyperscalers or enterprises taking capacity."),
    ("Who they lease FROM", 30, None, "Their landlords or wholesale providers, if they take space rather than own it."),
    ("Who builds for them", 26, None, "General contractor, EPC or engineer of record."),
    ("Power / utility partner", 26, None, "The utility, IPP or PPA counterparty behind the campus."),
    ("Still a real DC company?", 22, '"Yes,Acquired,Renamed,Dormant or dead,Not really a DC company,Unknown"',
     "Cross-check before we spend research time: some list rows are stale or were never DC businesses."),
    ("Source URL", 34, None, "Where you saw it. One link is enough -- it becomes the source on the record."),
    ("Notes", 34, None, "Anything else worth carrying: a campus name, a market, a person to ask."),
]


def load():
    comp = {}
    for f in glob.glob(f"{REPO}/data/companies/*.json"):
        c = json.load(open(f)); comp[c["id"]] = c
    rels = json.load(open(f"{REPO}/data/relationships.json"))
    investors = [json.load(open(f)) for f in glob.glob(f"{REPO}/data/investors/*.json")]
    return comp, rels, investors


def measure(comp, rels, investors):
    """degree, backer count and headcount-of-mapped-people per company id"""
    deg, back, partners = collections.Counter(), collections.Counter(), collections.defaultdict(set)
    name = lambda cid: (comp.get(cid) or {}).get("name", cid)
    for r in rels:
        if r.get("type") not in DEAL: continue
        ends = [e for e in (r["from"], r["to"])]
        for e in ends:
            if e.startswith("company:") and e[8:] in comp:
                deg[e[8:]] += 1
                other = ends[1] if e == ends[0] else ends[0]
                partners[e[8:]].add(name(other[8:]) if other.startswith("company:") else other.split(":", 1)[-1])
        # "who is behind this company" is answered by backing OR by an acquisition:
        # Blackstone/CPP own AirTrunk through an `acquired` edge, not an `invested_in` one.
        if r["type"] in ("invested_in", "acquired") and r["to"].startswith("company:"):
            back[r["to"][8:]] += 1
    for i in investors:                       # portfolios live on the investor record too
        for cid in i.get("investments") or []:
            if cid in comp:
                deg[cid] += 1; back[cid] += 1; partners[cid].add(i["name"])
    people = collections.Counter()
    for f in glob.glob(f"{REPO}/data/people/*.json"):
        cid = json.load(open(f)).get("current_company_id")
        if cid in comp: people[cid] += 1
    clients = collections.Counter()
    for f in glob.glob(f"{REPO}/data/searches/*.json"):
        cid = json.load(open(f)).get("client_company_id")
        if cid in comp: clients[cid] += 1
    return deg, back, partners, people, clients


def capacity(c):
    return sum((v.get("total_mw") or 0) + (v.get("early_stage_mw") or 0)
               for v in (c.get("capacity_mw") or {}).values())


def band(c, mw, npeople):
    """How much it would cost us to be wrong about this one."""
    if mw >= 250 or (npeople >= 5 and mw >= 50) or (c.get("headcount") or "").startswith(("1,001", "501", "5,001", "10,001")):
        return "A · Big and blank"
    if mw >= 50 or npeople >= 3 or c.get("hyperscale_focus") in ("Primary Focus", "Secondary Focus"):
        return "B · Worth a look"
    return "C · Small or unknown scale"


def country(c):
    hq = (c.get("headquarters") or "").strip()
    return hq.split(",")[-1].strip() if "," in hq else (hq or "")


def row_for(c, mw, npeople, nclients, partners):
    return {
        "Company": c["name"],
        "What they are": " + ".join(ROLE_LABEL.get(r, r) for r in (c.get("roles") or [])),
        "Kind of business": PARENT_LABEL.get(c.get("parent_industry"), c.get("parent_industry") or ""),
        "HQ": c.get("headquarters") or "",
        "Country": country(c),
        "Staff (company)": c.get("headcount") or "",
        "Capacity MW": round(mw) if mw else "",
        "Hyperscale focus": c.get("hyperscale_focus") or "",
        "People we have mapped": npeople or "",
        "Ward searches": nclients or "",
        "Already linked to": "; ".join(sorted(partners)[:6]),
        "Website": c.get("website") or "",
        "LinkedIn": c.get("linkedin") or "",
        "Where the name came from": "; ".join(c.get("source_lists") or []) or "Clockwork / research",
        "id": c["id"],
    }


HELD_COLS = ["Company", "What they are", "Kind of business", "HQ", "Country", "Staff (company)",
             "Capacity MW", "Hyperscale focus", "People we have mapped", "Ward searches",
             "Already linked to", "Website", "LinkedIn", "Where the name came from"]
WIDTHS = {"Company": 34, "What they are": 26, "Kind of business": 24, "HQ": 30, "Country": 16,
          "Staff (company)": 13, "Capacity MW": 12, "Hyperscale focus": 15,
          "People we have mapped": 13, "Ward searches": 11, "Already linked to": 40,
          "Website": 30, "LinkedIn": 30, "Where the name came from": 26}


def write_sheet(wb, title, rows, blurb, show_band):
    ws = wb.create_sheet(title)
    cols = (["#"] + (["Band"] if show_band else []) + HELD_COLS + [c[0] for c in FILL_COLS])
    ws.append([blurb] + [""] * (len(cols) - 1))
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols))
    ws["A1"].font = Font(name=FONT, size=10, italic=True, color="44546A")
    ws["A1"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 30
    ws.append(cols)
    head_row = 2
    first_fill = 1 + (1 if show_band else 0) + len(HELD_COLS) + 1
    for j, c in enumerate(ws[head_row], start=1):
        c.font = Font(name=FONT, bold=True, color="FFFFFF", size=10)
        c.fill = PatternFill("solid", fgColor="2E7D5B" if j >= first_fill else "0B3D5C")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for k, (label, _w, _dv, note) in enumerate(FILL_COLS):
        ws.cell(row=head_row, column=first_fill + k).comment = Comment(note, "Claude")
    ws.row_dimensions[head_row].height = 34

    BAND_FILL = {"A · Big and blank": "FBE3E3", "B · Worth a look": "FDF0DC", "C · Small or unknown scale": "FFFFFF"}
    thin = Side(style="thin", color="D9D9D9")
    for i, r in enumerate(rows, start=1):
        vals = [i] + ([r["Band"]] if show_band else []) + [r[c] for c in HELD_COLS] + [""] * len(FILL_COLS)
        ws.append(vals)
        row = ws.max_row
        fill = PatternFill("solid", fgColor=BAND_FILL.get(r.get("Band"), "FFFFFF"))
        for j in range(1, len(cols) + 1):
            cell = ws.cell(row=row, column=j)
            cell.font = Font(name=FONT, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=(j >= first_fill or cols[j - 1] in ("HQ", "Already linked to")))
            cell.border = Border(bottom=thin)
            cell.fill = PatternFill("solid", fgColor="F2F8F4") if j >= first_fill else fill

    n = ws.max_row
    for k, (label, w, dv_list, _note) in enumerate(FILL_COLS):
        col = get_column_letter(first_fill + k)
        ws.column_dimensions[col].width = w
        if dv_list and n > head_row:
            dv = DataValidation(type="list", formula1=dv_list, allow_blank=True, showDropDown=False)
            ws.add_data_validation(dv); dv.add(f"{col}{head_row+1}:{col}{n}")
    for j, name in enumerate(cols, start=1):
        if name in WIDTHS: ws.column_dimensions[get_column_letter(j)].width = WIDTHS[name]
    ws.column_dimensions["A"].width = 5
    if show_band: ws.column_dimensions["B"].width = 24
    ws.freeze_panes = ws.cell(row=head_row + 1, column=(3 if show_band else 2))
    ws.auto_filter.ref = f"A{head_row}:{get_column_letter(len(cols))}{n}"
    return ws


def main():
    out_xlsx = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "company_gap_list.xlsx")
    comp, rels, investors = load()
    deg, back, partners, people, clients = measure(comp, rels, investors)

    unconnected, no_backer = [], []
    for c in sorted(comp.values(), key=lambda x: x["name"].lower()):
        cid, mw, np_ = c["id"], capacity(c), people[c["id"]]
        r = row_for(c, mw, np_, clients[cid], partners[cid])
        if not deg[cid]:
            r["Band"] = band(c, mw, np_); r["_mw"] = mw
            unconnected.append(r)
        elif not back[cid]:
            r["_mw"] = mw
            no_backer.append(r)

    order = {"A · Big and blank": 0, "B · Worth a look": 1, "C · Small or unknown scale": 2}
    unconnected.sort(key=lambda r: (order[r["Band"]], -r["_mw"], r["Company"].lower()))
    no_backer.sort(key=lambda r: (-r["_mw"], r["Company"].lower()))

    wb = Workbook(); wb.remove(wb.active)
    write_sheet(wb, "No connection at all", unconnected,
                "Every company in the brain with no backer, no lease, no deal, no partner of any kind — nothing ties it to anything else, "
                "so it floats free on the map. Green columns are for you to fill; everything to the left is what we already hold. "
                "Band A first: the big ones we know nothing about.", show_band=True)
    write_sheet(wb, "No owner on record", no_backer,
                "These have a lease, a deal or a build relationship, so they are on the map — but nobody is recorded as owning or backing them. "
                "Some will simply be listed companies with no single owner, which is itself the answer we want in the Ownership column. "
                "Sorted biggest first by capacity.", show_band=False)

    # ---- read me ----
    ws = wb.create_sheet("Read me", 0)
    tot = len(comp)
    lines = [
        ("Company gap list", 16, True),
        ("", 11, False),
        (f"Generated {__import__('datetime').date.today().isoformat()} from the brain. Re-run scripts/build_gap_list.py any time to refresh it.", 11, False),
        ("", 11, False),
        ("What is in here", 13, True),
        (f"Tab 1 — No connection at all ({len(unconnected)} of {tot} companies). No investor, no lease, no acquisition, no JV, no build or power "
         "relationship. We hold the name, usually a website and a headcount, sometimes a capacity figure, and nothing about who they deal with.", 11, False),
        (f"Tab 2 — No owner on record ({len(no_backer)} companies). They have a deal or a lease, so they sit on the map, but nothing says who owns or "
         "backs them. A public company like Digital Realty belongs here legitimately — write \"Public\" and it is answered. AirTrunk does not: "
         "Blackstone and CPP bought it in 2024 and that is on the record, which is why it is not in this list.", 11, False),
        ("", 11, False),
        ("The one thing we do not hold for ANY company", 13, True),
        (f"Public or private. There is no ownership field on a company record — not for these {len(unconnected)}, not for the other "
         f"{tot - len(unconnected)} either. The Ownership column is how it gets into the brain for the first time, so it is worth filling even on a "
         "company you are not otherwise researching.", 11, False),
        ("", 11, False),
        ("How the bands work on tab 1", 13, True),
        ("A · Big and blank — 250 MW or more, or a real staff count, or people we have already mapped there. Being wrong about these is expensive.", 11, False),
        ("B · Worth a look — 50 MW or more, or three-plus people mapped, or flagged hyperscale-focused on your sheet.", 11, False),
        ("C · Small or unknown scale — no capacity figure and nothing else to go on. Many will turn out not to be real DC businesses, which is "
         "itself a useful answer: mark them under \"Still a real DC company?\" and I will retire the record.", 11, False),
        ("", 11, False),
        ("What happens when you send it back", 13, True),
        ("Every filled row becomes sourced data: Ownership and the owner go onto the company record, and each \"leases to / leases from / builds for / "
         "power partner\" name becomes a relationship — a line on the map — with your Source URL attached and marked as checked by you. "
         "A row with a name but no URL still goes in, marked as told by Siddhi rather than researched.", 11, False),
        ("", 11, False),
        ("You do not have to fill it all", 13, True),
        ("The Ownership column alone, on band A, would be the single biggest improvement to the map. Everything else is a bonus. "
         "Partial rows are fine — anything blank simply stays unknown.", 11, False),
    ]
    for i, (text, size, bold) in enumerate(lines, start=1):
        ws[f"A{i}"] = text
        ws[f"A{i}"].font = Font(name=FONT, size=size, bold=bold)
        ws[f"A{i}"].alignment = Alignment(wrap_text=True, vertical="top")
        if len(text) > 110: ws.row_dimensions[i].height = 30 * (1 + len(text) // 150)
    ws.column_dimensions["A"].width = 122

    # ---- counts ----
    ws = wb.create_sheet("Counts")
    ws.append(["Band", "Companies"])
    for b, n in collections.Counter(r["Band"] for r in unconnected).most_common():
        ws.append([b, n])
    ws.append([]); ws.append(["By what they are", "Companies"])
    for k, n in collections.Counter(r["What they are"] for r in unconnected).most_common():
        ws.append([k, n])
    ws.append([]); ws.append(["By country", "Companies"])
    for k, n in collections.Counter(r["Country"] or "not recorded" for r in unconnected).most_common(20):
        ws.append([k, n])
    for row in ws.iter_rows():
        for c in row: c.font = Font(name=FONT, size=10, bold=(c.row in (1,) or c.value in ("By what they are", "By country")))
    ws.column_dimensions["A"].width = 42; ws.column_dimensions["B"].width = 12

    wb.save(out_xlsx)

    # ---- csv of the same rows, for the repo ----
    import csv
    csv_path = os.path.join(REPO, "data/derived/company_gaps.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gap", "band"] + HELD_COLS + ["company_id"])
        for r in unconnected:
            w.writerow(["no connection at all", r["Band"]] + [r[c] for c in HELD_COLS] + [r["id"]])
        for r in no_backer:
            w.writerow(["no owner on record", ""] + [r[c] for c in HELD_COLS] + [r["id"]])

    print(f"companies: {tot}")
    print(f"no connection at all: {len(unconnected)}  {dict(collections.Counter(r['Band'] for r in unconnected))}")
    print(f"on the map but no owner on record: {len(no_backer)}")
    print("wrote:", out_xlsx)
    print("wrote:", csv_path)


if __name__ == "__main__":
    main()
