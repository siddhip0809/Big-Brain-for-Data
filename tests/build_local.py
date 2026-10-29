#!/usr/bin/env python3
"""Build tests/.build/atlas.html: the page with this repo's data, Three.js r128 vendored
locally (the CDN is not reachable from the sandbox) and its internals exposed as
window.__T for the Playwright tests. Run viewer/build_graph3d_data.py first.

Three.js comes from `npm pack three@0.128.0` the first time, cached in tests/.build.
Never run `playwright install`; Chromium lives at /opt/pw-browsers/chromium.
"""
import os, re, shutil, subprocess, tarfile

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, ".build")


def vendor():
    lib = os.path.join(OUT, "three128")
    if os.path.exists(os.path.join(lib, "three.min.js")): return
    os.makedirs(lib, exist_ok=True)
    subprocess.run(["npm", "pack", "three@0.128.0", "--silent"], cwd=OUT, check=True, capture_output=True)
    with tarfile.open(os.path.join(OUT, "three-0.128.0.tgz")) as t:
        for m in t.getmembers():
            if m.name == "package/build/three.min.js" or re.match(r"package/examples/js/(lines|controls)/[A-Za-z0-9]+\.js$", m.name):
                m.name = os.path.basename(m.name); t.extract(m, lib)


def main():
    os.makedirs(OUT, exist_ok=True); vendor()
    html = open(f"{REPO}/viewer/atlas3d_template.html").read().replace(
        "__GRAPH_DATA_JSON__", open(f"{REPO}/viewer/graph3d_data.json").read())
    html = re.sub(r"https://cdn\.jsdelivr\.net/npm/three@0\.128\.0/(?:build|examples/js/[a-z]+)/([A-Za-z0-9.]+\.js)", r"three128/\1", html)
    hook = ("  window.__T = { GRAPH, SEARCHES, PEOPLE, NOTES, nodeById, nodeVisible, baseVisible, selectNode, openOrg, ORG_TREE,\n"
            "                 renderSearches, get selectedNode(){ return selectedNode; } };\n")
    i = html.rindex("})();"); html = html[:i] + hook + html[i:]
    open(os.path.join(OUT, "atlas.html"), "w").write(html)
    print("wrote", os.path.join(OUT, "atlas.html"))


if __name__ == "__main__":
    main()
