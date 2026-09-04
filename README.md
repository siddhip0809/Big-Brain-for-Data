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

- **52 companies**: Pure Data Centers and STACK Infrastructure (both active
  Ward Search client engagements, hand-written records); 48 more identified
  as current employers of candidates and classified as data center
  operators/developers/hyperscalers/real-estate-developers (minimal stub
  records — see `viewer/README.md` for the classification rule); and 2
  (Prologis, Trammell Crow Company) added by hand as known real-estate
  firms with a dedicated data center arm, currently with no candidates
  attached
- **1 investor**: Oaktree Capital Management (inferred from a Clockwork
  subtitle — flagged as unverified, see its entry)
- **384 people**: candidates from the Pure Data Centers "VP Sales" search
  and the STACK Infrastructure "Cost Strategy" search, imported from
  Clockwork exports on 2026-09-04. Each has a `department` — Sales (110),
  Pre-Construction (271), or Energy & Utilities (3) — and, where their
  current employer is one of the companies above, a `works_at` link to it.
  Email, phone, and compensation were deliberately left out of these
  records (kept in Clockwork only) — see `docs/schema.md`.
- **565 relationships** connecting the above (candidacy links, employment
  links, and the one investor link)
- An interactive visual graph of all of this — see `viewer/README.md`

Placeholder `example-` entries used during initial setup have been removed
now that real data is in place.
