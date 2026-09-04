# Graph Viewer

This folder holds the source behind the published "Data Center Atlas" —
the interactive visual graph of everything in `data/`.

- **`build_graph_data.py`** — reads every file in `data/companies/`,
  `data/people/`, `data/investors/`, and `data/relationships.json`, and
  turns them into one `graph_data.json` blob shaped for the viewer
  (nodes + links).
- **`atlas_template.html`** — the page itself (dark "blueprint" themed
  interactive node graph, built with D3.js). It has a placeholder,
  `__GRAPH_DATA_JSON__`, where the real data gets inserted.

## How it's published

You never need to run these yourself — when you ask to refresh the visual
graph after adding new data, this is what happens:

1. `build_graph_data.py` regenerates `graph_data.json` from the current
   contents of `data/`.
2. That JSON is inserted into `atlas_template.html` in place of
   `__GRAPH_DATA_JSON__`, producing a complete, self-contained HTML page.
3. The page is published as an Artifact (a private web page) and the link
   is shared with you.

Because the page embeds a snapshot of the data at build time, it needs to
be regenerated and republished any time you want the graph to reflect new
additions to `data/` — just ask.
