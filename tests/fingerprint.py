#!/usr/bin/env python3
"""Capture what the atlas renders -- visible-node counts under each filter, and the text of
the detail panel, org chart (every mode), searches, flows and notes panels for a fixed set
of nodes -- as one JSON file. Run it before and after a refactor of the page or builder
and diff the two: identical output means identical behaviour.

    python3 tests/fingerprint.py out.json          # uses tests/.build/atlas.html

Long strings are written as a length and a hash; out.json.full holds the text itself, so a
difference can be read. Keep both outside the repo: the text includes people's names.
"""
import asyncio, hashlib, json, sys
from harness import atlas

NODES = ["equinix", "stack-infrastructure", "google", "aecom", "panattoni", "avk", "investor:blackstone", "turner-townsend", "crusoe"]
JS_VIS = "() => window.__T.GRAPH.nodes.filter(n => window.__T.nodeVisible(n)).length"


async def main():
    out = {}
    async with atlas() as pg:
        txt = lambda sel: pg.evaluate(f"(document.querySelector('{sel}') || {{}}).textContent || ''")
        async def click(sel, ms=700): await pg.click(sel); await pg.wait_for_timeout(ms)
        out["stats"] = await txt("#statsGrid"); out["header"] = [await txt("#statNodes"), await txt("#statLinks")]
        out["legend"] = await txt("#legend"); out["edge_legend"] = await txt("#edgeLegend")
        out["vis_default"] = await pg.evaluate(JS_VIS); out["iso_count"] = await txt("#isoCount")
        out["link_types"] = await pg.evaluate("() => { const c = {}; window.__T.GRAPH.links.forEach(l => { const k = l.type + '/' + l.style; c[k] = (c[k] || 0) + 1; }); return c; }")
        for n in NODES:                                   # detail panel + org chart in every mode
            ok = await pg.evaluate(f"(() => {{ const n = window.__T.nodeById['{n}']; if(!n) return false; window.__T.selectNode(n); return true; }})()")
            if not ok: out[f"detail:{n}"] = None; continue
            await pg.wait_for_timeout(150)
            out[f"detail:{n}"] = await txt("#detailBody")
            if await pg.evaluate("!!document.getElementById('openOrg')"):
                await click("#openOrg", 500)
                for mode in await pg.evaluate("[...document.querySelectorAll('#orgMode button')].map(b => b.dataset.mode)"):
                    await click(f"#orgMode button[data-mode='{mode}']", 350)
                    out[f"org:{n}:{mode}"] = (await txt("#orgLead")) + "|" + (await txt("#orgBody"))
                await pg.fill("#orgFilter", "director"); await pg.wait_for_timeout(300)
                out[f"org:{n}:filter"] = await txt("#orgBody")
                await click("#orgClose", 200)
        await click("#detailClose", 200)
        await click("#srchBtn", 400)                      # searches panel
        for st in await pg.evaluate("[...document.querySelectorAll('#srchStatus button')].map(b => b.dataset.st)"):
            await click(f"#srchStatus button[data-st='{st}']", 250)
            out[f"searches:{st or 'all'}"] = (await txt("#srchSub")) + "|" + (await txt("#srchBody"))
        await click("#srchClose", 200)
        await click("#flowsBtn", 500)                     # flows matrix
        for view in ("tier", "fn"):
            await click(f"#flowsView button[data-view='{view}']", 300)
            for scope in ("all", "core", "in"):
                await click(f"#flowsScope button[data-scope='{scope}']", 300)
                out[f"flows:{view}:{scope}"] = (await txt("#flowsSub")) + "|" + (await txt("#flowsBody"))
            await click("#flowsBody td[data-k]", 300)     # a cell opens the people behind the number
            out[f"flows:{view}:cell"] = await txt("#flowsBody")
            await click("#flowsBody td.sel", 300)
        await click("#flowsClose", 200)
        await click("#notesBtn", 500); out["notes"] = (await txt("#notesSub")) + "|" + (await txt("#notesBody")); await click("#notesClose", 200)
        await pg.fill("#searchInput", "stack"); await pg.wait_for_timeout(400); out["search:stack"] = await txt("#searchResults")
        await pg.fill("#searchInput", ""); await pg.wait_for_timeout(200)
        steps = [("#adjacentSwitch", 2000, "adjacent_on"), ('#isoMode button[data-mode="show"]', 2500, "iso_show"),
                 ('#isoMode button[data-mode="apart"]', 2000, "iso_apart"), ('#isoMode button[data-mode="hide"]', 1500, "iso_hide"),
                 ("#adjacentSwitch", 1500, "adjacent_off"), (".mini-toggle[data-line='talent_flow']", 1500, "flows_on"),
                 ('#flowMode button[data-mode="dept"]', 1500, "flows_dept"), ('#flowMode button[data-mode="tier"]', 1200, "flows_tier"),
                 (".mini-toggle[data-line='talent_flow']", 1200, "flows_off"), ('#wardOnly button[data-on="1"]', 1200, "clients_only"),
                 ('#wardOnly button[data-on="2"]', 1200, "projects_on_file"), ('#wardOnly button[data-on="0"]', 1200, "all_companies"),
                 ('#isoMode button[data-mode="hide"]', 1500, "back_to_default"), ("#themeBtn", 1000, "dark"), ("#themeBtn", 1000, "light")]
        for sel, ms, name in steps:
            await click(sel, ms)
            out[f"vis:{name}"] = [await pg.evaluate(JS_VIS), await txt("#isoCount"), await pg.evaluate("document.querySelectorAll('.label3d:not(.zone-cap)').length")]
        out["edge_legend_after"] = await txt("#edgeLegend")
        # navigation between panels: a company's searches, then a mover's card to their company on the map
        await pg.evaluate("window.__T.selectNode(window.__T.nodeById['stack-infrastructure'])"); await pg.wait_for_timeout(200)
        await click("#openSearches", 400)
        out["nav:searches_for"] = [await pg.evaluate("document.getElementById('srchFilter').value"), await txt("#srchSub"),
                                   await pg.evaluate("[...document.querySelectorAll('#srchStatus button.on')].map(b => b.dataset.st)")]
        await click("#srchBody .srch-client[data-company]", 1500)
        out["nav:search_client"] = [await pg.evaluate("window.__T.selectedNode && window.__T.selectedNode.id"), await pg.evaluate("document.getElementById('searches').hidden")]
        await click("#flowsBtn", 500); await click("#flowsBody td[data-k]", 300); await click("#flowsBody .pcard[data-company]", 1500)
        out["nav:flows_card"] = [await pg.evaluate("window.__T.selectedNode && window.__T.selectedNode.id"), await pg.evaluate("document.getElementById('flows').hidden"),
                                 await pg.evaluate(JS_VIS)]
        out["page_errors"] = pg.errors
    # whitespace between tags is layout, not content: collapse it so re-indented markup compares equal
    out = {k: (" ".join(v.split()) if isinstance(v, str) else v) for k, v in out.items()}
    json.dump({k: (v if not isinstance(v, str) or len(v) < 200 else f"{len(v)} chars sha1 {hashlib.sha1(v.encode()).hexdigest()[:12]}") for k, v in out.items()},
              open(sys.argv[1], "w"), indent=1, ensure_ascii=False, sort_keys=True)
    json.dump(out, open(sys.argv[1] + ".full", "w"), indent=1, ensure_ascii=False, sort_keys=True)   # the text itself, for reading a difference
    print(len(out), "captures ->", sys.argv[1], "| page errors:", pg.errors)

if __name__ == "__main__":
    asyncio.run(main())
