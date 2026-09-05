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
- **`sources/`** — raw notes, pasted articles, or text that specific facts
  were derived from, kept so every fact can be traced back to where it
  came from

## Status

Real data has started loading. Currently in the brain:

- **1,163 companies** — in two groups, both carried on each record as
  `roles` (see `docs/schema.md`):
  - **741 data-center companies** — Pure Data Centers and STACK
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
  - **422 adjacent-industry companies** from four more of Siddhi's lists —
    Energy Developers (159), Civil/Land Engineers (116), General
    Contractors USA (150), Cold Storage & Industrial Developers (29) —
    kept in the brain with her DC-exposure rating and every column from
    the sheets, but switched off by default in the 3D atlas. 42 companies
    sit on more than one list (AECOM is a civil engineer, an industrial
    developer *and* a GC) and render as multi-colour nodes.
  Every company also carries a `parent_industry` (`pure_play` vs
  `real_estate` / `energy_utilities` / `telecom` / `construction_engineering`
  / `diversified_conglomerate`) — the direct-tap recruiting pool vs.
  "check what this candidate actually works on."
  Every company also carries a `parent_industry` field: `pure_play` if
  data centers are its own dedicated business (the direct-tap recruiting
  pool), or `real_estate` / `energy_utilities` / `telecom` /
  `construction_engineering` / `diversified_conglomerate` if it's one arm
  of a bigger business (e.g. Prologis- or Panattoni-style real estate
  parents, energy companies like NextEra Energy Resources, telecoms like
  NTT) — those need a closer look at what a candidate actually works on.
- **123 investors**: Oaktree Capital Management (the original entry) plus
  122 more added from web research into who backs each company (private
  equity firms, infrastructure funds, sovereign wealth funds, VC) —
  every claim carries a source and a confidence rating on its
  relationship, and every record explicitly says "verify against your
  own research" since this came from web search, not Clockwork. A second
  research round (2026-09-05, 6 parallel agents) took company-backed
  count from 49 to 104 and added 40 new investor firms; a follow-up
  crypto-mining-pivot round added 4 more (Starwood Capital Group,
  Generate Capital, Spring Lane Capital, and Galaxy Digital in its dual
  role as both a company and an investor).
- **1,980 people**: candidates from Ward Search's two active searches
  (Pure Data Centers "VP Sales," STACK Infrastructure "Cost Strategy")
  plus their long-term mapping pools, and 5 firm-wide "Long Term Mapping"
  lists (Sales, Precon, Development, Construction, Utilities) — imported
  from Clockwork exports across 2026-09-04 – 2026-09-05. Each has a
  `department` — Sales (547), Pre-Construction (486), Development (445),
  Construction (321), or Energy & Utilities (191) — and, where their
  current employer qualifies as a data center company, a `works_at` link
  to it. Anyone whose employer didn't qualify was **not** kept as an
  individual profile (see `viewer/README.md`). Email, phone, and
  compensation were deliberately left out of every record (kept in
  Clockwork only) — see `docs/schema.md`.
- **2,806 relationships** connecting the above (candidacy links,
  employment links, and investor links)
- An interactive visual graph of all of this — see `viewer/README.md`

**Known issue:** "Pure Data Centers" and "Pure Data Centres" exist as two
separate company records (American vs. British spelling, one hand-written
as the client company, one auto-generated from candidate data) — worth
merging.

Placeholder `example-` entries used during initial setup have been removed
now that real data is in place.
