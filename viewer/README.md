# Graph Viewer

This folder holds the source behind the published "Data Center Atlas" —
the interactive visual graph of everything in `data/`.

## Structure

The graph is a **radial tree**, not a free-floating network:

```
Data Center Companies (root)
 ├─ each classified data-center company
 │   ├─ Sales / Pre-Construction / Development / Construction /
 │   │  Energy & Utilities (whichever it actually has people in)
 │   └─ investor, if one backs that company (e.g. Oaktree → Pure Data Centers)
 └─ Contractors & Consultants (aggregate branch, hidden by default)
     ├─ Sales / Pre-Construction / Development / ...
```

People are grouped by their **actual current employer**, not by which
recruiting search brought them into Clockwork. A company only gets its
own branch if it's a genuine data center **operator, developer,
hyperscaler, or neocloud/AI-infra company** (cryptomining-to-datacenter
pivots like TeraWulf, Core Scientific, Hut 8 and IREN count too) —
general contractors, cost consultants, engineering firms, and diversified
real estate/logistics developers (e.g. DPR Construction, Turner &
Townsend, Mortenson, Goodman, Segro) are grouped into one "Contractors &
Consultants" branch instead, split the same way by department, and their
individual profiles are **not** kept in `data/people/` at all if their
employer doesn't qualify.

Classification started from Clockwork's per-candidate "Organisation
Experience" tag, but that tag alone is too noisy to trust on presence
alone — one mistagged candidate at a 100+-person consultancy like Turner
& Townsend was enough to wrongly promote the whole company. The working
rule is now: a company only qualifies if a real majority of its people
carry a genuine "Data Center Developer," "Hyperscaler," or "Neo
Clouds/AI Infra" tag (roughly ≥50%, cross-checked against which of these
companies are actually recognizable operators/developers/hyperscalers/
neoclouds) — not "at least one candidate somewhere carries it." Revisit
this by hand if it misclassifies a company you know isn't right;
`viewer/README.md` (this section) records the reasoning so the next
pass doesn't have to redo it. Companies with zero current people (Pure
Data Centers is one) still get a branch as long as they have a
`data/companies/*.json` record.

**Department** in the tree is one of five: Sales, Pre-Construction,
Development, Construction, or Energy & Utilities — mostly derived from
which Long Term Mapping list or active search sourced a candidate, with
one skill-tag override (an energy-negotiation/engineering tag moves
someone into Energy & Utilities regardless of source list).
`viewer/build_graph_data.py`'s `DEPARTMENT_ORDER` controls display
order — a new department name beyond it still renders, just appended at
the end, and needs a color added to `DEPT_PALETTE` in
`atlas_template.html` to get its own hue instead of the neutral
fallback.

## Files

- **`build_graph_data.py`** — reads every file in `data/companies/`,
  `data/people/`, and `data/investors/`, and builds the nested tree above
  as `tree_data.json`. A person lands under their `current_company_id`
  (set on the person record) and `department` field; anyone without a
  qualifying `current_company_id` falls into the aggregate branch.
- **`atlas_template.html`** — the page itself (dark "blueprint" themed
  radial tree, built with D3.js — `d3.hierarchy` + `d3.tree` in radial
  mode, drawn on canvas). It has a placeholder, `__TREE_DATA_JSON__`,
  where the real data gets inserted.

## How it's published

You never need to run these yourself — when you ask to refresh the visual
graph after adding new data, this is what happens:

1. `build_graph_data.py` regenerates `tree_data.json` from the current
   contents of `data/`.
2. That JSON is inserted into `atlas_template.html` in place of
   `__TREE_DATA_JSON__`, producing a complete, self-contained HTML page.
3. The page is published as an Artifact (a private web page) and the link
   is shared with you, updating the same URL each time.

Because the page embeds a snapshot of the data at build time, it needs to
be regenerated and republished any time you want the graph to reflect new
additions to `data/` — just ask.

## 3D prototype (companies + investors only)

There is a second, experimental 3D viewer, deliberately scoped down while
we get the visual design right: it drops the people layer entirely and
shows only the 185 data-center companies and 79 private-equity/investor
backers, spread out in true 3D space (a small custom force-directed
layout, not a stacked tree) and clustered + colored by tier — Hyperscaler,
NeoCloud/AI Infra, Data Center Developer/Operator, Cryptomining (reserved,
currently empty) — with Investors as their own cluster, connected by a
line to every company they've backed.

- **`build_graph3d_data.py`** — reads `data/companies/` and
  `data/investors/`, classifies each company into one of the four tiers
  by its `tags` (priority: NeoCloud/AI Infra tag first, then Hyperscaler,
  then any crypto-mining tag, else Developer/Operator), and writes a flat
  `graph3d_data.json` of `{categories, nodes, links}` — not a tree, since
  an investor can back more than one company.
- The 3D page itself (built the same way — data inserted into an HTML
  template, published as a separate Artifact) uses Three.js instead of
  D3/canvas, so you can orbit, zoom, and click a node in true 3D.

This is a step back in scope on purpose, at your request, so the company
+ investor layer reads cleanly before people are added back in.
