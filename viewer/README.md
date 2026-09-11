# Graph Viewer

The source behind the published "Data Center Atlas" — the interactive visual
graph of everything in `data/`.

- **`build_graph3d_data.py`** — reads `data/` and writes `graph3d_data.json`
  (gitignored; a build product).
- **`atlas3d_template.html`** — the page itself. `__GRAPH_DATA_JSON__` is
  replaced with that JSON at publish time, producing one self-contained file
  that is published as a private Artifact at the same URL each time.

See `../CLAUDE.md` for the build order and the conventions.

An earlier 2D radial-tree viewer (`build_graph_data.py` + `atlas_template.html`)
was removed on 2026-09-10: it had been superseded by the 3D atlas and the
per-company org charts, nothing referenced it, and its output path no longer
existed. It is in git history if it is ever wanted back.

## How the 3D atlas works

There is a second, experimental 3D viewer, deliberately scoped down while
we get the visual design right: it drops the people layer entirely and
shows only the data-center companies and private-equity/investor backers,
spread out in true 3D space via a small custom force-directed layout (not
a stacked tree). Companies loosely cluster and are colored by tier —
Hyperscaler, NeoCloud/AI Infra, Data Center Developer/Operator,
Cryptomining (US Bitcoin miners that have pivoted into AI/HPC data center
hosting, like TeraWulf, Hut 8, Cipher Mining, and Bitfarms/Keel
Infrastructure). Investors (violet) deliberately do NOT get a fixed
"home" position the way company tiers do — a company belongs to exactly
one tier, so anchoring it is coherent, but an investor can back companies
across every tier at once, so pinning it to one arbitrary point fights
its real connections instead of reflecting them. Each investor instead
sits wherever its actual backing pulls it (close to a single portfolio
company, or toward the middle if it backs a spread of them), plus a weak
data-driven "co-investment" pull toward other investors who've backed the
same company — real relational clustering, not an arbitrary same-color
rule. There are no visible category hub markers either (removed per
Siddhi's request, 2026-09-05) — tier is carried by node color alone, kept
legible via the sidebar legend.

- **`build_graph3d_data.py`** — reads `data/companies/` and
  `data/investors/` and writes a flat `graph3d_data.json` of
  `{categories, parent_industry_meta, nodes, links, stats}` (not a tree,
  since an investor can back more than one company). Tier comes from each
  record's `roles` list — the single source of truth since the 2026-09-05
  import of Siddhi's lists; the build refuses a record without one. Tier
  was never derived from the CRM's "Hyperscaler" / "Neo Clouds/AI Infra"
  tags, which turned out to mean "this company's people have worked on
  X-related projects," not "this company IS an X." Eight company roles exist — four
  data-center tiers (Hyperscaler, NeoCloud, Cryptomining pivot,
  Developer/Operator) and four **adjacent industries** (Energy developer,
  General contractor, Civil/land engineering, Industrial/cold-storage
  developer) that the atlas keeps **switched off by default**; a company
  holding several roles is drawn as a **banded sphere**, one horizontal
  colour stripe per role. The nine colours were validated together as a
  CVD-safe set on the dark surface. The adjacent industries are a
  **separate zone** of space (per Siddhi, 2026-09-08): companies whose
  roles are *all* adjacent get their anchors on a second, smaller sphere
  set to the right of the data-center core from the default camera angle,
  each zone carries a quiet floating caption, and the legend has a
  one-click "show all / hide all" switch for the whole group. A company
  with any data-center role (e.g. a developer that is also an energy
  developer) stays in the core; investors sit wherever their portfolio
  pulls them, so a backer of both groups stretches between the zones. The
  pure-play/"needs vetting" fade applies inside the core only — every
  adjacent company is non-pure-play by definition, so fading the whole
  zone would say nothing. The overview camera frames whichever zones are
  switched on. The two zones are connected by three relationship types
  (`contractor_for` sky blue, `supplies_power_to` red, `site_partner`
  pink, see `docs/schema.md`); those edges carry **no layout spring**, so
  the zones hold their shape and the line alone shows the link. Clicking
  a core company whose partners sit in the hidden zone shows a hint with
  a one-click "show it" that switches the zone on and re-focuses. Each company also carries a
  `parent_industry` (`pure_play`, `real_estate`, `energy_utilities`,
  `telecom`, `construction_engineering`, or `diversified_conglomerate`)
  saying whether data centers are its own dedicated business or one arm
  of a bigger one. Physics runs only over the nodes currently shown, and
  the overview camera refits itself to whatever is visible.
- **`atlas3d_template.html`** — the 3D page itself (data inserted in
  place of `__GRAPH_DATA_JSON__`, same pattern as `atlas_template.html`),
  built with Three.js instead of D3/canvas so you can orbit, zoom, and
  click a node in true 3D.

**Lines:** four relationship types are drawn, each its own colour (key in
the sidebar): violet = investor backing, white = lease/tenant, amber =
acquisition, green = joint venture. Since 2026-09-08 they are real
pixel-width "fat" lines (Three.js `LineSegments2`) and the **dash pattern
carries a second dimension within the colour**: for acquisitions, solid =
completed, dashed = announced/pending, dotted = terminated; for backing
and leases, solid = high-confidence (official or multi-source), dashed =
single-source, verify. The build sets `style` on every edge
(`line_style()` in `build_graph3d_data.py`). In focus mode the focused
node's own edges are redrawn thicker and brighter in the same colours and
patterns. Deal edges (`tenant_of`, `acquired`, `jv_partner`, see
`docs/schema.md`) use softer, longer springs than backing edges, so
related companies lean toward each other without being pulled out of
their tier.

**Node interaction — "focus mode":** clicking a node doesn't just open the
text detail panel — it zooms the camera in, arranges that node's direct
connections (backers, portfolio companies, tenants, landlords, acquirers,
JV partners) into a clean ring around it — centred in the part of the
stage the detail panel doesn't cover — and fades everything else in the
graph nearly out of view. The layout is frozen while focused so the ring
holds still. Click one of the ring nodes to drill one level deeper (it
recenters and reveals *its* connections); a "← Back" / "Show full graph"
control pair (top-left of the stage) steps back out. This replaces a
static text card with a spatial, explorable "atomic diagram" of each
node's neighborhood, per Siddhi's request.

**Calm view (2026-09-09, at Siddhi's request — the graph "looked scary").**
Three changes, all in the template:
- **Light theme by default**, the original dark "terminal" look behind a
  header toggle (remembered per browser). On the light ground the glow
  sprites are off, lease lines are slate instead of white, labels are dark
  with a white halo, and the grid is gone.
- **Progressive disclosure.** The atlas opens on the connected structure
  only (unconnected switch defaults to Hide, ~270 nodes instead of 865);
  node size follows weight (connections + people mapped); labels are
  ranked by weight and placed greedily with collision avoidance under a
  zoom-dependent budget (24 far out → 140 close in), so they never pile
  up; hovering a node lights up its neighbours and its own lines and dims
  everything else; the settled layout fades in instead of exploding.
- **Flower layout.** The data-center core is the centre; each adjacent
  industry is its own petal (energy, GC, civil, industrial) on a ring in
  the plane facing the default camera, at 45° offsets, so the four sit
  top-right / top-left / bottom-left / bottom-right around the core with a
  coloured caption each. Orbiting still works; the ring is only planar
  from the opening angle.

**Every line type has its own switch** (2026-09-09) in the Lines key, plus
"all on / all off". A type that is off is not drawn, does not count toward
"connected", and drops out of focus rings — so "only leases" or "only
power supply" are one click. Talent flow starts off; everything else on.

**Unconnected nodes.** 593 of the 865 default-view nodes have no line to
anything else shown (companies from Siddhi's lists with no researched
backer, tenant or deal yet). A three-way switch under the legend leaves
them in place (**Show**), fades and shrinks them and drifts them to an
outer shell around their zone (**Set apart**), or drops them from the
graph and re-runs the layout on what is left (**Hide**). "Unconnected" is
judged against the tiers currently switched on, so a core company whose
only partner sits in the hidden adjacent zone counts as unconnected until
that zone is shown; searching for a hidden node flips the switch back to
Show so it can be focused.

**Talent flows (2026-09-09).** Derived from career histories by
`scripts/build_talent_flows.py`: a move is a person's previous employer →
current employer. Every move is classified two ways: by **origin group**
(within the data-center core, from an adjacent industry, from an investor,
or from outside the industry — outside is bucketed by keyword into
brokerage & advisory, consultancy & engineering, telecom & network,
technology, untracked data-center operators, untracked utilities and
construction, finance, government & military, other) and by the exact
**tier-to-tier pair** (hyperscaler → developer, developer → neocloud …).
The sidebar's "Open tier-to-tier matrix" shows the whole matrix (rows =
previous tier, columns = current tier, scoped to all moves / within the
core / into the core); click a cell for the people and a card to focus
their company. Each company panel shows "Where from" (group split with
percentages) and "By tier"; the org chart has a "By previous industry"
grouping. Flow lines: solid = same tier, dashed = another tier in the same
group, dotted = across groups. The overview also has a **By function**
view (rows = the department people work in now, columns = where they came
from, with row percentages; click a cell for the people and their top
source employers) and a function filter that applies to the tier matrix
too — "where do energy & utilities people come from" is one selection.
`data/derived/talent_flow_by_function.csv` is the same table as data. Each company panel shows **Hires from** and **Alumni
now at** (top counts, untracked employers included by name) and how many
people started in the last six months; the org chart has a **By previous
employer** grouping and a green **new** badge; grey **talent-flow lines**
between tracked companies are off by default (toggle in the Lines key)
because they are a people signal, not a structural tie — they carry no
layout spring and, when on, count toward "connected".

**Ward's assessment layer (2026-09-09).** Person cards badge top-tier
functions, "spoken with before" and a "recent move" warning; expanding a
card shows assessed skills with high/low confidence, the 1-4 rating, the
tenure judgement, the hyperscaler-equivalent seniority, education and
biography, over a line saying it is Ward's judgement rather than research.
Slate diversity is reported as an aggregate — "18 of 105 assessed
recorded as from an under-represented group" — on each company panel and
in the org-chart header, with a discreet per-person marker and a line
noting it is Ward's observation rather than self-declared. The org chart
groups by **top tier** or **assessed skill** (a person can
appear under several), each company panel summarises how many of its
people are assessed and which high-confidence skills sit there, and the
filter matches skills, education and biography text.

**People — the org chart (added 2026-09-08).** People are deliberately
*not* drawn as nodes in the 3D view (that was what made the earlier full
graph unreadable). Instead they come back through each company: the
company detail panel lists "People in the brain (N)" by department with
the most senior mapped person in each, and "Open org chart →" opens a
full-stage overlay for that company:

- **Leadership mapped** — a row of everyone at C-suite or EVP/SVP/MD rank,
  i.e. "who is in charge" as far as our mapping goes.
- **By department** (default) — one column per company department
  (`function` on the person record, derived from the title; house order
  Executive → Development → Sales → Pre-Con → Construction → Energy → …),
  most senior first; the top rank in each column is flagged **most
  senior** when it is Director level or above.
- **By location** — the same people grouped by `location_norm.group`
  (US state, or country elsewhere), so London never splits across
  "England" and "United Kingdom".
- Every column header has a **"N titles"** toggle listing the distinct
  job titles used in that department (or place) with headcounts — the
  company's own wording, ready to paste into a search.
- A text filter matches name, title, location *and past employers* ("who
  at Vantage used to be at Google?").
- Click any card to expand **past employers** (from the parsed career
  history), earlier roles at the same company, a LinkedIn link, and a
  note when the department was inferred from the mapping list rather than
  the title.

Two honesty labels are built in: the header says the chart is "from Ward
Search mapping, not the company's full org", and "most senior" means most
senior *among the people we have mapped*. `build_graph3d_data.py` emits
only the fields the chart needs (name, title, function, seniority,
location, LinkedIn, career) — never email, phone, or compensation.

**Ward's own searches (2026-09-10).** `data/searches/` is read into the page but
deliberately **not** drawn as nodes — 90 extra dots would clutter the map for no
gain. The searches reach the map three ways instead:

- **On the client company.** Its detail panel opens with a **Ward history** block:
  how many searches we have run for them, how many we placed, then a row per
  search with its status, dates, pipeline size and who was placed.
- **On the candidate.** A person card carries an "in our pipeline · N" pill (or
  "we placed" where we did), and expanding the card lists each search with how
  far they got — approached, contender, offered, we passed, client passed,
  withdrew — translated from the Clockwork status. 478 mapped people carry this.
- **"Where we have worked"** — a full-stage overlay grouping every search by
  client, biggest relationship first, filterable by status and by free text
  (client, role or candidate name). Clicking a client name focuses it on the map.

A **"Clients only"** switch narrows the whole graph to the 21 clients that are
companies here. Because those rarely have lines to each other, turning it on also
moves the unconnected switch to Show (visibly, in the sidebar) so the map doesn't
empty out.

Two things this deliberately does not show: **confidential searches are not in
the data at all** (the repo syncs to GitHub), and compensation and fee data were
never pulled. A "pipeline count is a floor" note appears on the 38 long-term
mapping pools whose full candidate lists have not been paged out of Clockwork.
