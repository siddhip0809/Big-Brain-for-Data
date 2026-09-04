# Graph Viewer

This folder holds the source behind the published "Data Center Atlas" —
the interactive visual graph of everything in `data/`.

## Structure

The graph is a **radial tree**, not a free-floating network:

```
Data Center Companies (root)
 ├─ each classified data-center company
 │   ├─ Sales (people currently working there)
 │   ├─ Pre-Construction (people currently working there)
 │   ├─ Energy & Utilities (people currently working there)
 │   └─ investor, if one backs that company (e.g. Oaktree → Pure Data Centers)
 └─ Contractors & Consultants (aggregate branch, hidden by default)
     ├─ Sales
     └─ Pre-Construction
```

People are grouped by their **actual current employer**, not by which
recruiting search brought them into Clockwork. A company only gets its own
branch if at least one candidate's current-employer record carries
Clockwork's "Data Center Developer," "Hyperscaler," or "Real Estate
Development" organisation tag — everyone else (general contractors, cost
consultants, engineering firms — e.g. DPR Construction, Turner &
Townsend, Mortenson) is grouped into one "Contractors & Consultants"
branch instead, split the same way by department. That classification is
a blunt rule on noisy per-candidate tag data, not researched
company-by-company — worth revisiting if it misclassifies someone you
know isn't right. A handful of companies (Pure Data Centers, Prologis,
Trammell Crow Company) were added by hand rather than derived from
Clockwork data, and show up with zero people until real candidates there
are added.

**Department**, in the tree, means "Sales," "Pre-Construction," or
"Energy & Utilities" — derived from which recruiting search sourced a
candidate (Sales-search vs. Development-search) and, within the
Development-search pool, whether they carry an energy-negotiation or
energy-engineering skill tag from Clockwork (currently 3 people, all at
Google). `viewer/build_graph_data.py`'s `DEPARTMENT_ORDER` controls
display order — new department names beyond it still render, just
appended at the end, and need a color added to `DEPT_PALETTE` in
`atlas_template.html` to get their own hue instead of the neutral
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
