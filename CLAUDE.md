# Working on this repo

A knowledge graph of the data-center industry, built for Ward Search (executive
search). Plain JSON files, a few Python build scripts, and one self-contained
HTML page published as a private Artifact. No framework, no build system, no
dependencies beyond `openpyxl` for the spreadsheet importers.

## Hard rules

1. **Never store email, phone or compensation for a person.** Anywhere. Source
   files carry these columns; every importer drops them at read time. If you add
   an importer, drop them explicitly and say so in its docstring.
2. **Nothing about a confidential Clockwork search enters this repo** — not the
   client, not the role title. The repo syncs to GitHub.
3. **Every researched claim carries its sources.** A claim with no source URL is
   marked `confidence: "low"` and `status: "unsupported"` rather than deleted.
   Never invent a URL, a figure or a date.
4. **Judgement is labelled as judgement.** Ward's own assessments live under
   `assessment` on a person and say so in the UI; research findings are separate.

## Layout

```
data/companies/*.json     1,204 companies. `roles` is the single source of truth for tier.
data/investors/*.json     124 funds. `investments` lists company ids.
data/people/*.json        9,239 people. Filename ends in the first 8 chars of the Clockwork id.
data/relationships.json   3,626 edges, one flat list. See docs/schema.md for the types.
data/searches/*.json      91 searches pulled from Clockwork (client, brief, pipeline, placement).
                          Referred to as `search:<filename>`; the `id` field is the Clockwork UUID.
data/derived/*.csv        Generated. Never hand-edit; rerun the script.
scripts/                  Importers (import_*) and derivations (build_*, enrich_*, merge_*).
viewer/build_graph3d_data.py   Reads all of data/, writes viewer/graph3d_data.json.
viewer/atlas3d_template.html   The page. `__GRAPH_DATA_JSON__` is replaced at publish time.
docs/schema.md            What every field means. Update it when you add one.
```

`viewer/graph3d_data.json` is gitignored: it is a build product.

## The pipeline

Data changes, then run in this order:

```bash
python3 scripts/enrich_people.py --apply      # function, seniority, career, location_norm
python3 scripts/build_title_index.py          # data/derived/job_titles*.csv
python3 scripts/build_talent_flows.py         # data/derived/talent_flow*.csv
python3 viewer/build_graph3d_data.py          # viewer/graph3d_data.json
```

Then build and publish the page: substitute the JSON into the template and
publish with the Artifact tool, passing the existing URL so it updates in place
rather than creating a second artifact.

```python
tpl = open('viewer/atlas3d_template.html').read()
out = tpl.replace('__GRAPH_DATA_JSON__', open('viewer/graph3d_data.json').read())
```

Artifact URL: `https://claude.ai/code/artifact/46437bf6-d084-4f23-ab65-6a9a58860f25`
It declares the `db` capability (verification flags are stored there), so omit
`capabilities` on republish to carry the declaration forward.

## Conventions that matter

- **Every script is dry-run by default.** `--apply` writes. Keep it that way.
- **Every script has a `__main__` guard.** `enrich_people` and
  `build_talent_flows` are imported by other modules; without the guard an
  import with `--apply` in `sys.argv` rewrites all 9,000 person records. This
  has happened once.
- **Company ids are slugs** (`stack-infrastructure`). Investor *nodes* in the
  graph are namespaced `investor:<id>` because six names are both a company and
  an investor (Google, NVIDIA, Galaxy Digital, Actis, GI Partners, Generate
  Capital). Relationship endpoints are `company:<id>` / `investor:<id>`.
- **Name matching** uses a `norm` (alphanumeric lowercase) then a `loose` pass
  that strips corporate suffixes, and only accepts a loose match when it is
  unique. Copy that pattern; do not fuzzy-match on similarity scores. Real
  near-misses that are *different* companies: Switch vs Global Switch, Galaxy
  Digital vs Galaxy Data Centers, POWER Engineers vs Power Construction.
- **Merging duplicates** is `scripts/merge_companies.py <keep> <drop> --apply`.
  It only drops a repointed edge that exactly duplicates an existing one.

## The page

One file, ~2,000 lines, Three.js r128 from jsdelivr. No bundler.

- **Layout** is a custom O(n²) force simulation over the *visible* nodes only.
  The data-center core sits at the origin; each adjacent industry is a petal on
  a ring in the plane facing the default camera. Cross-zone and talent-flow
  edges carry no spring, so the zones hold their shape.
- **Lines** are `LineSegments2` fat lines. Colour is the relationship type,
  dash pattern is status or confidence. In r128 `dashed: true` alone does
  nothing — you must also set `material.defines.USE_DASH` and
  `needsUpdate = true`.
- **Labels** are DOM divs. One div per visible node (so
  `document.querySelectorAll('.label3d').length` is a good proxy for node count
  in tests), ranked by weight and placed greedily with collision avoidance
  under a zoom-dependent budget. A test that counts *visible* labels measures
  the budget, not the graph.
- **Theme** is light by default; `body.dark` restores the original dark look.
  Define colours as CSS variables on `:root` and override under `body.dark`.
  Glow sprites are dark-mode only.
- **Toggles**: tier filters, an adjacent show/hide-all, a three-way unconnected
  switch (show / set apart / hide, default hide), and a per-type on/off for
  every line plus all-on/all-off. A line switched off stops counting toward
  "connected", so it changes the unconnected count and focus rings too.

## Testing

Playwright against a local copy of the page, with the CDN URLs rewritten to the
vendored Three.js under the scratchpad. Chromium is at
`/opt/pw-browsers/chromium`; never run `playwright install`.

Two environment traps that look like bugs and are not:
- **Google Fonts is blocked here** and the stylesheet is render-blocking, so the
  page takes ~15 s to become interactive. Route `**fonts.googleapis.com**` to
  `abort()` and it is ~2.4 s.
- **No GPU.** WebGL runs on SwiftShader, so the frame rate with fat lines drawn
  is ~10 fps regardless of the data. Not a regression.
- **LibreOffice cannot run** in this sandbox, so `recalc.py` from the xlsx skill
  times out even on a 4-cell file. Verify spreadsheet formulas by hand.

## Clockwork

Live via MCP. Call `clockwork_get_knowledge` with `business-rules` and `domain`
first — they encode rules you must follow (do-not-contact is a hard stop,
confidential searches, the client-visibility flag, how status name/category/rank
differ). Internal projects (`isInternal`) are firm-side mapping duplicates,
usually named `[M] …`, and are filtered out.

There is deliberately **no `scripts/import_clockwork_searches.py`**: Clockwork is
reachable only through MCP tools, which a standalone Python process cannot call.
The search pull is therefore an agent task, not a script. To repeat or extend it:

- `clockwork_list_projects` pages with `offset` behaving as a **page index**, not a
  row offset — use `offset = page` with a fixed `limit`, or you will re-read page 0.
- Skip `isConfidential` (write nothing at all, not even the id) and `isInternal`.
- Keep a pipeline entry only when its status `rank` >= 100; below that it is a raw
  long-list touch, not a candidacy.
- Match a candidate to `data/people/` on the Clockwork person id, which is the
  suffix of the person filename. No match means write `brain_person_id: null`; do
  not create a thin person record from a pipeline row.
- Job descriptions occasionally contain a salary range. Redact it — rule 1.
- 39 searches carry `pipeline_not_pulled: true` (11,071 candidacies, mostly Long
  Term Mapping pools). Resuming those means paging `clockwork_list_candidacies`.
