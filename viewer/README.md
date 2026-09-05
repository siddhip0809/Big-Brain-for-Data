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
shows only the data-center companies and private-equity/investor backers,
spread out in true 3D space via a small custom force-directed layout (not
a stacked tree) and clustered + colored by tier — Hyperscaler, NeoCloud/AI
Infra, Data Center Developer/Operator, Cryptomining (US Bitcoin miners
that have pivoted into AI/HPC data center hosting, like TeraWulf, Hut 8,
Cipher Mining, and Bitfarms/Keel Infrastructure) — with Investors as
their own cluster, connected by a line to every company they've backed.

- **`build_graph3d_data.py`** — reads `data/companies/` and
  `data/investors/` and writes a flat `graph3d_data.json` of
  `{categories, parent_industry_meta, nodes, links}` (not a tree, since
  an investor can back more than one company). Two explicit allowlists
  decide tier (`TRUE_HYPERSCALER_IDS`, `TRUE_NEOCLOUD_IDS`) rather than
  trusting the CRM's "Hyperscaler"/"Neo Clouds/AI Infra" tags directly —
  both tags turned out to mean "this company's people have worked on
  X-related projects," not "this company IS an X," and were firing on
  dozens of companies that are really just data center developers/
  operators. Each company also carries a `parent_industry` (`pure_play`,
  `real_estate`, `energy_utilities`, `telecom`, `construction_engineering`,
  or `diversified_conglomerate`) saying whether data centers are the
  company's own dedicated business or one arm of a bigger one.
- **`atlas3d_template.html`** — the 3D page itself (data inserted in
  place of `__GRAPH_DATA_JSON__`, same pattern as `atlas_template.html`),
  built with Three.js instead of D3/canvas so you can orbit, zoom, and
  click a node in true 3D.

**Node interaction — "focus mode":** clicking a node doesn't just open the
text detail panel — it zooms the camera in, arranges that node's direct
connections (an investor's whole portfolio, or a company's backers) into
a clean ring around it, and fades everything else in the graph nearly
out of view. Click one of the ring nodes to drill one level deeper (it
recenters and reveals *its* connections); a "← Back" / "Show full graph"
control pair (top-left of the stage) steps back out. This replaces a
static text card with a spatial, explorable "atomic diagram" of each
node's neighborhood, per Siddhi's request.

This is a step back in scope on purpose, at your request, so the company
+ investor layer reads cleanly before people are added back in.
