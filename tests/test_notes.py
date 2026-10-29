#!/usr/bin/env python3
"""The notes layer in the atlas: sidebar count, panel, filters, in-confidence and
judgement labels, company section, person card, links and Escape. It picks its company
and person from whatever notes exist (no names here: this file goes to GitHub) and
skips cleanly when there are none."""
import asyncio, sys
from harness import atlas, Checks


async def main():
    check = Checks()
    async with atlas() as pg:
        if not await pg.evaluate("window.__T.NOTES.length"):
            print("no notes in data/notes/ -- nothing to test"); return 0
        n = await pg.evaluate('window.__T.NOTES.length')
        check('sidebar shows the note count', (await pg.inner_text('#notesCount')).strip() == str(n), f'{n}')
        await pg.click('#notesBtn'); await pg.wait_for_timeout(600)
        cards = await pg.evaluate("document.querySelectorAll('#notesBody .pipeline-entry').length")
        check('panel lists every note', cards == n, f'{cards} cards for {n} notes')
        check('note box is drawn', await pg.evaluate("!!document.getElementById('nfText')"))
        check('in-confidence tag shown', await pg.evaluate("document.querySelectorAll('#notesBody .pill.dnc').length") > 0)
        check('judgement labelled', 'not a reported fact' in await pg.inner_text('#notesBody'))
        await pg.click('#notesKind button[data-k="signal"]'); await pg.wait_for_timeout(300)
        sig = await pg.evaluate("document.querySelectorAll('#notesBody .pipeline-entry').length")
        want = await pg.evaluate("window.__T.NOTES.filter(x => (x.signals||[]).length).length")
        check('signals filter', sig == want, f'{sig} vs {want}')
        cid = await pg.evaluate("(window.__T.NOTES.flatMap(x => x.about || []).find(r => window.__T.nodeById[r] && window.__T.nodeById[r].kind === 'company')) || ''")
        cname = await pg.evaluate(f"(window.__T.nodeById['{cid}'] || {{}}).name || ''")
        await pg.click('#notesKind button[data-k=""]'); await pg.fill('#notesFilter', cname); await pg.wait_for_timeout(300)
        pan = await pg.evaluate("document.querySelectorAll('#notesBody .pipeline-entry').length")
        check('text filter narrows', 0 < pan <= n, f'{pan}')
        await pg.fill('#notesFilter', ''); await pg.wait_for_timeout(200)
        await pg.click(f"#notesBody .note-link[data-ref='{cid}'] >> nth=0"); await pg.wait_for_timeout(2500)
        check('company link closes the panel', await pg.evaluate("document.getElementById('notes').hidden"))
        body = await pg.evaluate("document.getElementById('detailBody').textContent")
        sel = await pg.evaluate("(window.__T.selectedNode || {}).id")
        check('company panel shows what we heard', 'What we’ve heard' in body, f'selected={sel}')
        await pg.click('#notesBtn'); await pg.wait_for_timeout(400)
        pid = await pg.evaluate("(Object.values(window.__T.PEOPLE).flat().find(p => window.__T.NOTES.some(x => (x.about||[]).includes(p.id))) || {}).id || ''")
        await pg.click(f"#notesBody .note-link[data-ref='{pid}'] >> nth=0"); await pg.wait_for_timeout(1500)
        check('person link opens the org chart', not await pg.evaluate("document.getElementById('org').hidden"))
        card = await pg.evaluate(f"(document.querySelector('.pcard[data-pid=\"{pid}\"]') || {{}}).textContent || ''")
        check('person card carries the heard pill and notes', 'heard' in card and 'What we’ve heard' in card, card[:120].replace('\n', ' / '))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        await pg.click('#notesBtn'); await pg.wait_for_timeout(300); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        check('Escape closes the notes panel', await pg.evaluate("document.getElementById('notes').hidden"))
        check("no page errors", not pg.errors, str(pg.errors)[:300])
    return check.done()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
