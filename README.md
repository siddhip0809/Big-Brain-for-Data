# Big Brain for Data

A knowledge base ("the brain") covering the data center industry: companies,
people, private investors, and the relationships that connect them —
built for research and sourcing work.

## How this works (no coding required)

You don't need to open or edit any files yourself. You talk to Claude in
plain English — "add this company," "who invests in Company X," "show me
everyone we know at Company Y" — and Claude reads and updates the files in
this repository on your behalf. Every change is tracked in git, so nothing
is ever silently lost or overwritten.

## What's in here

- **`data/companies/`** — one file per company (data center operators,
  builders, service providers, etc.)
- **`data/people/`** — one file per person (executives, engineers,
  candidates, contacts)
- **`data/investors/`** — one file per investor or fund (private equity,
  venture capital, infrastructure funds, etc.)
- **`data/relationships.json`** — the connections between all of the above
  (e.g. "works at," "invested in," "board member of")
- **`docs/schema.md`** — a plain-English description of what information
  each type of entry holds
- **`data/derived/`** — indexes computed from the records above (job
  titles by company/department); regenerate, don't hand-edit
- **`scripts/`** — `enrich_people.py` (derives department, seniority,
  career and normalised location on every person record) and
  `build_title_index.py`; re-run both after importing people
- **`sources/`** — raw notes, pasted articles, or text that specific facts
  were derived from, kept so every fact can be traced back to where it
  came from

## Status

Real data has started loading. Currently in the brain:

- **1,141 companies** — in two groups, both carried on each record as
  `roles` (see `docs/schema.md`):
  - **726 data-center companies** — Pure Data Centers and STACK
    Infrastructure (active Ward Search client engagements, hand-written
    records); ~190 more identified as current employers of candidates in
    Clockwork and classified as genuine operators/developers/hyperscalers/
    neoclouds (that rule was tightened twice to throw out general
    contractors, consultancies, and diversified real estate firms that had
    slipped in on noisy tag data, plus 9 mistagged CRM "current employer"
    values like an EV-charging company; a 2026-09-05 research round added a
    batch of US crypto miners — Cipher Mining, Riot Platforms, MARA, Bitfarms,
    Bitdeer and others — that have pivoted into AI/HPC hosting); and the
    bulk imported 2026-09-05 from Siddhi's own curated **Data Centre
    Developer** list (799 rows → 664 kept after skipping the 135 she typed
    "Other/Not Relevant"), which also brought website, LinkedIn, HQ,
    headcount, hyperscale focus, and **MW capacity by region** for 638
    companies.
  - **415 adjacent-industry companies** from four more of Siddhi's lists —
    Energy Developers (159), Civil/Land Engineers (116), General
    Contractors USA (150), Cold Storage & Industrial Developers (29) —
    kept in the brain with her DC-exposure rating and every column from
    the sheets, but switched off by default in the 3D atlas. 42 companies
    sit on more than one list (AECOM is a civil engineer, an industrial
    developer *and* a GC) and render as multi-colour nodes.
  Every company also carries a `parent_industry` field: `pure_play` if
  data centers are its own dedicated business (the direct-tap recruiting
  pool), or `real_estate` / `energy_utilities` / `telecom` /
  `construction_engineering` / `diversified_conglomerate` if it's one arm
  of a bigger business (e.g. Prologis- or Panattoni-style real estate
  parents, energy companies like NextEra Energy Resources, telecoms like
  NTT) — those need a closer look at what a candidate actually works on.
- **124 investors**: Oaktree Capital Management (the original entry) plus
  123 more added from web research into who backs each company (private
  equity firms, infrastructure funds, sovereign wealth funds, VC) —
  every claim carries a source and a confidence rating on its
  relationship, and every record explicitly says "verify against your
  own research" since this came from web search, not Clockwork. A second
  research round (2026-09-05, 6 parallel agents) took company-backed
  count from 49 to 104 and added 40 new investor firms; a follow-up
  crypto-mining-pivot round added 4 more (Starwood Capital Group,
  Generate Capital, Spring Lane Capital, and Galaxy Digital in its dual
  role as both a company and an investor).
- **2,129 people**: candidates from Ward Search's two active searches
  (Pure Data Centers "VP Sales," STACK Infrastructure "Cost Strategy")
  plus their long-term mapping pools, and 5 firm-wide "Long Term Mapping"
  lists (Sales, Precon, Development, Construction, Utilities) — imported
  from Clockwork exports across 2026-09-04 – 2026-09-05. Each has a
  `department` — Sales (547), Pre-Construction (486), Development (445),
  Construction (321), or Energy & Utilities (191) — and, where their
  current employer qualifies as a data center company, a `works_at` link
  to it. Candidates at **adjacent-industry** employers (Turner & Townsend,
  Mortenson, HITT, Clark …) were re-imported on 2026-09-09 at Siddhi's
  request (`scripts/import_adjacent_people.py`; 149 new people, 350 more
  linked to their employer), so those companies now have org charts too;
  the ~85 candidates still left out work at consultancies that are on none
  of the lists (Linesight, Cumming, RLB, AtkinsRéalis, JLL, C&W). Since 2026-09-08 each
  person also carries a derived **`function`** — the company department
  their title belongs to (Development & Real Estate 574, Pre-Construction
  & Cost 429, Sales & Leasing 365, Construction & Delivery 295, Energy &
  Utilities 198, Executive leadership 59, …) — a **seniority rank**
  (C-suite 79, EVP/SVP/MD 122, VP/Head 306, Director 616, Manager/Lead
  667, IC 190; Clockwork's own level where it had one, otherwise from the
  title) and a parsed **`career`** list (11,666 past-employer entries).
  Those three fields drive the per-company **org chart** in the atlas.
  **Talent flows** (`scripts/build_talent_flows.py`, 2026-09-09) turn the
  career histories into "who hires from whom": each person's previous
  employer → current employer (1,524 moves, 484 pairs between tracked
  companies, e.g. AWS → Microsoft 11, AWS → Google 10, Equinix → Digital
  Realty 7) plus a list of the 226 people who started their current role
  in the last six months — `data/derived/talent_flows.csv` and
  `recent_moves.csv`, and in the atlas as each company's "Hires from /
  Alumni now at" panel, an org-chart grouping by previous employer, a
  "new" badge, and toggleable grey flow lines.
  Locations are normalised too (`location_norm`: US state or country),
  and `data/derived/job_titles.csv` + `job_titles_by_function.csv` index
  every job title in use per company and per department — the exact
  wording to search on (rebuild with `scripts/build_title_index.py`).
  Email, phone, and compensation were deliberately left out of every
  record (kept in Clockwork only) — see `docs/schema.md`.
- **3,048 relationships** connecting the above — candidacy links,
  employment links, investor backing (124 investors incl. Google and
  NVIDIA in their dual role as strategic investors), and, since
  2026-09-05, a **company-to-company deal layer** of 98 edges:
  - `tenant_of` — who leases data-center capacity from whom (AWS →
    Cipher Mining, Oracle → Vantage/Related Digital/STACK for OpenAI's
    Stargate sites, Meta → CoreWeave ~$35B, Microsoft → Crusoe 900 MW,
    Anthropic → Nscale/Hut 8/TeraWulf, Fluidstack → Hut 8/TeraWulf …)
  - `acquired` — consolidation with status (American Tower → CoreSite,
    Blackstone → QTS, KKR/GIP → CyrusOne, DigitalBridge/IFM → Switch,
    Vantage → Yondr's Johor campus, Riot → Bitfarms *terminated*, AIP →
    Aligned $40B, Equinix and Digital Realty country tuck-ins …)
  - `jv_partner` — Crusoe ↔ Lancium (Abilene), TeraWulf ↔ Fluidstack,
    Meta ↔ Blue Owl (Hyperion) and ↔ BlackRock (El Paso)
  - **adjacent industry → data-center core** (2026-09-08, 141 edges from a
    4-agent research round): `contractor_for` (75 — Holder → Google /
    Microsoft / Meta, Turner and McCarthy → Vantage, HITT → QTS / Corscale
    / Rowan, Walbridge → Related Digital's $16B Michigan Stargate site,
    Yates and Haskell → AWS Mississippi, plus civil engineers like Bohler
    → AWS Warrenton and Kimley-Horn → QTS Fayetteville),
    `supplies_power_to` (61 — AES → Meta / Google / AWS / Microsoft, Talen
    → AWS Susquehanna, Brookfield → Microsoft 10.5 GW, Ørsted, Avangrid,
    Invenergy, Entergy-style utility agreements; ~36 GW where stated) and
    `site_partner` (5 — Hillwood → Meta / T5, Affinius → Corscale, Seefried
    → Edged). **Coverage caveat:** the researchers' web-search budget ran
    out part-way, so roughly a third of the contractors and a fifth of the
    energy companies were checked; the rest are unverified, not
    confirmed-negative. Firms with a confirmed DC practice but confidential
    clients (Suffolk, Clayco, Skanska, Hensel Phelps, Bowman, Dewberry,
    Dominion's ~40 GW of unnamed contracts …) deliberately have no edge.
  Deals whose counterparty isn't a tracked node (Teraco, Stronghold,
  Whinstone, Anyscale, Groq …) are kept as dated "M&A:" notes on the
  acquirer's record — ~40 of them — so nothing from the research is lost.
  For a headhunter these are hiring/layoff signals: the miners-turned-
  landlords (TeraWulf, Hut 8, Cipher, Applied Digital) and the Stargate
  landlords (Vantage, Related Digital, STACK, Crusoe, SB Energy) are where
  the 2026–28 construction, commissioning and operations demand sits.
- **Weekly hiring signals (automated).** A Routine ("Data center brain —
  weekly hiring signals", Mondays 06:00 UTC, set up 2026-09-09) runs in a
  fresh session: theme-based web searches over the past week (campus
  announcements, leases, PPAs, M&A, JVs, executive appointments), writes
  sourced signals to `data/signals/YYYY-MM-DD.json`, adds relationships
  where both parties are tracked, rebuilds, republishes the atlas, commits
  to this branch, and emails Siddhi a summary. Same evidence rules as the
  rest of the brain: only URLs returned by search results, nothing
  guessed, an empty week is a valid result. Pause or edit it in the
  claude.ai Routines list.
- **Verification flags.** Every researched relationship can carry
  `verified_by` (research team / Siddhi / Ward confirmed, each dated),
  set by clicking in the atlas and pulled back with
  `scripts/pull_verifications.py`.
- **Gap list.** `data/derived/` also holds the per-company talent flows;
  the list of unconnected companies with columns to fill was sent to
  Siddhi on 2026-09-09 as a spreadsheet — send it back filled and each
  row becomes sourced relationships.
- An interactive visual graph of all of this — see `viewer/README.md`

**Duplicates:** 22 double records were merged on 2026-09-09 with
`scripts/merge_companies.py` (Pure Data Centers/Centres, STACK
Infrastructure/STACK Americas, NTT/NTT Global Data Centers, Mortenson,
Ark, atNorth, BGO, Green Mountain ×3, ENGIE, Telehouse, EDP and EDF
Renewables' North America arms, Bit Digital, Goodman, Webcor, Bohler,
OPCORE, maincubes, Structure Tone Southwest, Digital Realty Bersama,
Polar/Polar DC). Regional arms fold into the parent; the dropped name
becomes an alias so search still finds it. Deliberately *not* merged:
Switch vs Global Switch, Galaxy Digital vs Galaxy Data Centers, Switch vs
Switch Datacenters — different companies with similar names.

Placeholder `example-` entries used during initial setup have been removed
now that real data is in place.
