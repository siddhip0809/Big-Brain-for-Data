#!/usr/bin/env python3
"""Every toggle flips exactly once per click, also after the edge legend has been
re-rendered (theme switch, flow mode), and toggling back restores the same graph.
Guards the 2026-09-16 bug where a listener bound inside renderEdgeLegend() stacked
one handler per re-render and a line toggle cancelled itself."""
import asyncio, sys
from harness import atlas, Checks

VIS = "() => window.__T.GRAPH.nodes.filter(n => window.__T.nodeVisible(n)).length"
STATE = "(t) => document.querySelector(`.mini-toggle[data-line='${t}']`).textContent"


async def main():
    check = Checks()
    async with atlas() as pg:
        base = await pg.evaluate(VIS)
        async def click(sel, ms=1200): await pg.click(sel); await pg.wait_for_timeout(ms)
        await click("#themeBtn")                                     # one legend re-render
        await click(".mini-toggle[data-line='invested_in']")
        check("line toggle flips once after the legend re-renders", await pg.evaluate(STATE, "invested_in") == "off")
        check("switching investor lines off changes the connected set", await pg.evaluate(VIS) != base)
        await click(".mini-toggle[data-line='invested_in']")
        check("toggling back restores the graph", await pg.evaluate(STATE, "invested_in") == "on" and await pg.evaluate(VIS) == base)
        await click("#themeBtn")
        await click('#flowMode button[data-mode="dept"]', 1000); await click('#flowMode button[data-mode="tier"]', 1000)
        await click(".mini-toggle[data-line='talent_flow']", 1000)  # dept mode switched flows on; back to default
        await click(".mini-toggle[data-line='tenant_of']")
        check("a line still flips once after four re-renders", await pg.evaluate(STATE, "tenant_of") == "off")
        await click(".mini-toggle[data-line='tenant_of']")
        check("graph back to baseline", await pg.evaluate(VIS) == base)
        await click("#linesNone", 1000)
        check("all off", await pg.evaluate("[...document.querySelectorAll('.mini-toggle[data-line]')].every(b => b.textContent === 'off')"))
        await click("#linesAll", 1000)
        check("all on", await pg.evaluate("[...document.querySelectorAll('.mini-toggle[data-line]')].every(b => b.textContent === 'on')"))
        await click(".mini-toggle[data-line='talent_flow']", 1000)
        await click("#adjacentSwitch", 2500); n = await pg.evaluate(VIS)
        check("adjacent petals on adds nodes", n > base, f"{base}->{n}")
        await click("#adjacentSwitch", 1500)
        check("adjacent petals off restores the graph", await pg.evaluate(VIS) == base)
        await click(".legend-row[data-cat='neocloud']"); n = await pg.evaluate(VIS)
        check("a tier row hides its tier", n < base, f"{base}->{n}")
        await click(".legend-row[data-cat='neocloud']")
        check("the tier row restores it", await pg.evaluate(VIS) == base)
        await click('#isoMode button[data-mode="show"]', 2500)
        check("show unconnected adds nodes", await pg.evaluate(VIS) > base)
        await click('#isoMode button[data-mode="hide"]', 1500)
        check("hide unconnected restores the graph", await pg.evaluate(VIS) == base)
        await click('#wardOnly button[data-on="1"]'); n = await pg.evaluate(VIS)
        check("clients only narrows the map", 0 < n < base, f"{n}")
        await click('#wardOnly button[data-on="0"]'); await click('#isoMode button[data-mode="hide"]', 1500)
        check("clients filter off restores the graph", await pg.evaluate(VIS) == base)
        check("no page errors", not pg.errors, str(pg.errors)[:300])
    return check.done()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
