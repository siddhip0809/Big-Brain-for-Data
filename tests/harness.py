"""Shared Playwright setup: open tests/.build/atlas.html with fonts blocked (they are
render-blocking and unreachable here) and collect page errors. See CLAUDE.md, Testing."""
import os
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".build", "atlas.html")


class Checks:
    def __init__(self): self.fails = []
    def __call__(self, name, ok, info=""):
        print(("ok   " if ok else "FAIL ") + name + (f"  {info}" if info else ""))
        if not ok: self.fails.append(name)
    def done(self):
        print("\n" + ("FAILURES: " + ", ".join(self.fails) if self.fails else "all checks pass"))
        return 1 if self.fails else 0


@asynccontextmanager
async def atlas():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium",
                                    args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": 1400, "height": 900}); pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        await pg.route("**fonts.googleapis.com**", lambda r: r.abort())
        await pg.goto("file://" + PAGE)
        await pg.wait_for_function('window.__T && document.querySelectorAll(".label3d").length > 0', timeout=60000)
        await pg.wait_for_timeout(1500)
        try: yield pg
        finally: await b.close()
