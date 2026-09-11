#!/usr/bin/env python3
"""Build the validation workbook: every claim in the brain that rests on
research or on Claude's judgement, one row each, with a ✅/❎ dropdown."""
import json, glob, re, collections, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

import sys
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "validation_checklist.xlsx")
FONT = "Arial"
isurl = lambda s: isinstance(s, str) and re.match(r"^https?://", s.strip())

def main():
    cs, iv = {}, {}
    for f in glob.glob(f"{REPO}/data/companies/*.json"):
        c = json.load(open(f)); cs[c["id"]] = c
    for f in glob.glob(f"{REPO}/data/investors/*.json"):
        c = json.load(open(f)); iv[c["id"]] = c
    name_of = lambda ref: (cs.get(ref[8:], {}).get("name") if ref.startswith("company:") else iv.get(ref[9:], {}).get("name")) or ref
    rels = json.load(open(f"{REPO}/data/relationships.json"))
    DEAL = {"invested_in", "tenant_of", "acquired", "jv_partner", "contractor_for", "supplies_power_to", "site_partner"}
    TYPE_LABEL = {"invested_in": "Investor backing", "tenant_of": "Lease / tenant", "acquired": "Acquisition",
                  "jv_partner": "Joint venture", "contractor_for": "Builds / engineers for",
                  "supplies_power_to": "Supplies power to", "site_partner": "Land / campus partner"}

    rows = []
    def add(priority, group, what, claim, why, sources, ref=""):
        rows.append({"Priority": priority, "What to check": group, "Item": what, "The claim as recorded": claim,
                     "Why it is on this list": why, "Sources": sources, "ref": ref})

    # ---- 1. relationships: unsupported, corrected, partial, then the rest ----
    for r in rels:
        if r["type"] not in DEAL: continue
        a, b = name_of(r["from"]), name_of(r["to"])
        label = TYPE_LABEL[r["type"]]
        detail = (r.get("detail") or "").strip()
        note = ""
        m = re.search(r"— Re-sourcing note \(2026-09-08\): (.*)$", detail, re.S)
        if m: note = m.group(1).strip(); detail = detail[:m.start()].strip()
        urls = [s.strip() for s in r.get("sources", []) if isurl(s)]
        ver = (r.get("verification") or "").split(" (")[0]
        conf = r.get("confidence") or ""
        claim = f"{a} → {b} ({label}){' · ' + r['status'] if r.get('status') else ''}\n{detail}"
        if not urls:
            add(1, "Claim with no source", f"{a} → {b}", claim,
                "No page could be found naming both parties and this deal. Marked unsupported — likeliest to be wrong.", "", r["type"])
        elif ver == "none":
            add(1, "Claim with no source", f"{a} → {b}", claim,
                "Re-sourcing found nothing supporting this. Marked unsupported.", " | ".join(urls), r["type"])
        elif note:
            add(2, "Sources say something different", f"{a} → {b}", claim,
                "What the sources actually say: " + note, " | ".join(urls), r["type"])
        elif ver == "partial":
            add(3, "Only partly supported", f"{a} → {b}", claim,
                "A source names both parties but does not confirm the figures or terms.", " | ".join(urls), r["type"])
        elif conf in ("medium", "medium-high"):
            add(4, "Single-source claim", f"{a} → {b}", claim,
                "Rests on one press source rather than an announcement or filing.", " | ".join(urls), r["type"])
        else:
            add(6, "Well-sourced claim", f"{a} → {b}", claim,
                "An announcement, filing or two independent sources. Spot-check only.", " | ".join(urls), r["type"])

    # ---- 2. classifications that came from a sheet cell or a keyword rule ----
    AI_APP = {"cursor", "harvey-ai", "figure-ai", "ambience-healthcare", "xtx-markets", "corning", "intel", "anthropic", "cerebras", "amd", "nvidia", "bytedance", "tiktok", "openai"}
    for cid, c in cs.items():
        if "neocloud" in c["roles"] and cid in AI_APP:
            add(2, "Is this really a NeoCloud?", c["name"],
                f"Filed as NeoCloud / AI Infra (roles: {', '.join(c['roles'])})",
                "Typed \"Neocloud\" on your Data Centre Developer sheet, but it reads as an AI application or hardware company rather than infrastructure. Tick if the tier is right; cross and I will re-file it.",
                c.get("website") or "")
        t = (c.get("list_attributes", {}).get("Data Centre Developer", {}) or {}).get("Type")
        if t == "Hyperscale" and "hyperscaler" not in c["roles"]:
            add(3, "Hyperscaler or not?", c["name"],
                f"Your sheet types this \"Hyperscale\"; the brain files it as {', '.join(c['roles'])}",
                "You defined hyperscaler narrowly (own global platform), so I kept it out of that tier. Tick to keep it as is, cross to promote it.",
                c.get("website") or "")
    HYPER = [c["name"] for c in cs.values() if "hyperscaler" in c["roles"]]
    add(2, "Is this really a NeoCloud?", "The hyperscaler list itself",
        "Hyperscalers in the brain: " + ", ".join(sorted(HYPER)),
        "You said roughly five or six true hyperscalers. This is the current list, including the Chinese platforms. Tick if right, cross and tell me who to remove.", "")

    # ---- 3. merges and name resolutions done on judgement ----
    JUDGEMENT = [
        ("Polar → Polar DC", "Merged the Clockwork stub \"Polar\" into \"Polar DC\" (London data-center developer)",
         "Same name, and the one person is London-based from CyrusOne land acquisition. Reasonable, not certain."),
        ("Digital Realty Bersama → Digital Realty", "Folded the Indonesian JV into the parent record",
         "Treated a joint venture as part of the parent. Cross if you want JVs kept separate."),
        ("Lincoln Property Company → Lincoln", "Your real-estate sheet's \"Lincoln Property Company\" matched the existing \"Lincoln\" record", "Name match only."),
        ("Mapletree → Mapletree Industrial", "Your sheet's \"Mapletree\" matched the existing \"Mapletree Industrial\" record", "Parent vs listed industrial trust; may be two entities."),
        ("Duke Realty and DCT Industrial → Prologis", "Both folded into Prologis, which acquired them", "Acquired entities merged into the buyer rather than kept as history."),
        ("CRG → Clayco", "CRG folded into Clayco as its development arm", "They operate under one group but market separately."),
        ("TPA Group → TPA", "Two records merged", "Assumed the developer-list TPA and the core-list TPA are the same firm."),
        ("Affinius Capital ← USAA Real Estate", "Merged as one firm after the rename", "USAA Real Estate rebranded to Affinius; merged on that basis."),
        ("IDI Logistics ← IDR", "Merged as one firm", "IDR (Industrial Developments International) is IDI's former name."),
        ("Amazon → AWS", "\"Amazon\" career mentions now count as AWS", "Retail Amazon roles will be counted as AWS in talent flows."),
        ("Dominion → Dominion Energy", "Alias added so dump profiles resolve", "The parent utility and our record treated as one."),
        ("Avangrid / TotalEnergies / TransAlta / Tenaska → their renewables arms", "Parent names aliased to the renewables-arm records", "Parent and arm treated as one company for people and deals."),
    ]
    for item, claim, why in JUDGEMENT:
        add(2, "Merge or match I judged", item, claim, why + " Tick to keep, cross to split back out.", "")

    # ---- 4. the 7,110 directory profiles, as one decision ----
    add(3, "Bulk import decision", "7,110 directory profiles from the people export",
        "Added at companies already tracked; title and employer only, no career history or location, unverified against Clockwork. Badged \"directory\" in the atlas.",
        "They deepen org charts but were never checked. Tick to keep them, cross and I will remove them or restrict them to Director level and above.", "")
    add(4, "Bulk import decision", "5,905 profiles left out",
        "Their employers are not in the brain: utilities (PG&E, Xcel, SCE, Oncor), consultancies (Linesight, HDR, Atwell, Bowman), brokerages (JLL, CBRE, Cushman).",
        "Tick to leave them out, cross if you want those employers added as companies so the people come in.", "")

    # ---- 5. derived classifications worth a sanity check ----
    add(4, "Derived rule", "Department assigned from job title",
        "Every person's department is derived from their title by keyword (Development & Real Estate 576, Pre-Con & Cost 547, Sales & Leasing 365, Construction & Delivery 299, Energy & Utilities 198 …); generic titles fall back to the Clockwork mapping list.",
        "A rule, not a per-person judgement. Tick if the split looks right in the org charts.", "")
    add(4, "Derived rule", "Seniority assigned from job title",
        "Clockwork's own level is used where it exists (478 people); the rest are derived from the title into C-suite / EVP-SVP-MD / VP-Head / Director / Manager-Lead / IC.",
        "Same caveat. \"Most senior\" in an org chart means most senior among people we have mapped.", "")
    add(4, "Derived rule", "Pure-play vs needs-vetting (parent_industry)",
        f"682 companies are marked pure-play; 250 construction/engineering, 159 energy, 105 real estate, 6 conglomerate, 2 telecom.",
        "Drives the solid vs faded nodes and your direct-tap pool. Mostly inferred from the source list, not researched per company.", "")

    order = {1: "1 · Doubtful — check first", 2: "2 · Needs your judgement", 3: "3 · Partly supported",
             4: "4 · Single source or a rule", 6: "6 · Well sourced — spot-check"}
    rows.sort(key=lambda r: (r["Priority"], r["What to check"], r["Item"]))

    wb = Workbook(); ws = wb.active; ws.title = "Validation"
    COLS = ["#", "Verdict", "Notes from you", "Band", "What to check", "Item", "The claim as recorded", "Why it is on this list", "Sources"]
    ws.append(COLS)
    head = Font(name=FONT, bold=True, color="FFFFFF", size=11)
    for c in ws[1]:
        c.font = head; c.fill = PatternFill("solid", fgColor="0B3D5C"); c.alignment = Alignment(vertical="center", wrap_text=True)
    BAND_FILL = {1: "FBE3E3", 2: "FDF0DC", 3: "FDF8DC", 4: "EEF4F8", 6: "FFFFFF"}
    thin = Side(style="thin", color="D9D9D9")
    for i, r in enumerate(rows, start=1):
        ws.append([i, "", "", order[r["Priority"]], r["What to check"], r["Item"], r["The claim as recorded"], r["Why it is on this list"], r["Sources"]])
        row = ws.max_row
        fill = PatternFill("solid", fgColor=BAND_FILL[r["Priority"]])
        for j in range(1, len(COLS) + 1):
            cell = ws.cell(row=row, column=j)
            cell.font = Font(name=FONT, size=10)
            cell.alignment = Alignment(wrap_text=(j in (7, 8, 9)), vertical="top")
            cell.border = Border(bottom=thin)
            if j != 2: cell.fill = fill
        v = ws.cell(row=row, column=2)
        v.fill = PatternFill("solid", fgColor="FFF9C4"); v.alignment = Alignment(horizontal="center", vertical="center")
        v.font = Font(name=FONT, size=13)

    dv = DataValidation(type="list", formula1='"✅,❎,❓"', allow_blank=True, showDropDown=False)
    dv.prompt = "✅ correct · ❎ wrong or remove · ❓ needs a proper look"; dv.promptTitle = "Verdict"
    ws.add_data_validation(dv); dv.add(f"B2:B{ws.max_row}")
    widths = [5, 9, 26, 24, 24, 34, 62, 52, 46]
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "D2"; ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{ws.max_row}"
    ws.row_dimensions[1].height = 30
    ws["B1"].comment = Comment("Pick ✅, ❎ or ❓ from the dropdown. Filter column D to work one band at a time.", "Claude")

    # ---- summary sheet with live formulas ----
    s2 = wb.create_sheet("Progress", 0)
    s2["A1"] = "Validation progress"; s2["A1"].font = Font(name=FONT, bold=True, size=14)
    s2["A3"] = "Band"; s2["B3"] = "Rows"; s2["C3"] = "✅"; s2["D3"] = "❎"; s2["E3"] = "❓"; s2["F3"] = "Left to do"
    for c in s2[3]: c.font = Font(name=FONT, bold=True); c.fill = PatternFill("solid", fgColor="D9E6EF")
    bands = [order[k] for k in (1, 2, 3, 4, 6)]
    n = ws.max_row
    for i, b in enumerate(bands, start=4):
        s2[f"A{i}"] = b
        s2[f"B{i}"] = f'=COUNTIF(Validation!$D$2:$D${n},$A{i})'
        s2[f"C{i}"] = f'=COUNTIFS(Validation!$D$2:$D${n},$A{i},Validation!$B$2:$B${n},"✅")'
        s2[f"D{i}"] = f'=COUNTIFS(Validation!$D$2:$D${n},$A{i},Validation!$B$2:$B${n},"❎")'
        s2[f"E{i}"] = f'=COUNTIFS(Validation!$D$2:$D${n},$A{i},Validation!$B$2:$B${n},"❓")'
        s2[f"F{i}"] = f'=$B{i}-$C{i}-$D{i}-$E{i}'
    tot = 4 + len(bands)
    s2[f"A{tot}"] = "Total"; s2[f"A{tot}"].font = Font(name=FONT, bold=True)
    for col in "BCDEF":
        s2[f"{col}{tot}"] = f'=SUM({col}4:{col}{tot-1})'; s2[f"{col}{tot}"].font = Font(name=FONT, bold=True)
    notes = [
        "", "How to use this sheet",
        "1. Open the Validation tab and put ✅, ❎ or ❓ in the yellow Verdict column. ✅ = correct, ❎ = wrong or remove it, ❓ = needs a proper look.",
        "2. Filter column D to take one band at a time. Band 1 is the doubtful handful; band 6 is well-sourced and only needs spot-checks.",
        "3. Add anything useful in Notes from you — a correct figure, the real counterparty, a date.",
        "4. Send the file back. ✅ rows are recorded as checked by Siddhi and stop being questioned; ❎ rows I correct or remove; ❓ rows go into the next research round.",
        "",
        "What is NOT in here: anything you typed yourself (your five company lists) and anything from Clockwork. Only research findings and my own judgement calls are listed.",
        "Sources were returned by web searches and could not all be opened from the sandbox, so a link means the page was cited as naming the deal, not that it was read end to end.",
    ]
    for i, line in enumerate(notes, start=tot + 2):
        s2[f"A{i}"] = line
        s2[f"A{i}"].font = Font(name=FONT, bold=(line == "How to use this sheet"), size=11)
    s2.column_dimensions["A"].width = 118
    for col, w in zip("BCDEF", [10, 8, 8, 8, 12]): s2.column_dimensions[col].width = w
    for row in s2.iter_rows():
        for c in row:
            if c.font.name != FONT: c.font = Font(name=FONT, size=11)

    wb.save(OUT)
    print("rows:", len(rows))
    print(collections.Counter(order[r["Priority"]] for r in rows))
    print("saved", OUT)


if __name__ == "__main__":
    main()
