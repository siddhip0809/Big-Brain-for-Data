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

- **186 companies**: Pure Data Centers and STACK Infrastructure (active
  Ward Search client engagements, hand-written records); the rest
  identified as current employers of candidates and classified as
  genuine data center operators/developers/hyperscalers/neocloud-AI-infra
  companies (minimal stub records — see `viewer/README.md` for the
  classification rule, tightened once to exclude general contractors,
  consultancies, and diversified real estate firms that had slipped in
  on noisy tag data)
- **1 investor**: Oaktree Capital Management (inferred from a Clockwork
  subtitle — flagged as unverified, see its entry)
- **1,993 people**: candidates from Ward Search's two active searches
  (Pure Data Centers "VP Sales," STACK Infrastructure "Cost Strategy")
  plus their long-term mapping pools, and 5 firm-wide "Long Term Mapping"
  lists (Sales, Precon, Development, Construction, Utilities) — imported
  from Clockwork exports across 2026-09-04 – 2026-09-05. Each has a
  `department` — Sales (547), Pre-Construction (488), Development (445),
  Construction (322), or Energy & Utilities (191) — and, where their
  current employer qualifies as a data center company, a `works_at` link
  to it. Anyone whose employer didn't qualify was **not** kept as an
  individual profile (see `viewer/README.md`). Email, phone, and
  compensation were deliberately left out of every record (kept in
  Clockwork only) — see `docs/schema.md`.
- **2,631 relationships** connecting the above (candidacy links,
  employment links, and the one investor link)
- An interactive visual graph of all of this — see `viewer/README.md`

Placeholder `example-` entries used during initial setup have been removed
now that real data is in place.
